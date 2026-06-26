use alloc::vec::Vec;
use crate::time::{SimulationClock, LogicalClock};
use crate::ledger::DAGLedger;
use crate::isa::{TypeTag, Value};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Register {
    pub value: Value,
    pub tag: TypeTag,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MachineState {
    pub registers: Vec<Register>,
    pub pc: usize,
    pub sim_clock: SimulationClock,
    pub logical_clock: LogicalClock,
    pub ledger: DAGLedger,
    // Coroutine states and heap will be added here
}

impl MachineState {
    pub fn new(num_registers: usize) -> Self {
        Self {
            registers: alloc::vec![Register { value: Value::ImmI64(0), tag: TypeTag::Unallocated }; num_registers],
            pc: 0,
            sim_clock: SimulationClock::new(0),
            logical_clock: LogicalClock::new(0),
            ledger: DAGLedger::new(),
        }
    }
}
