use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, Component};

#[pyclass(eq, eq_int)]
#[derive(Clone, Debug, PartialEq)]
pub enum Confidence {
    C1, C2, C3, C4, C5,
}

impl Confidence {
    fn to_int(&self) -> i32 {
        match self {
            Confidence::C1 => 1,
            Confidence::C2 => 2,
            Confidence::C3 => 3,
            Confidence::C4 => 4,
            Confidence::C5 => 5,
        }
    }

    fn from_int(v: i32) -> Self {
        match v {
            v if v <= 1 => Confidence::C1,
            2 => Confidence::C2,
            3 => Confidence::C3,
            4 => Confidence::C4,
            _ => Confidence::C5,
        }
    }
}

#[pymethods]
impl Confidence {
    fn __repr__(&self) -> String { format!("{:?}", self) }
    fn __str__(&self) -> String { format!("{:?}", self) }
}

#[pyclass(eq, eq_int)]
#[derive(Clone, Debug, PartialEq)]
pub enum TaintStatus {
    Clean,
    Suspect,
    Tainted,
}

#[pymethods]
impl TaintStatus {
    fn __repr__(&self) -> String { format!("{:?}", self).to_lowercase() }
    fn __str__(&self) -> String { format!("{:?}", self).to_lowercase() }
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct FactNode {
    #[pyo3(get, set)]
    pub fact_id: String,
    #[pyo3(get, set)]
    pub confidence: Confidence,
    #[pyo3(get, set)]
    pub effective_confidence: Confidence,
    #[pyo3(get, set)]
    pub invalidated: bool,
    #[pyo3(get, set)]
    pub taint_status: TaintStatus,
    #[pyo3(get, set)]
    pub parents: Vec<String>,
    #[pyo3(get, set)]
    pub children: Vec<String>,
    #[pyo3(get, set)]
    pub source: Option<String>,
}

#[pymethods]
impl FactNode {
    #[new]
    #[pyo3(signature = (fact_id, confidence, effective_confidence, invalidated=false, taint_status=TaintStatus::Clean, parents=Vec::new(), children=Vec::new(), source=None))]
    fn new(
        fact_id: String,
        confidence: Confidence,
        effective_confidence: Confidence,
        invalidated: bool,
        taint_status: TaintStatus,
        parents: Vec<String>,
        children: Vec<String>,
        source: Option<String>,
    ) -> Self {
        FactNode {
            fact_id,
            confidence,
            effective_confidence,
            invalidated,
            taint_status,
            parents,
            children,
            source,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "FactNode(id={}, conf={:?}, effective={:?}, taint={:?}, source={:?})",
            self.fact_id, self.confidence, self.effective_confidence, self.taint_status, self.source
        )
    }
}

fn _downgrade_confidence(conf: &Confidence, steps: i32) -> Confidence {
    Confidence::from_int(conf.to_int() - steps)
}

#[pyfunction]
pub fn check_safe_path(base: String, path: String) -> bool {
    let base_path = Path::new(&base);
    let target_path = Path::new(&path);

    if target_path.is_absolute() && base_path.is_absolute() {
        return target_path.starts_with(base_path);
    }
    
    let mut depth: i32 = 0;
    for component in target_path.components() {
        match component {
            Component::Normal(_) => depth += 1,
            Component::ParentDir => depth -= 1,
            Component::CurDir => {},
            Component::RootDir => {
                 if !target_path.is_absolute() || !base_path.is_absolute() {
                     return false;
                 }
            },
            Component::Prefix(_) => return false,
        }
        if depth < 0 {
            return false;
        }
    }
    true
}

#[pyfunction]
pub fn propagate_taint(start_id: String, mut graph: HashMap<String, FactNode>) -> (HashSet<String>, HashMap<String, FactNode>) {
    let mut touched = HashSet::new();
    let mut queue = VecDeque::new();

    if let Some(start_node) = graph.get_mut(&start_id) {
        start_node.invalidated = true;
        start_node.taint_status = TaintStatus::Tainted;
        start_node.effective_confidence = Confidence::C1;
        queue.push_back(start_id.clone());
    } else {
        return (touched, graph);
    }

    while let Some(current_id) = queue.pop_front() {
        touched.insert(current_id.clone());
        
        let children = if let Some(node) = graph.get(&current_id) {
            node.children.clone()
        } else {
            continue;
        };

        for child_id in children {
            let (parent_count, tainted_parents, suspect_parents) = {
                if let Some(child) = graph.get(&child_id) {
                    let p_count = child.parents.len();
                    let mut t_count = 0;
                    let mut s_count = 0;
                    for pid in &child.parents {
                        if let Some(p) = graph.get(pid) {
                            match p.taint_status {
                                TaintStatus::Tainted => t_count += 1,
                                TaintStatus::Suspect => s_count += 1,
                                TaintStatus::Clean => {}
                            }
                        }
                    }
                    (p_count, t_count, s_count)
                } else {
                    continue;
                }
            };

            if let Some(child) = graph.get_mut(&child_id) {
                if child.taint_status == TaintStatus::Clean {
                    child.taint_status = TaintStatus::Suspect;
                }

                if parent_count > 0 && (tainted_parents as f32 / parent_count as f32) >= 0.5 {
                    child.taint_status = TaintStatus::Tainted;
                }

                if child.invalidated || child.taint_status == TaintStatus::Tainted {
                    child.effective_confidence = Confidence::C1;
                } else if tainted_parents > 0 {
                    child.effective_confidence = _downgrade_confidence(&child.confidence, 2);
                } else if suspect_parents > 0 {
                    child.effective_confidence = _downgrade_confidence(&child.confidence, 1);
                } else {
                    child.effective_confidence = child.confidence.clone();
                }

                if !touched.contains(&child_id) {
                    queue.push_back(child_id);
                }
            }
        }
    }

    (touched, graph)
}

#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Confidence>()?;
    m.add_class::<TaintStatus>()?;
    m.add_class::<FactNode>()?;
    m.add_function(wrap_pyfunction!(check_safe_path, m)?)?;
    m.add_function(wrap_pyfunction!(propagate_taint, m)?)?;
    Ok(())
}
