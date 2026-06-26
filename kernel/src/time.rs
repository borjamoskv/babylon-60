use core::fmt;

/// Untrusted wall clock time, mapped to Unix timestamp.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PhysicalClock(pub u64);

/// Instruction cycle counter within the VM. Strictly monotonic.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct LogicalClock(pub u64);

/// Mathematical simulation time (e.g., UNIT.TICK).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SimulationClock(pub u64);

impl PhysicalClock {
    pub const fn new(ms: u64) -> Self { Self(ms) }
}

impl LogicalClock {
    pub const fn new(ticks: u64) -> Self { Self(ticks) }
    pub fn tick(&mut self) { self.0 = self.0.saturating_add(1); }
}

impl SimulationClock {
    pub const fn new(units: u64) -> Self { Self(units) }
    pub fn advance(&mut self, units: u64) { self.0 = self.0.saturating_add(units); }
}
