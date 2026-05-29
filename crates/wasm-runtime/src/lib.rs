use wasmtime::*;
use anyhow::Result;
use tracing::{info, warn};

/// ⚡ CORTEX WASM RUNTIME
/// Entorno de ejecución de latencia 0 para Agentes Ouroboros.
/// Los agentes son funciones puras compiladas a WebAssembly que 
/// consumen fricción y devuelven el delta de estado.

pub struct WasmAgentRuntime {
    engine: Engine,
    module: Module,
}

impl WasmAgentRuntime {
    /// Instancia el runtime cargando el binario .wasm de un agente
    pub fn new(wasm_bytes: &[u8]) -> Result<Self> {
        let mut config = Config::new();
        // Optimización extrema para ejecución efímera
        config.cranelift_opt_level(OptLevel::SpeedAndSize);
        config.epoch_interruption(true); // Previene ciclos infinitos en agentes

        let engine = Engine::new(&config)?;
        let module = Module::new(&engine, wasm_bytes)?;
        
        info!("🧬 WASM Agent Module cargado exitosamente en el engine.");
        Ok(Self { engine, module })
    }

    /// Interpreta un evento pasándolo al agente WASM
    /// (Skeleton API: Asume que el agente expone la función `process_friction`)
    pub fn interpret_friction(&self, event_payload: f64) -> Result<f64> {
        let mut store = Store::new(&self.engine, ());
        
        // Limitamos el tiempo de ejecución para evitar limerencia infinita
        store.set_epoch_deadline(1);

        // Instanciamos el módulo en la tienda de estado
        let instance = match Instance::new(&mut store, &self.module, &[]) {
            Ok(inst) => inst,
            Err(e) => {
                warn!("Fallo al instanciar agente WASM: {}", e);
                return Err(e);
            }
        };

        // Extraemos la función tipada pura: (fricción) -> delta_entropía
        let process_fn = instance.get_typed_func::<f64, f64>(&mut store, "process_friction")?;

        // Ejecutamos la función pura dentro del sandbox WASM
        let delta_entropy = process_fn.call(&mut store, event_payload)?;
        
        info!("Agente WASM devolvió delta de entropía: {}", delta_entropy);
        Ok(delta_entropy)
    }
}
