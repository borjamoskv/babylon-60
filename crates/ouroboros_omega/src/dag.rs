// [C5-REAL] Exergy-Maximized
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OuroborosNode {
    pub hash: String,
    pub parent_hash: Option<String>,
    pub exergy_score: f64,
    pub executable_payload: Vec<u8>,
}

impl OuroborosNode {
    pub fn new(payload: Vec<u8>, parent_hash: Option<String>, exergy_score: f64) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(&payload);
        if let Some(ref p) = parent_hash {
            hasher.update(p.as_bytes());
        }
        let hash = hex::encode(hasher.finalize());

        Self {
            hash,
            parent_hash,
            exergy_score,
            executable_payload: payload,
        }
    }
}

pub struct MerkleDagStore {
    nodes: Arc<RwLock<HashMap<String, OuroborosNode>>>,
    head: Arc<RwLock<Option<String>>>,
}

impl MerkleDagStore {
    pub fn new() -> Self {
        Self {
            nodes: Arc::new(RwLock::new(HashMap::new())),
            head: Arc::new(RwLock::new(None)),
        }
    }

    pub fn insert(&self, node: OuroborosNode) {
        let hash = node.hash.clone();
        let current_head = { self.head.read().unwrap().clone() };

        // Exergy evaluation: only update head if exergy score improves
        // Lower entropy = Higher exergy. We assume exergy_score > 0 is better.
        let mut should_update_head = false;

        {
            let mut nodes = self.nodes.write().unwrap();
            
            // Apoptosis condition: If node exists and new exergy is worse, reject.
            if let Some(existing) = nodes.get(&hash) {
                if node.exergy_score <= existing.exergy_score {
                    return; // Reject mutation
                }
            }
            
            nodes.insert(hash.clone(), node.clone());

            if let Some(ref head_hash) = current_head {
                if let Some(head_node) = nodes.get(head_hash) {
                    if node.exergy_score > head_node.exergy_score {
                        should_update_head = true;
                    }
                }
            } else {
                should_update_head = true;
            }
        }

        if should_update_head {
            let mut head_lock = self.head.write().unwrap();
            *head_lock = Some(hash);
        }
    }

    pub fn get_head(&self) -> Option<OuroborosNode> {
        let head_hash = { self.head.read().unwrap().clone() };
        if let Some(h) = head_hash {
            let nodes = self.nodes.read().unwrap();
            nodes.get(&h).cloned()
        } else {
            None
        }
    }

    pub fn purge_dead_weight(&self, exergy_threshold: f64) -> usize {
        let mut nodes = self.nodes.write().unwrap();
        let initial_len = nodes.len();
        
        nodes.retain(|_, node| node.exergy_score >= exergy_threshold);
        
        initial_len - nodes.len()
    }
}
