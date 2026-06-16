use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Semantic CRDT Logarithmic Opinion Pool (LogOP)
/// Implements Coordination Plane consensus without probability flattening
/// according to the CORTEX-NATIVE-ARCHITECTURE Doctrine.
#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogOpinionPool {
    #[pyo3(get, set)]
    pub dimensions: usize,
    pub opinions: Vec<f64>,
    pub weights: Vec<f64>,
}

#[pymethods]
impl LogOpinionPool {
    #[new]
    pub fn new(dimensions: usize) -> Self {
        LogOpinionPool {
            dimensions,
            opinions: Vec::new(),
            weights: Vec::new(),
        }
    }

    /// Add an opinion (vector of probabilities) with a given structural weight
    pub fn add_opinion(&mut self, opinion: Vec<f64>, weight: f64) -> PyResult<bool> {
        if opinion.len() != self.dimensions {
            return Err(pyo3::exceptions::PyValueError::new_err("Dimension mismatch in LogOP"));
        }
        
        self.opinions.extend(opinion);
        self.weights.push(weight);
        Ok(true)
    }

    /// Aggregate using LogOP to prevent probability flattening.
    /// P(x) \propto \prod_i P_i(x)^{w_i}
    pub fn aggregate(&self) -> PyResult<Vec<f64>> {
        if self.weights.is_empty() {
            return Ok(vec![0.0; self.dimensions]);
        }

        let num_opinions = self.weights.len();
        let mut aggregated = vec![0.0; self.dimensions];
        let mut sum = 0.0;

        for d in 0..self.dimensions {
            let mut prod = 1.0;
            for i in 0..num_opinions {
                let p = self.opinions[i * self.dimensions + d];
                let w = self.weights[i];
                prod *= p.powf(w);
            }
            aggregated[d] = prod;
            sum += prod;
        }

        // Normalize probability distribution
        if sum > 0.0 {
            for d in 0..self.dimensions {
                aggregated[d] /= sum;
            }
        }

        Ok(aggregated)
    }
}
