// CORTEX v8 — Merkle Tree (Rust substrate).
//
// Axiom Ω₂: "Merkle Trees reduce trust-cost from O(N) to O(log N)."

use crate::canonical::sha256_hex;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProofDirection {
    Left,
    Right,
}

#[derive(Debug, Clone)]
pub struct ProofStep {
    pub hash: String,
    pub direction: ProofDirection,
}

pub struct MerkleTree {
    root_hash: Option<String>,
    leaves: Vec<String>,
    layers: Vec<Vec<String>>,
}

impl MerkleTree {
    pub fn new(leaves: Vec<String>) -> Self {
        if leaves.is_empty() {
            return Self {
                root_hash: None,
                leaves: Vec::new(),
                layers: Vec::new(),
            };
        }

        let mut layers: Vec<Vec<String>> = Vec::new();
        let mut current = leaves.clone();
        layers.push(current.clone());

        while current.len() > 1 {
            let mut next = Vec::with_capacity((current.len() + 1) / 2);
            for i in (0..current.len()).step_by(2) {
                let left = &current[i];
                let right = if i + 1 < current.len() {
                    &current[i + 1]
                } else {
                    &current[i]
                };
                next.push(hash_pair(left, right));
            }
            layers.push(next.clone());
            current = next;
        }

        let root_hash = Some(current[0].clone());
        Self { root_hash, leaves, layers }
    }

    pub fn root_hash(&self) -> Option<&str> {
        self.root_hash.as_deref()
    }

    pub fn get_proof(&self, index: usize) -> Vec<ProofStep> {
        if self.leaves.is_empty() || index >= self.leaves.len() {
            return Vec::new();
        }

        let mut proof = Vec::new();
        let mut idx = index;

        for layer in &self.layers[..self.layers.len() - 1] {
            let sibling_idx = if idx % 2 == 0 { idx + 1 } else { idx - 1 };
            if sibling_idx < layer.len() {
                let direction = if idx % 2 == 0 {
                    ProofDirection::Right
                } else {
                    ProofDirection::Left
                };
                proof.push(ProofStep {
                    hash: layer[sibling_idx].clone(),
                    direction,
                });
            } else {
                proof.push(ProofStep {
                    hash: layer[idx].clone(),
                    direction: ProofDirection::Right,
                });
            }
            idx /= 2;
        }
        proof
    }

    pub fn verify_proof(leaf_hash: &str, proof: &[ProofStep], root_hash: &str) -> bool {
        let mut current = leaf_hash.to_string();
        for step in proof {
            current = match step.direction {
                ProofDirection::Left => hash_pair(&step.hash, &current),
                ProofDirection::Right => hash_pair(&current, &step.hash),
            };
        }
        current == root_hash
    }
}

#[inline]
fn hash_pair(left: &str, right: &str) -> String {
    sha256_hex(format!("{}{}", left, right).as_bytes())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_tree() {
        let tree = MerkleTree::new(vec![]);
        assert!(tree.root_hash().is_none());
    }

    #[test]
    fn test_single_leaf() {
        let tree = MerkleTree::new(vec!["abc".to_string()]);
        assert_eq!(tree.root_hash(), Some("abc"));
    }

    #[test]
    fn test_two_leaves_proof() {
        let tree = MerkleTree::new(vec!["aaa".to_string(), "bbb".to_string()]);
        let root = tree.root_hash().unwrap().to_string();
        let proof = tree.get_proof(0);
        assert!(MerkleTree::verify_proof("aaa", &proof, &root));
        assert!(!MerkleTree::verify_proof("wrong", &proof, &root));
    }

    #[test]
    fn test_odd_leaves() {
        let leaves = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let tree = MerkleTree::new(leaves);
        let root = tree.root_hash().unwrap().to_string();
        for i in 0..3 {
            let leaf = ["a", "b", "c"][i];
            let proof = tree.get_proof(i);
            assert!(MerkleTree::verify_proof(leaf, &proof, &root));
        }
    }
}
