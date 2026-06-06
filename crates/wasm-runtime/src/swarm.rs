// [C5-REAL] Exergy-Maximized
use crate::WasmAgentRuntime;
use anyhow::Result;
use tracing::{info, warn};
use std::collections::HashMap;

/// Gestor del Enjambre WASM (Ciclo Ouroboros)
/// Mantiene N agentes WASM instanciados y distribuye la fricción.
pub struct WasmSwarm {
    agents: HashMap<String, WasmAgentRuntime>,
}

impl WasmSwarm {
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    /// Despliega o reemplaza un agente en el enjambre
    pub fn spawn_agent(&mut self, agent_id: String, wasm_bytes: &[u8]) -> Result<()> {
        let runtime = WasmAgentRuntime::new(wasm_bytes)?;
        self.agents.insert(agent_id.clone(), runtime);
        info!("Agente {} cristalizado en WASM y añadido al enjambre.", agent_id);
        Ok(())
    }

    /// Purgado térmico: Elimina un agente del enjambre
    pub fn kill_agent(&mut self, agent_id: &str) {
        if self.agents.remove(agent_id).is_some() {
            warn!("Agente {} aniquilado estructuralmente (Pruning).", agent_id);
        }
    }

    /// Ciclo de fricción: Inyecta señal en el agente y devuelve la entropía resultante
    pub fn cycle_friction(&self, agent_id: &str, friction_signal: f64) -> Result<f64> {
        if let Some(agent) = self.agents.get(agent_id) {
            let delta = agent.interpret_friction(friction_signal)?;
            Ok(delta)
        } else {
            anyhow::bail!("Agente {} no existe en el enjambre (posiblemente purgado).", agent_id)
        }
    }
    
    /// Retorna la cuenta actual de agentes activos
    pub fn active_count(&self) -> usize {
        self.agents.len()
    }
}
