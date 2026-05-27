use pyo3::prelude::*;
use rand::Rng;
use rayon::prelude::*;
use std::f32;

/// A HyperVector representing a concept in the Vector Symbolic Architecture (VSA).
#[pyclass]
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
    
    pub fn to_list<'py>(&self, py: Python<'py>) -> PyResult<Vec<f32>> {
        Ok(self.data.clone())
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

#[pyclass]
pub struct EpistemicMembrane {
    dim: usize,
    item_memory: Vec<HyperVector>,
    role_consistency: HyperVector,
    role_novelty: HyperVector,
    threshold_consistency: f32,
    threshold_novelty: f32,
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

    pub fn commit(&mut self, proposal_hv: HyperVector) {
        self.item_memory.push(proposal_hv);
    }
}

pub fn register(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<HyperVector>()?;
    m.add_class::<EpistemicMembrane>()?;
    m.add_function(wrap_pyfunction!(bind_sequence, m)?)?;
    m.add_function(wrap_pyfunction!(bundle_sequence, m)?)?;
    Ok(())
}
