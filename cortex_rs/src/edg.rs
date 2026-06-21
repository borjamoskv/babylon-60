use dashmap::DashMap;
use pyo3::prelude::*;
use std::collections::HashSet;
use std::sync::Arc;
use crate::bft::exergy::{ExergyMutation, ExergyGuard, ExergyError};

#[pyclass]
#[derive(Clone, Debug, PartialEq)]
pub enum ValidationStatus {
    Accepted,
    Challenged,
    Deprecated,
    Invalid,
}

#[pyclass]
#[derive(Clone)]
pub struct RetrievalNode {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get, set)]
    pub status: ValidationStatus,
    #[pyo3(get, set)]
    pub confidence: f64,
    // dependencies: Nodes this node supports
    pub supported_by: HashSet<String>,
    // supports: Nodes that support this node
    pub supports: HashSet<String>,
    #[pyo3(get, set)]
    pub exergy: f64,
    #[pyo3(get, set)]
    pub rul_claim_id: Option<String>,
}

#[pymethods]
impl RetrievalNode {
    #[new]
    pub fn new(id: String, confidence: f64) -> Self {
        RetrievalNode {
            id,
            status: ValidationStatus::Accepted,
            confidence,
            supported_by: HashSet::new(),
            supports: HashSet::new(),
            exergy: 0.0,
            rul_claim_id: None,
        }
    }

    #[getter]
    pub fn get_supported_by(&self) -> Vec<String> {
        self.supported_by.iter().cloned().collect()
    }

    #[getter]
    pub fn get_supports(&self) -> Vec<String> {
        self.supports.iter().cloned().collect()
    }
}

#[pyclass]
pub struct RetrievalGraph {
    pub(crate) nodes: Arc<DashMap<String, RetrievalNode>>,
}

#[pymethods]
impl RetrievalGraph {
    #[new]
    pub fn new() -> Self {
        RetrievalGraph {
            nodes: Arc::new(DashMap::new()),
        }
    }

    pub fn add_node(&self, node: RetrievalNode) {
        self.nodes.insert(node.id.clone(), node);
    }

    pub fn get_node_status(&self, node_id: &str) -> Option<ValidationStatus> {
        self.nodes.get(node_id).map(|n| n.status.clone())
    }

    pub fn add_dependency(&self, supporter_id: &str, supported_id: &str) -> PyResult<()> {
        // Supporter supports Supported
        if let Some(mut supporter) = self.nodes.get_mut(supporter_id) {
            supporter.supports.insert(supported_id.to_string());
        } else {
            return Err(pyo3::exceptions::PyKeyError::new_err(format!(
                "Node not found: {}",
                supporter_id
            )));
        }

        if let Some(mut supported) = self.nodes.get_mut(supported_id) {
            supported.supported_by.insert(supporter_id.to_string());
        } else {
            return Err(pyo3::exceptions::PyKeyError::new_err(format!(
                "Node not found: {}",
                supported_id
            )));
        }

        Ok(())
    }

    pub fn invalidate_node(&self, node_id: &str) -> Vec<String> {
        let mut affected = Vec::new();
        let mut stack = vec![node_id.to_string()];

        while let Some(current_id) = stack.pop() {
            if let Some(mut node) = self.nodes.get_mut(&current_id) {
                if node.status != ValidationStatus::Invalid {
                    node.status = ValidationStatus::Invalid;
                    node.confidence = 0.0;
                    affected.push(current_id.clone());

                    // Propagate invalidation to all nodes that this node supports
                    for supported_id in &node.supports {
                        stack.push(supported_id.clone());
                    }
                }
            }
        }

        affected
    }
}

impl RetrievalGraph {
    pub fn apply_exergy_mutation(
        &self,
        mutation: &ExergyMutation,
        guard: &ExergyGuard,
    ) -> Result<(), ExergyError> {
        let valid_nodes: Vec<String> = self.nodes.iter().map(|kv| kv.key().clone()).collect();
        guard.validate(mutation, &valid_nodes)?;
        if let Some(mut node) = self.nodes.get_mut(&mutation.node_id) {
            node.exergy += mutation.delta;
            if mutation.rul_claim_id.is_some() {
                node.rul_claim_id = mutation.rul_claim_id.clone();
            }
            Ok(())
        } else {
            Err(ExergyError::NodeNotFound {
                id: mutation.node_id.clone(),
            })
        }
    }
}
