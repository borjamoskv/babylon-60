use std::collections::{HashMap, HashSet};
use pyo3::prelude::*;

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct AtmsGraph {
    pub nodes: HashSet<String>,
    pub dependencies: HashMap<String, Vec<String>>, // Child -> Parents (DependsOn)
    pub entails: HashMap<String, Vec<String>>,      // Parent -> Children (Entails)
    pub conflicts: HashMap<String, Vec<String>>,    // Node -> Conflicting nodes
}

impl Default for AtmsGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl AtmsGraph {
    #[new]
    pub fn new() -> Self {
        AtmsGraph {
            nodes: HashSet::new(),
            dependencies: HashMap::new(),
            entails: HashMap::new(),
            conflicts: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node_id_str: &str) -> PyResult<()> {
        self.nodes.insert(node_id_str.to_string());
        Ok(())
    }

    pub fn add_dependency(&mut self, child_str: &str, parent_str: &str) -> PyResult<()> {
        let child = child_str.to_string();
        let parent = parent_str.to_string();
        
        self.dependencies.entry(child.clone()).or_default().push(parent.clone());
        self.entails.entry(parent).or_default().push(child);
        Ok(())
    }

    #[pyo3(name = "invalidate_cascade")]
    pub fn invalidate_cascade(&mut self, root_id: &str) -> Vec<String> {
        use std::collections::VecDeque;

        let mut queue = VecDeque::new();
        let mut invalidated = Vec::new();
        let mut visited = HashSet::new();

        if self.nodes.contains(root_id) {
            queue.push_back(root_id.to_string());
            visited.insert(root_id.to_string());
        }

        while let Some(current) = queue.pop_front() {
            self.nodes.remove(&current);
            invalidated.push(current.clone());

            if let Some(children) = self.entails.get(&current) {
                for child in children {
                    if !visited.contains(child) {
                        visited.insert(child.clone());
                        queue.push_back(child.clone());
                    }
                }
            }
        }

        // Clean up from the graph
        for node in &invalidated {
            self.dependencies.remove(node);
            self.entails.remove(node);
            self.conflicts.remove(node);
        }

        for deps in self.dependencies.values_mut() {
            deps.retain(|x| !visited.contains(x));
        }
        for ents in self.entails.values_mut() {
            ents.retain(|x| !visited.contains(x));
        }
        for confs in self.conflicts.values_mut() {
            confs.retain(|x| !visited.contains(x));
        }

        invalidated
    }
}

