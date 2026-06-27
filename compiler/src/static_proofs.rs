use proof_ir::{AbstractState, ProofIR};
use std::vec::Vec;

pub fn generate_proof_ir() -> ProofIR {
    ProofIR {
        state: AbstractState {
            variables: Vec::new(),
        },
        invariants: Vec::new(),
        obligations: Vec::new(),
    }
}
