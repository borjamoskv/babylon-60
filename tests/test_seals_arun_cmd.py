import pytest

from cortex.guards import seals


class _FakeProcess:
    returncode = 0

    async def communicate(self) -> tuple[bytes, bytes]:
        return b"ok", b""


@pytest.mark.asyncio
async def test_arun_cmd_injects_pythonpath_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_env: list[dict[str, str]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_env.append(dict(kwargs["env"]))
        return _FakeProcess()

    monkeypatch.setenv("PYTHONPATH", "original")
    monkeypatch.setattr(seals.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    code, out = await seals.arun_cmd(["python", "--version"])

    assert code == 0
    assert out == "ok"
    assert captured_env[0]["PYTHONPATH"] == ".:original"


@pytest.mark.asyncio
async def test_arun_cmd_can_skip_pythonpath_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_env: list[dict[str, str]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured_env.append(dict(kwargs["env"]))
        return _FakeProcess()

    monkeypatch.setenv("PYTHONPATH", "original")
    monkeypatch.setattr(seals.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    code, out = await seals.arun_cmd(
        ["pyright", "cortex/", "--outputjson"], inject_pythonpath=False
    )

    assert code == 0
    assert out == "ok"
    assert captured_env[0]["PYTHONPATH"] == "original"


@pytest.mark.asyncio
async def test_seal_2_captures_pyright_output_to_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: list[dict[str, object]] = []

    async def fake_arun_cmd(*args, **kwargs):
        captured_kwargs.append(dict(kwargs))
        return 1, '{"summary": {"errorCount": 74}}'

    monkeypatch.setattr(seals, "arun_cmd", fake_arun_cmd)

    passed, status = await seals.check_seal_2_type_safety()

    assert passed is True
    assert status == "verified"
    assert captured_kwargs == [{"capture_to_file": True, "inject_pythonpath": False}]
