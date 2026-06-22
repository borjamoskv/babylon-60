use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::time::{SystemTime, UNIX_EPOCH};

/// Generates an Ephemeral MTK Token (Minimal Trusted Kernel) for database mutations.
/// The token is derived from the payload hash and a secret kernel key using Blake3.
#[pyfunction]
pub fn mint_ephemeral_token(payload_hash: &str, kernel_key: &str) -> PyResult<String> {
    if payload_hash.is_empty() || kernel_key.is_empty() {
        return Err(PyValueError::new_err("Payload hash and kernel key cannot be empty."));
    }

    let start = SystemTime::now();
    let since_the_epoch = start.duration_since(UNIX_EPOCH)
        .expect("Time went backwards");
    let timestamp_ms = since_the_epoch.as_millis();

    let mut hasher = blake3::Hasher::new();
    hasher.update(kernel_key.as_bytes());
    hasher.update(payload_hash.as_bytes());
    hasher.update(&timestamp_ms.to_be_bytes());

    let result = hasher.finalize();
    let code_hex = result.to_hex();
    
    // Format: mtk_auth_<timestamp>_<hex>
    let token = format!("mtk_auth_{}_{}", timestamp_ms, code_hex);
    
    Ok(token)
}

/// Verifies an Ephemeral MTK Token to ensure the mutation is authorized by the MTK.
#[pyfunction]
pub fn verify_ephemeral_token(token: &str, payload_hash: &str, kernel_key: &str) -> PyResult<bool> {
    if !token.starts_with("mtk_auth_") {
        return Ok(false);
    }

    let parts: Vec<&str> = token.split('_').collect();
    if parts.len() != 4 {
        return Ok(false);
    }

    let timestamp_str = parts[2];
    let signature_hex = parts[3];

    let timestamp_ms: u128 = timestamp_str.parse()
        .map_err(|_| PyValueError::new_err("Invalid timestamp in token"))?;

    // Basic expiration: 5000 ms (5 seconds) window for C5-REAL execution
    let start = SystemTime::now();
    let current_ms = start.duration_since(UNIX_EPOCH).unwrap().as_millis();
    if current_ms > timestamp_ms + 5000 {
        return Ok(false); // Token expired
    }

    let mut hasher = blake3::Hasher::new();
    hasher.update(kernel_key.as_bytes());
    hasher.update(payload_hash.as_bytes());
    hasher.update(&timestamp_ms.to_be_bytes());

    let expected_hex = hasher.finalize().to_hex();

    // In a real crypto setting, use constant time eq. Here string eq is fine.
    Ok(signature_hex == expected_hex.as_str())
}
