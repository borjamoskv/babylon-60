"""ZIP export for DORA evidence packs."""

from __future__ import annotations

import zipfile
from pathlib import Path

from cortex.compliance.dora.models import DoraConfig
from cortex.compliance.dora.render import RenderedPack, render_evidence_pack


def export_dora_pack(
    config: DoraConfig,
    output_path: str | Path,
    *,
    lifecycle_status: str = "draft",
) -> RenderedPack:
    """Render and write a DORA evidence pack ZIP."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pack = render_evidence_pack(config, lifecycle_status=lifecycle_status)
    if pack.manifest.validation.errors:
        codes = ", ".join(issue.code for issue in pack.manifest.validation.errors)
        raise ValueError(f"DORA evidence pack has validation errors: {codes}")
    if lifecycle_status == "issued" and pack.manifest.validation.warnings:
        codes = ", ".join(issue.code for issue in pack.manifest.validation.warnings)
        raise ValueError(f"DORA evidence pack cannot be issued with validation warnings: {codes}")
    _write_zip(pack, output)
    return pack


def _write_zip(pack: RenderedPack, output: Path) -> None:
    fixed_timestamp = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for document in sorted(pack.documents, key=lambda item: item.path):
            info = zipfile.ZipInfo(document.path, fixed_timestamp)
            archive.writestr(info, document.content.encode("utf-8"))

        info = zipfile.ZipInfo("manifest.json", fixed_timestamp)
        archive.writestr(info, pack.manifest_json().encode("utf-8"))
