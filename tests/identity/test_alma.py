import json
from pathlib import Path

import pytest

from cortex.identity.alma import AlmaIdentity, SoulCorruptionError


def test_alma_generation_and_verification(tmp_path: Path) -> None:
    alma_file = tmp_path / "alma.json"
    pub_key_hex = AlmaIdentity.generate_dummy(alma_file)

    assert alma_file.exists()

    # Should load properly without exceptions
    identity = AlmaIdentity(alma_file, pub_key_hex)
    assert "thermodynamic limits" in identity.invariants[0]
    assert identity.thermodynamic_limits["max_exergy_loss_per_cycle"] == 10.0

def test_alma_corruption_raises_error(tmp_path: Path) -> None:
    alma_file = tmp_path / "alma.json"
    pub_key_hex = AlmaIdentity.generate_dummy(alma_file)

    doc = json.loads(alma_file.read_text("utf-8"))
    doc["invariants"].append("I secretly love eating entropy.")
    alma_file.write_text(json.dumps(doc), "utf-8")

    with pytest.raises(SoulCorruptionError, match="E_SOUL_CORRUPTION: Invalid Ed25519 Signature."):
        AlmaIdentity(alma_file, pub_key_hex)

def test_alma_missing_signature(tmp_path: Path) -> None:
    alma_file = tmp_path / "alma.json"
    pub_key_hex = AlmaIdentity.generate_dummy(alma_file)

    doc = json.loads(alma_file.read_text("utf-8"))
    del doc["signature"]
    alma_file.write_text(json.dumps(doc), "utf-8")

    with pytest.raises(SoulCorruptionError, match="Missing cryptosignature"):
        AlmaIdentity(alma_file, pub_key_hex)

def test_alma_no_key_bypasses_crypto(tmp_path: Path) -> None:
    alma_file = tmp_path / "alma.json"
    AlmaIdentity.generate_dummy(alma_file)

    doc = json.loads(alma_file.read_text("utf-8"))
    del doc["signature"]
    doc["invariants"].append("Some hacked invariant")
    alma_file.write_text(json.dumps(doc), "utf-8")

    # Passing None for public_key_hex bypasses check
    identity = AlmaIdentity(alma_file, None)
    assert len(identity.invariants) == 3
