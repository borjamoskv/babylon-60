from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_skill_auditor():
    module_path = Path(__file__).resolve().parents[1] / "scratch" / "skill_auditor.py"
    spec = importlib.util.spec_from_file_location("skill_auditor", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_audit_skills_detects_missing_asset_and_missing_axioms(tmp_path: Path) -> None:
    auditor = _load_skill_auditor()

    good_skill = tmp_path / "good-skill"
    (good_skill / "scripts").mkdir(parents=True)
    (good_skill / "scripts" / "runner.py").write_text("print('ok')\n", encoding="utf-8")
    (good_skill / "SKILL.md").write_text(
        "---\n"
        "name: good-skill\n"
        "description: Good skill.\n"
        "axioms:\n"
        "  - omega_2_thermodynamic\n"
        "---\n\n"
        "Use `python3 scripts/runner.py`.\n",
        encoding="utf-8",
    )

    bad_skill = tmp_path / "bad-skill"
    bad_skill.mkdir()
    (bad_skill / "SKILL.md").write_text(
        "---\n"
        "name: bad-skill\n"
        "description: Broken skill.\n"
        "---\n\n"
        "Use `python3 scripts/missing.py`.\n",
        encoding="utf-8",
    )

    report = auditor.audit_skills(
        tmp_path,
        command_exists=lambda command: "/usr/bin/python3" if command == "python3" else None,
    )
    by_id = {skill.skill_id: skill for skill in report.skills}

    assert report.summary.active_skill_count == 2
    assert by_id["good-skill"].reproducibility_status == "C5-STATIC"
    assert by_id["bad-skill"].reproducibility_status == "C4-SIMULACION"
    assert any(issue.code == "missing_field_axioms" for issue in by_id["bad-skill"].issues)
    assert any(issue.code == "missing_local_asset_reference" for issue in by_id["bad-skill"].issues)


def test_cli_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    auditor = _load_skill_auditor()

    skill = tmp_path / "single-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: single-skill\n"
        "description: Single deterministic skill.\n"
        "axioms:\n"
        "  - omega_2_thermodynamic\n"
        "---\n\n"
        "No local assets.\n",
        encoding="utf-8",
    )

    json_out = tmp_path / "audit.json"
    markdown_out = tmp_path / "audit.md"
    exit_code = auditor.main(
        [
            "--skills-root",
            str(tmp_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
            "--stdout-format",
            "summary",
        ]
    )

    assert exit_code == 0
    assert json_out.exists()
    assert markdown_out.exists()

    json_payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown_payload = markdown_out.read_text(encoding="utf-8")

    assert json_payload["summary"]["active_skill_count"] == 1
    assert "Audit-Omega Report" in markdown_payload
    assert "single-skill" in markdown_payload


def test_slash_commands_and_code_tokens_are_not_treated_as_missing_assets_or_commands(
    tmp_path: Path,
) -> None:
    auditor = _load_skill_auditor()

    skill = tmp_path / "slash-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: slash-skill\n"
        "description: Skill with slash commands and code tokens.\n"
        "axioms:\n"
        "  - omega_2_thermodynamic\n"
        "---\n\n"
        "- `/guard-audit`\n"
        "- `/guard-verify-c5`\n"
        "\n"
        "```ts\n"
        "const value = await fetch('/api');\n"
        "return value;\n"
        "```\n"
        "\n"
        "```bash\n"
        "python3 --version\n"
        "```\n",
        encoding="utf-8",
    )

    report = auditor.audit_skills(
        tmp_path,
        command_exists=lambda command: "/usr/bin/python3" if command == "python3" else None,
    )
    audited_skill = report.skills[0]

    assert audited_skill.reproducibility_status == "C5-STATIC"
    assert not any(issue.code == "missing_local_asset_reference" for issue in audited_skill.issues)
    assert not any(issue.code == "missing_command_dependency" for issue in audited_skill.issues)


def test_self_test_mode_passes() -> None:
    auditor = _load_skill_auditor()

    assert auditor.main(["--test"]) == 0


def test_package_routes_mime_types_and_placeholders_do_not_count_as_missing_assets(
    tmp_path: Path,
) -> None:
    auditor = _load_skill_auditor()

    skill = tmp_path / "protocol-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: protocol-skill\n"
        "description: Skill with protocol docs and one real local missing asset.\n"
        "axioms:\n"
        "  - omega_2_thermodynamic\n"
        "---\n\n"
        "- `@modelcontextprotocol/sdk/server/mcp.js`\n"
        "- `application/json`\n"
        "- `text/event-stream`\n"
        "- `anomalyco/tap/opencode`\n"
        "- `/tools/list`\n"
        "- `/post/[slug]`\n"
        "- `/ouro-audit-contract [file.sol]`\n"
        "- `verify_<skill>.py`\n"
        "- `scripts/missing.py`\n",
        encoding="utf-8",
    )

    report = auditor.audit_skills(tmp_path)
    audited_skill = report.skills[0]
    missing_assets = [
        issue for issue in audited_skill.issues if issue.code == "missing_local_asset_reference"
    ]

    assert len(missing_assets) == 1
    assert missing_assets[0].evidence == [str(skill / "scripts" / "missing.py")]
