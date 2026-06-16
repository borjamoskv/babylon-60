pub mod atms;
pub mod auth;
pub mod belief_object;
pub mod belief_scheduler;
pub mod crdt_logop;
pub mod ctre_guardian;
pub mod smt;
pub mod storage_guard;
pub mod ultramap;
pub mod zenoh_orchestrator;
use atms::AtmsGraph;
use belief_object::{BeliefObject, BeliefRelation, BeliefState, ProvenanceEnvelope, RelationType};
use belief_scheduler::MemoryScheduler;
use crdt_logop::LogOpinionPool;
use pyo3::prelude::*;
use smt::{SmtLeaf, SparseMerkleTree};
use ultramap::UltramapSubstrate;
use zenoh_orchestrator::ZenohOrchestrator;

/// CORTEX-Persist Cognitive Core Rust Extension
#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<BeliefState>()?;
    m.add_class::<RelationType>()?;
    m.add_class::<ProvenanceEnvelope>()?;
    m.add_class::<BeliefRelation>()?;
    m.add_class::<BeliefObject>()?;
    m.add_class::<AtmsGraph>()?;
    m.add_class::<SmtLeaf>()?;
    m.add_class::<SparseMerkleTree>()?;
    m.add_class::<UltramapSubstrate>()?;
    m.add_class::<MemoryScheduler>()?;
    m.add_class::<LogOpinionPool>()?;
    m.add_class::<ZenohOrchestrator>()?;
    m.add_function(wrap_pyfunction!(storage_guard::validate_proposal, m)?)?;
    m.add_function(wrap_pyfunction!(storage_guard::detect_poisoning, m)?)?;
    m.add_function(wrap_pyfunction!(ctre_guardian::ctre_atomic_commit, m)?)?;
    m.add_function(wrap_pyfunction!(auth::hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(auth::verify_password, m)?)?;
    Ok(())
}
