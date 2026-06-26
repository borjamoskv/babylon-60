use kernel::isa::Instruction;
use std::vec::Vec;

#[derive(Debug, Clone)]
pub struct AST {
    pub instructions: Vec<Instruction>,
}
