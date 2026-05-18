// CORTEX v8 — PyO3 FFI Bindings.
//
// Exposes the core Rust substrate to Python.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};

mod canonical;
mod merkle;
mod crypto;

/// compute_tx_hash(prev_hash, project, action, detail_json, timestamp, tenant_id=None)
#[pyfunction]
#[pyo3(signature = (prev_hash, project, action, detail_json, timestamp, tenant_id=None))]
fn compute_tx_hash(
    prev_hash: &str,
    project: &str,
    action: &str,
    detail_json: &str,
    timestamp: &str,
    tenant_id: Option<&str>,
) -> PyResult<String> {
    Ok(canonical::compute_tx_hash(
        prev_hash, project, action, detail_json, timestamp, tenant_id,
    ))
}

/// compute_tx_hash_v1(prev_hash, project, action, detail_json, timestamp)
#[pyfunction]
fn compute_tx_hash_v1(
    prev_hash: &str,
    project: &str,
    action: &str,
    detail_json: &str,
    timestamp: &str,
) -> PyResult<String> {
    Ok(canonical::compute_tx_hash_v1(
        prev_hash, project, action, detail_json, timestamp,
    ))
}

/// compute_fact_hash(content)
#[pyfunction]
fn compute_fact_hash(content: &str) -> PyResult<String> {
    Ok(canonical::compute_fact_hash(content))
}

/// canonical_json(obj_str) - Accepts a JSON string, parses it, and returns the canonical form.
/// (Python serializes to string first, then we canonicalize in Rust to avoid deep PyObject traversal).
#[pyfunction]
fn canonical_json(json_str: &str) -> PyResult<String> {
    let value: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| PyValueError::new_err(format!("Invalid JSON: {}", e)))?;
    Ok(canonical::canonical_json(&value))
}

/// MerkleTree Python wrapper
#[pyclass(name = "MerkleTree")]
struct PyMerkleTree {
    inner: merkle::MerkleTree,
}

#[pymethods]
impl PyMerkleTree {
    #[new]
    fn new(leaves: Vec<String>) -> Self {
        PyMerkleTree {
            inner: merkle::MerkleTree::new(leaves),
        }
    }

    #[getter]
    fn root_hash(&self) -> Option<String> {
        self.inner.root_hash().map(|s| s.to_string())
    }

    fn get_proof(&self, index: usize) -> Vec<(String, String)> {
        self.inner
            .get_proof(index)
            .into_iter()
            .map(|step| {
                let dir = match step.direction {
                    merkle::ProofDirection::Left => "L",
                    merkle::ProofDirection::Right => "R",
                };
                (step.hash, dir.to_string())
            })
            .collect()
    }

    #[staticmethod]
    fn verify_proof(leaf_hash: &str, proof: Vec<(String, String)>, root_hash: &str) -> bool {
        let rust_proof: Vec<merkle::ProofStep> = proof
            .into_iter()
            .map(|(hash, dir)| merkle::ProofStep {
                hash,
                direction: if dir == "L" {
                    merkle::ProofDirection::Left
                } else {
                    merkle::ProofDirection::Right
                },
            })
            .collect();
        merkle::MerkleTree::verify_proof(leaf_hash, &rust_proof, root_hash)
    }
}

/// CortexEncrypter Python wrapper
#[pyclass(name = "CortexEncrypter")]
struct PyCortexEncrypter {
    inner: crypto::CortexEncrypter,
}

#[pymethods]
impl PyCortexEncrypter {
    #[new]
    fn new(master_key: Option<Vec<u8>>) -> PyResult<Self> {
        let inner = crypto::CortexEncrypter::new(master_key)
            .map_err(PyValueError::new_err)?;
        Ok(PyCortexEncrypter { inner })
    }

    #[getter]
    fn is_active(&self) -> bool {
        self.inner.is_active()
    }

    #[pyo3(signature = (data, tenant_id="default"))]
    fn encrypt_str(&self, data: Option<&str>, tenant_id: &str) -> PyResult<Option<String>> {
        self.inner.encrypt_str(data, tenant_id).map_err(PyRuntimeError::new_err)
    }

    #[pyo3(signature = (encrypted_data, tenant_id="default"))]
    fn decrypt_str(&self, encrypted_data: Option<&str>, tenant_id: &str) -> PyResult<Option<String>> {
        self.inner.decrypt_str(encrypted_data, tenant_id).map_err(PyValueError::new_err)
    }
}

/// ZKSwarmIdentity Python wrapper
#[pyclass(name = "ZKSwarmIdentity")]
struct PyZKSwarmIdentity;

#[pymethods]
impl PyZKSwarmIdentity {
    #[staticmethod]
    fn generate_keypair() -> PyResult<(String, String)> {
        let kp = crypto::ZKSwarmIdentity::generate_keypair();
        Ok((kp.public_key_b64, kp.private_key_b64))
    }

    #[staticmethod]
    fn sign_payload(content: &str, private_key_b64: &str) -> PyResult<String> {
        crypto::ZKSwarmIdentity::sign_payload(content, private_key_b64)
            .map_err(PyValueError::new_err)
    }

    #[staticmethod]
    fn verify_payload(content: &str, public_key_b64: &str, signature_b64: &str) -> bool {
        crypto::ZKSwarmIdentity::verify_payload(content, public_key_b64, signature_b64)
    }
}

/// The main Python module.
#[pymodule]
fn cortex_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_tx_hash, m)?)?;
    m.add_function(wrap_pyfunction!(compute_tx_hash_v1, m)?)?;
    m.add_function(wrap_pyfunction!(compute_fact_hash, m)?)?;
    m.add_function(wrap_pyfunction!(canonical_json, m)?)?;
    
    m.add_class::<PyMerkleTree>()?;
    m.add_class::<PyCortexEncrypter>()?;
    m.add_class::<PyZKSwarmIdentity>()?;
    
    Ok(())
}
