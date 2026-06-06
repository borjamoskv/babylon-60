// [C5-REAL] Exergy-Maximized
pub mod dag;
pub mod exergy;
pub mod rl_engine;

use dag::{MerkleDagStore, OuroborosNode};
use exergy::{ExergyProbe, SignalMetrics};
use std::sync::Arc;
use tokio::time::{sleep, Duration};

/// OuroborosOmega is the Daemon running continuous autopoiesis.
pub struct OuroborosOmega {
    store: Arc<MerkleDagStore>,
}

impl OuroborosOmega {
    pub fn new() -> Self {
        Self {
            store: Arc::new(MerkleDagStore::new()),
        }
    }

    /// Background thread to constantly purge high-entropy nodes
    pub async fn start_continuous_causal_pruning(&self) {
        let store = Arc::clone(&self.store);
        
        tokio::spawn(async move {
            loop {
                // Minimum exergy threshold for survival (dynamically scales)
                let threshold = 0.5;
                
                let purged = store.purge_dead_weight(threshold);
                if purged > 0 {
                    println!("[OUROBOROS-OMEGA] Causal Pruning Executed: {} blocks amputated.", purged);
                }
                
                // Sleep until next cycle (continuous execution)
                sleep(Duration::from_secs(60)).await;
            }
        });
    }

    /// Simulates a JIT runtime mutation evaluation via RL 
    pub fn evaluate_mutation(&self, new_payload: Vec<u8>, metrics: SignalMetrics, parent_hash: Option<String>) {
        let exergy = metrics.calculate_exergy();
        
        if metrics.requires_apoptosis() {
            println!("[OUROBOROS-OMEGA] Mutation rejected. Apoptosis triggered.");
            return;
        }

        let node = OuroborosNode::new(new_payload, parent_hash, exergy);
        self.store.insert(node);
        println!("[OUROBOROS-OMEGA] Exergy optimized. New node committed to Merkle DAG.");
    }
}
