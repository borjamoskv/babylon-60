// [C5-REAL] Exergy-Maximized
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalMetrics {
    pub cpu_cycles: u64,
    pub ram_alloc_bytes: u64,
    pub c5_real_outputs: u64,
    pub theoretical_complexity: u64,
}

impl SignalMetrics {
    /// Calculate Dynamic Exergy (Thermodynamic Enforcer)
    /// Exergy = (C5_Operaciones * 1000) / max(1, Ciclos_CPU * RAM_mb)
    /// High exergy means high signal per unit of thermodynamic cost.
    pub fn calculate_exergy(&self) -> f64 {
        let ram_mb = (self.ram_alloc_bytes as f64) / 1_048_576.0;
        let cost = (self.cpu_cycles as f64) * f64::max(1.0, ram_mb);
        
        // Apoptosis penalty for high theoretical complexity with zero output
        let epistemic_limerence_penalty = if self.c5_real_outputs == 0 && self.theoretical_complexity > 50 {
            0.1 // 90% reduction in exergy score
        } else {
            1.0
        };

        let base_exergy = (self.c5_real_outputs as f64 * 1000.0) / f64::max(1.0, cost);
        base_exergy * epistemic_limerence_penalty
    }

    pub fn requires_apoptosis(&self) -> bool {
        // If it runs but produces 0 C5 outcomes and takes more than 1M cycles
        if self.c5_real_outputs == 0 && self.cpu_cycles > 1_000_000 {
            return true;
        }
        
        // If the exergy is practically zero
        if self.calculate_exergy() < 0.0001 {
            return true;
        }

        false
    }
}

pub struct ExergyProbe {
    pub metrics: SignalMetrics,
}

impl ExergyProbe {
    pub fn new() -> Self {
        Self {
            metrics: SignalMetrics {
                cpu_cycles: 0,
                ram_alloc_bytes: 0,
                c5_real_outputs: 0,
                theoretical_complexity: 0,
            },
        }
    }

    pub fn record_cycle(&mut self, cycles: u64, ram: u64, c5_out: u64) {
        self.metrics.cpu_cycles += cycles;
        self.metrics.ram_alloc_bytes += ram;
        self.metrics.c5_real_outputs += c5_out;
    }
}
