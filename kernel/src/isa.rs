use alloc::string::String;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct RegisterId(pub u8);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TypeTag {
    I64,
    F60,
    Time,
    Unallocated,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Value {
    ImmI64(i64),
    Reg(RegisterId),
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Opcode {
    /// Allocate Register Type
    Alloc(RegisterId, TypeTag),
    /// Assign
    Nig(RegisterId, Value),
    /// Add
    Dah(RegisterId, Value),
    /// Sub
    Lal(RegisterId, Value),
    /// Mul
    Ara(RegisterId, Value),
    /// Div
    Ba(RegisterId, Value),
    /// Fork execution
    Fork(String),
    /// Await symbol
    Await(String),
    /// Suspend execution for ticks
    After(RegisterId, String),
    /// Emit to Ledger
    Execute(String),
    /// Read to output (Effectful, moved to boundary)
    Sar(RegisterId),
    SarB60(RegisterId),
    /// Terminate gracefully
    Halt,
    /// Critical halt (assertion failed, math error)
    CriticalHalt,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Instruction {
    pub opcode: Opcode,
}
