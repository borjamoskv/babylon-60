use proof_ir::{ProofIR, AbstractState, Invariant, ProofObligation};
use std::vec::Vec;

pub fn generate_proof_ir() -> ProofIR {
    ProofIR {
        state: AbstractState { variables: Vec::new() },
        invariants: Vec::new(),
        obligations: Vec::new(),
    }
}
