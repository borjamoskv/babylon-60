use alloc::string::String;
use alloc::vec::Vec;
use crate::state::MachineState;
use crate::isa::{Instruction, Opcode, Value};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HaltReason {
    Graceful,
    Critical(String),
}

pub fn step(mut state: MachineState, instr: &Instruction) -> Result<MachineState, HaltReason> {
    state.logical_clock.tick();
    
    match &instr.opcode {
        Opcode::Alloc(reg_id, tag) => {
            if let Some(reg) = state.registers.get_mut(reg_id.0 as usize) {
                reg.tag = tag.clone();
            } else {
                return Err(HaltReason::Critical("Register out of bounds".into()));
            }
        }
        Opcode::Nig(reg_id, val) => {
            let eval_val = match val {
                Value::ImmI64(v) => Value::ImmI64(*v),
                Value::Reg(r) => {
                    if let Some(src) = state.registers.get(r.0 as usize) {
                        src.value.clone()
                    } else {
                        return Err(HaltReason::Critical("Register out of bounds".into()));
                    }
                }
            };
            if let Some(reg) = state.registers.get_mut(reg_id.0 as usize) {
                reg.value = eval_val;
            } else {
                return Err(HaltReason::Critical("Register out of bounds".into()));
            }
        }
        Opcode::Halt => return Err(HaltReason::Graceful),
        Opcode::CriticalHalt => return Err(HaltReason::Critical("Explicit critical halt".into())),
        // ... Implement other opcodes ...
        _ => {}
    }
    
    state.pc += 1;
    Ok(state)
}
