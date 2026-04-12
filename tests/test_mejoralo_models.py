from __future__ import annotations

from cortex.extensions.mejoralo.models import AntipatternFinding, AntipatternReport


def test_antipattern_report_counts_and_groups_by_severity() -> None:
    report = AntipatternReport(
        findings=[
            AntipatternFinding(
                scanner="security",
                severity="critical",
                file="alpha.py",
                line=10,
                message="secret leak",
                fix_hint="use env vars",
            ),
            AntipatternFinding(
                scanner="complexity",
                severity="high",
                file="beta.py",
                line=20,
                message="deep nesting",
                fix_hint="extract helper",
            ),
            AntipatternFinding(
                scanner="style",
                severity="high",
                file="gamma.py",
                line=30,
                message="ambiguous name",
                fix_hint="rename",
            ),
        ]
    )

    assert report.total == 3
    assert report.critical_count == 1
    assert report.high_count == 2
    grouped = report.by_severity()
    assert len(grouped["critical"]) == 1
    assert len(grouped["high"]) == 2
