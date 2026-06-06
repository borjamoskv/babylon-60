// [C5-REAL] Exergy-Maximized
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use sha2::{Sha256, Digest};
use std::collections::HashMap;

#[pyclass]
pub struct OuroborosStateAccumulator {
    leaves: Vec<[u8; 32]>,
    agent_indices: HashMap<String, usize>,
}

fn hash_leaf(agent_id: &str, state_json: &str) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(agent_id.as_bytes());
    hasher.update(state_json.as_bytes());
    let result = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&result);
    out
}

fn combine_hashes(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(left);
    hasher.update(right);
    let result = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&result);
    out
}

#[pymethods]
impl OuroborosStateAccumulator {
    #[new]
    pub fn new() -> Self {
        OuroborosStateAccumulator {
            leaves: Vec::new(),
            agent_indices: HashMap::new(),
        }
    }

    pub fn append_state(&mut self, agent_id: String, state_json: &str) -> usize {
        let hash = hash_leaf(&agent_id, state_json);
        let idx = self.leaves.len();
        self.leaves.push(hash);
        self.agent_indices.insert(agent_id, idx);
        idx
    }

    pub fn get_root(&self) -> String {
        if self.leaves.is_empty() {
            return hex::encode([0u8; 32]);
        }
        let mut current_level = self.leaves.clone();
        while current_level.len() > 1 {
            let mut next_level = Vec::new();
            for i in (0..current_level.len()).step_by(2) {
                if i + 1 < current_level.len() {
                    next_level.push(combine_hashes(&current_level[i], &current_level[i + 1]));
                } else {
                    // Duplicate last odd node
                    next_level.push(combine_hashes(&current_level[i], &current_level[i]));
                }
            }
            current_level = next_level;
        }
        hex::encode(current_level[0])
    }

    pub fn get_proof(&self, agent_id: &str) -> PyResult<Vec<String>> {
        let idx = match self.agent_indices.get(agent_id) {
            Some(&i) => i,
            None => return Err(PyValueError::new_err("Agent ID not found in accumulator")),
        };

        let mut proof = Vec::new();
        let mut current_idx = idx;
        let mut current_level = self.leaves.clone();

        while current_level.len() > 1 {
            let is_right = current_idx % 2 == 1;
            let sibling_idx = if is_right { current_idx - 1 } else { current_idx + 1 };

            if sibling_idx < current_level.len() {
                proof.push(hex::encode(current_level[sibling_idx]));
            } else {
                // Sibling is itself (odd tree size)
                proof.push(hex::encode(current_level[current_idx]));
            }

            let mut next_level = Vec::new();
            for i in (0..current_level.len()).step_by(2) {
                if i + 1 < current_level.len() {
                    next_level.push(combine_hashes(&current_level[i], &current_level[i + 1]));
                } else {
                    next_level.push(combine_hashes(&current_level[i], &current_level[i]));
                }
            }
            current_level = next_level;
            current_idx /= 2;
        }

        Ok(proof)
    }

    #[staticmethod]
    pub fn verify_proof(agent_id: &str, state_json: &str, proof: Vec<String>, index: usize, root_hex: &str) -> PyResult<bool> {
        let leaf_hash = hash_leaf(agent_id, state_json);
        let mut current_hash = leaf_hash;
        let mut current_idx = index;

        for sibling_hex in proof {
            let sibling_bytes = hex::decode(&sibling_hex)
                .map_err(|e| PyValueError::new_err(format!("Invalid sibling hex: {}", e)))?;
            if sibling_bytes.len() != 32 {
                return Err(PyValueError::new_err("Sibling hash must be 32 bytes"));
            }
            let mut sibling = [0u8; 32];
            sibling.copy_from_slice(&sibling_bytes);

            if current_idx % 2 == 1 {
                current_hash = combine_hashes(&sibling, &current_hash);
            } else {
                current_hash = combine_hashes(&current_hash, &sibling);
            }
            current_idx /= 2;
        }

        let computed_root = hex::encode(current_hash);
        Ok(computed_root == root_hex)
    }
}
