import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cortex.origin import KeyRegistry, EventEnvelope


def test_origin_envelope_signing_and_verification():
    # 1. Generate keys
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_b64 = base64.b64encode(private_key.private_bytes_raw()).decode("utf-8")
    pub_b64 = base64.b64encode(public_key.public_bytes_raw()).decode("utf-8")

    # 2. Register key
    registry = KeyRegistry()
    registry.register(key_id="key-01", public_key_b64=pub_b64, owner="agent-alice")

    # 3. Create envelope and sign
    payload = {"event": "state_transition", "data": {"x": 42}}
    envelope = EventEnvelope(payload=payload, key_id="key-01")
    envelope.sign(private_key_b64=priv_b64)

    # 4. Verify envelope
    assert envelope.verify(registry) is True

    # 5. Tampered payload verification failure
    envelope_tampered = EventEnvelope(
        payload={"event": "state_transition", "data": {"x": 43}},
        key_id="key-01",
        signature_b64=envelope.signature_b64,
    )
    assert envelope_tampered.verify(registry) is False

    # 6. Revoked key verification failure
    registry.revoke("key-01")
    assert envelope.verify(registry) is False
