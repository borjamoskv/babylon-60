use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use serde::{Deserialize, Serialize};
use std::collections::{HashSet, HashMap};
use sha2::{Sha256, Digest};
use hex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Layer1State {
    pub added: HashSet<String>,
    pub removed: HashSet<String>,
    pub vector_clock: HashMap<String, u64>,
}

impl Layer1State {
    pub fn new() -> Self {
        Layer1State {
            added: HashSet::new(),
            removed: HashSet::new(),
            vector_clock: HashMap::new(),
        }
    }

    pub fn add(&mut self, hash: String, agent: String, time: u64) {
        self.added.insert(hash);
        let current = self.vector_clock.entry(agent).or_insert(0);
        if time > *current {
            *current = time;
        }
    }

    pub fn remove(&mut self, hash: String) {
        self.removed.insert(hash);
    }

    pub fn merge(&mut self, other: &Layer1State) {
        self.added.extend(other.added.iter().cloned());
        self.removed.extend(other.removed.iter().cloned());
        for (k, v) in &other.vector_clock {
            let current = self.vector_clock.entry(k.clone()).or_insert(0);
            if *v > *current {
                *current = *v;
            }
        }
    }

    pub fn active_elements(&self) -> Vec<String> {
        let mut active: Vec<String> = self.added.difference(&self.removed).cloned().collect();
        // Layer 2 Determinism: Canonical Sort
        active.sort();
        active
    }

    pub fn merkle_hash(&self) -> String {
        let active = self.active_elements();
        let mut hasher = Sha256::new();
        for item in active {
            hasher.update(item.as_bytes());
        }
        hex::encode(hasher.finalize())
    }
}

#[pyclass(module = "cortex_rs")]
#[derive(Debug, Clone)]
pub struct CRDTMergeState {
    state: Layer1State,
}

#[pymethods]
impl CRDTMergeState {
    #[new]
    pub fn new() -> Self {
        CRDTMergeState {
            state: Layer1State::new(),
        }
    }

    pub fn add_model(&mut self, model_hash: String, agent_id: String, time: u64) {
        self.state.add(model_hash, agent_id, time);
    }

    pub fn remove_model(&mut self, model_hash: String) {
        self.state.remove(model_hash);
    }

    pub fn merge_with_json(&mut self, other_json: &str) -> PyResult<()> {
        let other_state: Layer1State = serde_json::from_str(other_json)
            .map_err(|e| PyValueError::new_err(format!("Invalid state JSON: {}", e)))?;
        self.state.merge(&other_state);
        Ok(())
    }

    pub fn get_state_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.state)
            .map_err(|e| PyValueError::new_err(format!("Failed to serialize: {}", e)))
    }

    pub fn get_active_models(&self) -> Vec<String> {
        self.state.active_elements()
    }

    pub fn get_merkle_hash(&self) -> String {
        self.state.merkle_hash()
    }
}
