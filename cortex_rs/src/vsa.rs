use pyo3::prelude::*;
use rand::Rng;
use std::f32;
use sha2::{Sha256, Digest};
use std::fs::OpenOptions;
use std::io::Write;

#[derive(Clone)]
pub struct MerkleTree {
    leaves: Vec<String>,
}

impl MerkleTree {
    pub fn new() -> Self {
        Self { leaves: Vec::new() }
    }

    pub fn push(&mut self, hash: String) {
        self.leaves.push(hash);
    }

    pub fn root(&self) -> String {
        if self.leaves.is_empty() {
            return "empty".to_string();
        }
        let mut current_level = self.leaves.clone();
        while current_level.len() > 1 {
            let mut next_level = Vec::new();
            for chunk in current_level.chunks(2) {
                let mut hasher = Sha256::new();
                hasher.update(chunk[0].as_bytes());
                if chunk.len() > 1 {
                    hasher.update(chunk[1].as_bytes());
                } else {
                    hasher.update(chunk[0].as_bytes());
                }
                next_level.push(hex::encode(hasher.finalize()));
            }
            current_level = next_level;
        }
        current_level[0].clone()
    }
}

/// A HyperVector representing a concept in the Vector Symbolic Architecture (VSA).
#[pyclass(from_py_object)]
#[derive(Clone, Debug, PartialEq)]
pub struct HyperVector {
    pub dim: usize,
    pub data: Vec<f32>,
}

#[pymethods]
impl HyperVector {
    #[new]
    pub fn new(dim: usize) -> Self {
        HyperVector {
            dim,
            data: vec![0.0; dim],
        }
    }

    /// Creates a random bipolar hypervector (-1.0 or 1.0)
    #[staticmethod]
    pub fn random(dim: usize) -> Self {
        let mut rng = rand::thread_rng();
        let data: Vec<f32> = (0..dim)
            .map(|_| if rng.gen_bool(0.5) { 1.0 } else { -1.0 })
            .collect();
        HyperVector { dim, data }
    }

    /// Binds this hypervector with another (element-wise multiplication)
    pub fn bind(&self, other: &HyperVector) -> PyResult<Self> {
        if self.dim != other.dim {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Dimensions must match for binding",
            ));
        }
        let data: Vec<f32> = self.data.iter().zip(other.data.iter()).map(|(a, b)| a * b).collect();
        Ok(HyperVector { dim: self.dim, data })
    }

    /// Bundles (adds) this hypervector with another
    pub fn bundle(&self, other: &HyperVector) -> PyResult<Self> {
        if self.dim != other.dim {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Dimensions must match for bundling",
            ));
        }
        let data: Vec<f32> = self.data.iter().zip(other.data.iter()).map(|(a, b)| a + b).collect();
        Ok(HyperVector { dim: self.dim, data })
    }

    /// Permutes (cyclic shift) the hypervector
    pub fn permute(&self, shifts: isize) -> Self {
        let mut data = self.data.clone();
        let len = data.len() as isize;
        if len == 0 {
            return self.clone();
        }
        let shift = ((shifts % len) + len) % len;
        let shift = shift as usize;
        data.rotate_right(shift);
        HyperVector { dim: self.dim, data }
    }

    /// Cosine similarity between two hypervectors
    pub fn similarity(&self, other: &HyperVector) -> PyResult<f32> {
        if self.dim != other.dim {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Dimensions must match for similarity",
            ));
        }
        let dot_product: f32 = self.data.iter().zip(other.data.iter()).map(|(a, b)| a * b).sum();
        let norm_a: f32 = self.data.iter().map(|a| a * a).sum::<f32>().sqrt();
        let norm_b: f32 = other.data.iter().map(|b| b * b).sum::<f32>().sqrt();
        if norm_a == 0.0 || norm_b == 0.0 {
            return Ok(0.0);
        }
        Ok(dot_product / (norm_a * norm_b))
    }
    
    pub fn to_list<'py>(&self, _py: Python<'py>) -> PyResult<Vec<f32>> {
        Ok(self.data.clone())
    }

    /// Computes the SHA-256 hash of the hypervector
    pub fn hash(&self) -> String {
        let mut hasher = Sha256::new();
        for val in &self.data {
            hasher.update(val.to_bits().to_le_bytes());
        }
        hex::encode(hasher.finalize())
    }
}

/// Binds multiple hypervectors together
#[pyfunction]
pub fn bind_sequence(vectors: Vec<HyperVector>) -> PyResult<HyperVector> {
    if vectors.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Empty sequence"));
    }
    let mut result = vectors[0].clone();
    for vec in vectors.iter().skip(1) {
        result = result.bind(vec)?;
    }
    Ok(result)
}

/// Bundles multiple hypervectors together
#[pyfunction]
pub fn bundle_sequence(vectors: Vec<HyperVector>) -> PyResult<HyperVector> {
    if vectors.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Empty sequence"));
    }
    let mut result = vectors[0].clone();
    for vec in vectors.iter().skip(1) {
        result = result.bundle(vec)?;
    }
    // Normalize after bundling
    let norm: f32 = result.data.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm > 0.0 {
        result.data.iter_mut().for_each(|v| *v /= norm);
    }
    Ok(result)
}

#[pyclass(skip_from_py_object)]
pub struct EpistemicMembrane {
    dim: usize,
    item_memory: Vec<HyperVector>,
    role_consistency: HyperVector,
    role_novelty: HyperVector,
    threshold_consistency: f32,
    #[allow(dead_code)]
    threshold_novelty: f32,
    merkle: MerkleTree,
}

#[pymethods]
impl EpistemicMembrane {
    #[new]
    pub fn new(dim: usize) -> Self {
        EpistemicMembrane {
            dim,
            item_memory: Vec::new(),
            role_consistency: HyperVector::random(dim),
            role_novelty: HyperVector::random(dim),
            threshold_consistency: 0.65,
            threshold_novelty: 0.35,
            merkle: MerkleTree::new(),
        }
    }

    pub fn encode_episode(&self, components: Vec<(String, HyperVector)>) -> PyResult<HyperVector> {
        let mut hv = HyperVector::new(self.dim);
        for (role_name, filler) in components {
            let role = if role_name == "consistency" {
                self.role_consistency.clone()
            } else if role_name == "novelty" {
                self.role_novelty.clone()
            } else {
                HyperVector::random(self.dim)
            };
            let bound = role.bind(&filler)?;
            hv = hv.bundle(&bound)?;
        }
        let norm: f32 = hv.data.iter().map(|v| v * v).sum::<f32>().sqrt();
        if norm > 0.0 {
            hv.data.iter_mut().for_each(|v| *v /= norm);
        }
        Ok(hv)
    }

    pub fn check_proposal<'py>(&self, py: Python<'py>, proposal_hv: &HyperVector) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);
        if self.item_memory.is_empty() {
            dict.set_item("accept", true)?;
            dict.set_item("reason", "empty_history")?;
            return Ok(dict);
        }

        let mut max_sim: f32 = -1.0;
        let mut sum_sim: f32 = 0.0;
        let mut nearest_idx: usize = 0;

        for (i, mem_hv) in self.item_memory.iter().enumerate() {
            let sim = proposal_hv.similarity(mem_hv)?;
            sum_sim += sim;
            if sim > max_sim {
                max_sim = sim;
                nearest_idx = i;
            }
        }

        let avg_sim = sum_sim / self.item_memory.len() as f32;
        let consistency = max_sim > self.threshold_consistency;
        let is_novel = avg_sim < 0.9;
        let accept = consistency && is_novel;

        dict.set_item("accept", accept)?;
        dict.set_item("max_similarity", max_sim)?;
        dict.set_item("avg_similarity", avg_sim)?;
        dict.set_item("nearest", nearest_idx)?;
        dict.set_item("reason", if accept { "consistent_novel" } else { "inconsistent_or_redundant" })?;

        Ok(dict)
    }

    pub fn commit(&mut self, proposal_hv: HyperVector) -> PyResult<String> {
        let h_hash = proposal_hv.hash();
        self.merkle.push(h_hash.clone());
        let root_hash = self.merkle.root();
        
        // C5-REAL: Cryptographic append-only ledger
        if let Ok(mut file) = OpenOptions::new()
            .create(true)
            .append(true)
            .open("cortex_ledger.jsonl")
        {
            let timestamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            let log_entry = format!("{{\"timestamp\": {}, \"hash\": \"{}\", \"root_hash\": \"{}\", \"dim\": {}}}\n",
                timestamp,
                h_hash,
                root_hash,
                proposal_hv.dim
            );
            let _ = file.write_all(log_entry.as_bytes());
        }

        self.item_memory.push(proposal_hv);
        Ok(root_hash)
    }

    pub fn consolidate_memory(&mut self) -> PyResult<usize> {
        if self.item_memory.is_empty() {
            return Ok(0);
        }
        
        let mut unique_memories = Vec::new();
        // Bundle everything to get the "core consensus" of current memory
        let mut consensus = self.item_memory[0].clone();
        for mem in self.item_memory.iter().skip(1) {
            consensus = consensus.bundle(mem)?;
        }
        
        // Normalize consensus
        let norm: f32 = consensus.data.iter().map(|v| v * v).sum::<f32>().sqrt();
        if norm > 0.0 {
            consensus.data.iter_mut().for_each(|v| *v /= norm);
        }
        
        unique_memories.push(consensus);
        
        for mem in self.item_memory.iter() {
            let mut is_redundant = false;
            for unique in unique_memories.iter() {
                if mem.similarity(unique)? > 0.85 {
                    is_redundant = true;
                    break;
                }
            }
            if !is_redundant && unique_memories.len() < 15 {
                unique_memories.push(mem.clone());
            }
        }
        
        let purged = self.item_memory.len() - unique_memories.len();
        self.item_memory = unique_memories;
        Ok(purged)
    }
}

pub fn register(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HyperVector>()?;
    m.add_class::<EpistemicMembrane>()?;
    m.add_function(wrap_pyfunction!(bind_sequence, m)?)?;
    m.add_function(wrap_pyfunction!(bundle_sequence, m)?)?;
    Ok(())
}
