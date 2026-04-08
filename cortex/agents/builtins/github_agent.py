"""GitHubAgent with typed ops and stable response envelopes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cortex.agents.builtins._explicit_ops import ExplicitOpsAgent, ExplicitOpsHandler
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.tools import ToolRegistry
from cortex.services.github_shortcuts import GitHubShortcutService, parse_line_spec, run_gh

logger = logging.getLogger(__name__)

_URL_OPS: frozenset[str] = frozenset(
    {"dev", "permalink", "search", "diff_url", "review", "blame", "history", "status"}
)
_GH_OPS: frozenset[str] = frozenset({"pr_checkout", "pr_view", "pr_create", "repo_clone"})
_SUPPORTED_OPS: frozenset[str] = frozenset(_URL_OPS | _GH_OPS)
_OP_ALIASES: dict[str, str] = {
    "diff-url": "diff_url",
}


class GitHubShortcutClient(Protocol):
    context: Any

    def dev_url(self, path: str | Path | None = None) -> str: ...
    def permalink_url(
        self,
        path: str | Path | None = None,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str: ...
    def search_url(
        self,
        query: str,
        *,
        path: str | None = None,
        language: str | None = None,
        symbol: str | None = None,
        repo_scoped: bool = True,
    ) -> str: ...
    def diff_url(
        self,
        *,
        pr_number: int | None = None,
        commit_sha: str | None = None,
        format_name: str = "patch",
    ) -> str: ...
    def review_url(self, pr_number: int) -> str: ...
    def blame_url(self, path: str | Path, *, ref: str | None = None) -> str: ...
    def history_url(self, path: str | Path, *, ref: str | None = None) -> str: ...


class ShortcutFactory(Protocol):
    def __call__(self, remote: str) -> GitHubShortcutClient: ...


class GhRunner(Protocol):
    def __call__(self, args: list[str], *, cwd: Path | None = None) -> None: ...


class _GitHubRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remote: str = "origin"

    @field_validator("remote")
    @classmethod
    def _validate_remote(cls, value: str) -> str:
        return _required_text(value, "remote")


class _StatusRequest(_GitHubRequest):
    op: Literal["status"]


class _DevRequest(_GitHubRequest):
    op: Literal["dev"]
    path: str | None = None


class _PermalinkRequest(_GitHubRequest):
    op: Literal["permalink"]
    path: str
    lines: str | None = None

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _required_text(value, "path")


class _SearchRequest(_GitHubRequest):
    op: Literal["search"]
    query: str = ""
    path: str | None = None
    language: str | None = None
    symbol: str | None = None
    all_repos: bool = False


class _DiffUrlRequest(_GitHubRequest):
    op: Literal["diff_url"]
    pr_number: int | None = None
    commit_sha: str | None = None
    format_name: str = "patch"


class _ReviewRequest(_GitHubRequest):
    op: Literal["review"]
    pr_number: int


class _RefPathRequest(_GitHubRequest):
    path: str
    ref: str | None = None

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        return _required_text(value, "path")


class _BlameRequest(_RefPathRequest):
    op: Literal["blame"]


class _HistoryRequest(_RefPathRequest):
    op: Literal["history"]


class _RepoCloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["repo_clone"]
    name_with_owner: str
    directory: str | None = None

    @field_validator("name_with_owner")
    @classmethod
    def _validate_name_with_owner(cls, value: str) -> str:
        return _required_text(value, "name_with_owner")


class _PrCheckoutRequest(_GitHubRequest):
    op: Literal["pr_checkout"]
    pr_number: int


class _PrViewRequest(_GitHubRequest):
    op: Literal["pr_view"]
    pr_number: int
    web: bool = False


class _PrCreateRequest(_GitHubRequest):
    op: Literal["pr_create"]
    title: str | None = None
    body: str | None = None
    base: str | None = None
    head: str | None = None
    draft: bool = False
    fill: bool = False
    web: bool = False


class _GitHubStatusResponse(BaseModel):
    agent: str
    status: Literal["ok"] = "ok"
    repo: str
    host: str
    branch: str
    head_sha: str
    remote: str
    supported_ops: list[str] = Field(default_factory=list)


class _GitHubUrlResponse(BaseModel):
    url: str
    kind: Literal["url"] = "url"


class _GitHubCommandResponse(BaseModel):
    executed: list[str]
    cwd: str | None = None


def _default_shortcut_factory(remote: str) -> GitHubShortcutClient:
    return GitHubShortcutService.from_repo(remote=remote)


class _GitHubOps(ExplicitOpsHandler):
    supported_ops: frozenset[str] = _SUPPORTED_OPS

    def __init__(
        self,
        shortcut_factory: ShortcutFactory,
        gh_runner: GhRunner,
    ) -> None:
        self._shortcut_factory = shortcut_factory
        self._gh_runner = gh_runner

    def normalize_op(self, op: str) -> str:
        return _OP_ALIASES.get(op, op)

    async def execute(
        self,
        op: str,
        payload: dict[str, Any],
        *,
        agent_id: str,
    ) -> Any:
        if op in _URL_OPS:
            return self._execute_url_op(op, payload, agent_id=agent_id)
        return self._execute_gh_op(op, payload)

    def _execute_url_op(self, op: str, payload: dict[str, Any], *, agent_id: str) -> dict[str, Any]:
        remote = _extract_remote(payload)
        service = self._shortcut_factory(remote)

        if op == "status":
            _StatusRequest.model_validate(payload)
            context = service.context
            return _GitHubStatusResponse(
                agent=agent_id,
                repo=f"{context.owner}/{context.repo}",
                host=context.host,
                branch=context.branch,
                head_sha=context.head_sha,
                remote=context.remote_name,
                supported_ops=sorted(self.supported_ops),
            ).model_dump()

        if op == "dev":
            request = _DevRequest.model_validate(payload)
            return _GitHubUrlResponse(url=service.dev_url(request.path)).model_dump()

        if op == "permalink":
            request = _PermalinkRequest.model_validate(payload)
            start_line, end_line = parse_line_spec(request.lines)
            return _GitHubUrlResponse(
                url=service.permalink_url(
                    request.path,
                    start_line=start_line,
                    end_line=end_line,
                )
            ).model_dump()

        if op == "search":
            request = _SearchRequest.model_validate(payload)
            return _GitHubUrlResponse(
                url=service.search_url(
                    request.query,
                    path=request.path,
                    language=request.language,
                    symbol=request.symbol,
                    repo_scoped=not request.all_repos,
                )
            ).model_dump()

        if op == "diff_url":
            request = _DiffUrlRequest.model_validate(payload)
            return _GitHubUrlResponse(
                url=service.diff_url(
                    pr_number=request.pr_number,
                    commit_sha=_optional_str(request.commit_sha),
                    format_name=request.format_name,
                )
            ).model_dump()

        if op == "review":
            request = _ReviewRequest.model_validate(payload)
            return _GitHubUrlResponse(url=service.review_url(request.pr_number)).model_dump()

        if op == "blame":
            request = _BlameRequest.model_validate(payload)
            return _GitHubUrlResponse(url=service.blame_url(request.path, ref=request.ref)).model_dump()

        if op == "history":
            request = _HistoryRequest.model_validate(payload)
            return _GitHubUrlResponse(
                url=service.history_url(request.path, ref=request.ref)
            ).model_dump()

        raise ValueError(f"unhandled url op: {op!r}")

    def _execute_gh_op(self, op: str, payload: dict[str, Any]) -> dict[str, Any]:
        if op == "repo_clone":
            request = _RepoCloneRequest.model_validate(payload)
            args = ["repo", "clone", request.name_with_owner]
            if request.directory:
                args.append(request.directory)
            self._gh_runner(args, cwd=None)
            return _GitHubCommandResponse(executed=args, cwd=None).model_dump()

        remote = _extract_remote(payload)
        service = self._shortcut_factory(remote)
        cwd = service.context.repo_root

        if op == "pr_checkout":
            request = _PrCheckoutRequest.model_validate(payload)
            args = ["pr", "checkout", str(request.pr_number)]
            self._gh_runner(args, cwd=cwd)
            return _GitHubCommandResponse(executed=args, cwd=str(cwd)).model_dump()

        if op == "pr_view":
            request = _PrViewRequest.model_validate(payload)
            args = ["pr", "view", str(request.pr_number)]
            if request.web:
                args.append("--web")
            self._gh_runner(args, cwd=cwd)
            return _GitHubCommandResponse(executed=args, cwd=str(cwd)).model_dump()

        if op == "pr_create":
            request = _PrCreateRequest.model_validate(payload)
            args = ["pr", "create"]
            _maybe_extend(args, "--title", request.title)
            _maybe_extend(args, "--body", request.body)
            _maybe_extend(args, "--base", request.base)
            _maybe_extend(args, "--head", request.head)
            if request.draft:
                args.append("--draft")
            if request.fill:
                args.append("--fill")
            if request.web:
                args.append("--web")
            self._gh_runner(args, cwd=cwd)
            return _GitHubCommandResponse(executed=args, cwd=str(cwd)).model_dump()

        raise ValueError(f"unhandled gh op: {op!r}")


class GitHubAgent(ExplicitOpsAgent):
    """Reactive agent for GitHub shortcuts and selected `gh` workflows."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        shortcut_factory: ShortcutFactory | None = None,
        gh_runner: GhRunner | None = None,
    ) -> None:
        super().__init__(
            manifest,
            bus,
            tool_registry,
            ops_handler=_GitHubOps(
                shortcut_factory=shortcut_factory or _default_shortcut_factory,
                gh_runner=gh_runner or run_gh,
            ),
        )

    async def tick(self) -> None:
        logger.debug("GitHubAgent tick — idle")


def _maybe_extend(args: list[str], flag: str, value: str | None) -> None:
    if value:
        args.extend([flag, value])


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _extract_remote(payload: dict[str, Any]) -> str:
    return _required_text(str(payload.get("remote", "origin")), "remote")


def _required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text
