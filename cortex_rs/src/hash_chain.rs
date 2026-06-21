// [C5-REAL] Exergy-Maximized
// B-8: Merkle Tree Batch Computation

use serde::{Deserialize, Serialize};
use sha3::{Digest, Sha3_256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MerkleRoot {
    pub root_hash: String,
    pub batch_id: String,
    pub leaves: Vec<String>,
}

pub fn compute_merkle_root(batch_id: &str, event_hashes: &[String]) -> MerkleRoot {
    if event_hashes.is_empty() {
        return MerkleRoot {
            root_hash: String::from("genesis"),
            batch_id: batch_id.to_string(),
            leaves: vec![],
        };
    }

    let mut current_level = event_hashes.to_vec();

    while current_level.len() > 1 {
        let mut next_level = Vec::new();
        for chunk in current_level.chunks(2) {
            let left = &chunk[0];
            let right = if chunk.len() > 1 { &chunk[1] } else { left };
            
            let mut hasher = Sha3_256::new();
            hasher.update(left.as_bytes());
            hasher.update(right.as_bytes());
            next_level.push(hex::encode(hasher.finalize()));
        }
        current_level = next_level;
    }

    MerkleRoot {
        root_hash: current_level[0].clone(),
        batch_id: batch_id.to_string(),
        leaves: event_hashes.to_vec(),
    }
}
