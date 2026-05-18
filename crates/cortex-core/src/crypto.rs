// CORTEX v8 — Cryptographic Security (Rust substrate).
//
// Application-level encryption and Zero-Knowledge Data.
// Implements AES-256-GCM and Ed25519 signatures.

use aes_gcm::aead::{Aead, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Nonce};
use ed25519_dalek::{Signer, Verifier};
use hkdf::Hkdf;
use rand::RngCore;
use sha2::Sha256;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use base64::{Engine as _, engine::general_purpose::STANDARD};

const NONCE_LENGTH: usize = 12; // 96-bit nonce for GCM
const KEY_LENGTH: usize = 32;   // 256-bit AES key
const PREFIX: &str = "v6_aesgcm:";

/// Zero-Knowledge Data Encrypter for DB rows.
/// Uses AES-256-GCM.
pub struct CortexEncrypter {
    master_key: Option<Vec<u8>>,
    tenant_keys: Arc<Mutex<HashMap<String, Vec<u8>>>>,
}

impl CortexEncrypter {
    /// Create a new encrypter with the given master key.
    pub fn new(master_key: Option<Vec<u8>>) -> Result<Self, String> {
        if let Some(ref key) = master_key {
            if key.len() != KEY_LENGTH {
                return Err(format!("AES-256 requires a {}-byte master key.", KEY_LENGTH));
            }
        }
        Ok(Self {
            master_key,
            tenant_keys: Arc::new(Mutex::new(HashMap::new())),
        })
    }

    pub fn is_active(&self) -> bool {
        self.master_key.is_some()
    }

    /// Derive a tenant-specific 32-byte key using HKDF over the master key.
    fn get_tenant_key(&self, tenant_id: &str) -> Result<Vec<u8>, String> {
        if !self.is_active() {
            return Err("Cannot derive key without a Master Key.".to_string());
        }

        let mut cache = self.tenant_keys.lock().unwrap();
        if let Some(key) = cache.get(tenant_id) {
            return Ok(key.clone());
        }

        let master_key = self.master_key.as_ref().unwrap();
        let hkdf = Hkdf::<Sha256>::new(Some(b"cortex_v6_tenant_isolation_salt"), master_key);
        let mut tenant_key = vec![0u8; KEY_LENGTH];
        hkdf.expand(tenant_id.as_bytes(), &mut tenant_key)
            .map_err(|e| format!("HKDF expand failed: {:?}", e))?;

        cache.insert(tenant_id.to_string(), tenant_key.clone());
        Ok(tenant_key)
    }

    /// Encrypt a string and return a safe Base64 representation.
    pub fn encrypt_str(&self, data: Option<&str>, tenant_id: &str) -> Result<Option<String>, String> {
        let data = match data {
            Some(d) if !d.is_empty() => d,
            _ => return Ok(data.map(|s| s.to_string())),
        };

        let key_bytes = self.get_tenant_key(tenant_id)?;
        let cipher = Aes256Gcm::new_from_slice(&key_bytes)
            .map_err(|e| format!("Invalid key length: {:?}", e))?;

        let mut nonce_bytes = [0u8; NONCE_LENGTH];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher.encrypt(nonce, data.as_bytes())
            .map_err(|e| format!("Encryption failed: {:?}", e))?;

        let mut combined = Vec::with_capacity(NONCE_LENGTH + ciphertext.len());
        combined.extend_from_slice(&nonce_bytes);
        combined.extend_from_slice(&ciphertext);

        let b64 = STANDARD.encode(&combined);
        Ok(Some(format!("{}{}", PREFIX, b64)))
    }

    /// Decrypt a Base64 string back into plaintext.
    pub fn decrypt_str(&self, encrypted_data: Option<&str>, tenant_id: &str) -> Result<Option<String>, String> {
        let encrypted = match encrypted_data {
            Some(e) if !e.is_empty() => e,
            _ => return Ok(encrypted_data.map(|s| s.to_string())),
        };

        if !encrypted.starts_with(PREFIX) {
            return Ok(Some(encrypted.to_string()));
        }

        if !self.is_active() {
            return Err("Database contains encrypted data but no Master Key is loaded.".to_string());
        }

        let raw_b64 = &encrypted[PREFIX.len()..];
        let combined = STANDARD.decode(raw_b64)
            .map_err(|e| format!("Base64 decode failed: {:?}", e))?;

        if combined.len() < NONCE_LENGTH {
            return Err("Corrupted data: too short for nonce".to_string());
        }

        let (nonce_bytes, ciphertext) = combined.split_at(NONCE_LENGTH);
        let nonce = Nonce::from_slice(nonce_bytes);

        let key_bytes = self.get_tenant_key(tenant_id)?;
        let cipher = Aes256Gcm::new_from_slice(&key_bytes)
            .map_err(|e| format!("Invalid key length: {:?}", e))?;

        let plaintext_bytes = cipher.decrypt(nonce, ciphertext)
            .map_err(|e| format!("Decryption failed for tenant '{}'. Possible cross-tenant access attempt or corrupted data: {:?}", tenant_id, e))?;

        let plaintext = String::from_utf8(plaintext_bytes)
            .map_err(|e| format!("Invalid UTF-8 in decrypted data: {:?}", e))?;

        Ok(Some(plaintext))
    }
}

/// The local identity of an autonomous agent.
#[derive(Debug, Clone)]
pub struct AgentKeyPair {
    pub public_key_b64: String,
    pub private_key_b64: String,
}

/// Manages cryptographic signing and verification for the CORTEX ZK-Swarm.
pub struct ZKSwarmIdentity;

impl ZKSwarmIdentity {
    pub fn generate_keypair() -> AgentKeyPair {
        let mut csprng = OsRng;
        let keypair = ed25519_dalek::SigningKey::generate(&mut csprng);
        let public_key = keypair.verifying_key();

        AgentKeyPair {
            public_key_b64: STANDARD.encode(public_key.as_bytes()),
            private_key_b64: STANDARD.encode(keypair.to_bytes()),
        }
    }

    pub fn sign_payload(content: &str, private_key_b64: &str) -> Result<String, String> {
        let priv_bytes = STANDARD.decode(private_key_b64)
            .map_err(|e| format!("Invalid base64 private key: {:?}", e))?;
        
        let signing_key = ed25519_dalek::SigningKey::from_bytes(
            priv_bytes.as_slice().try_into().map_err(|_| "Private key must be 32 bytes")?
        );

        use sha2::Digest;
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        let content_hash = hasher.finalize();

        let signature = signing_key.sign(&content_hash);
        Ok(STANDARD.encode(signature.to_bytes()))
    }

    pub fn verify_payload(content: &str, public_key_b64: &str, signature_b64: &str) -> bool {
        let pub_bytes = match STANDARD.decode(public_key_b64) {
            Ok(b) => b,
            Err(_) => return false,
        };
        let verifying_key = match ed25519_dalek::VerifyingKey::from_bytes(
            pub_bytes.as_slice().try_into().unwrap_or(&[0; 32])
        ) {
            Ok(k) => k,
            Err(_) => return false,
        };

        let sig_bytes = match STANDARD.decode(signature_b64) {
            Ok(b) => b,
            Err(_) => return false,
        };
        let signature = ed25519_dalek::Signature::from_bytes(
            sig_bytes.as_slice().try_into().unwrap_or(&[0; 64])
        );

        use sha2::Digest;
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        let content_hash = hasher.finalize();

        verifying_key.verify(&content_hash, &signature).is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_decryption() {
        let master_key = vec![42u8; 32];
        let encrypter = CortexEncrypter::new(Some(master_key)).unwrap();

        let plaintext = "Top secret agent data";
        let tenant = "tenant_1";

        let encrypted = encrypter.encrypt_str(Some(plaintext), tenant).unwrap().unwrap();
        assert!(encrypted.starts_with(PREFIX));
        assert_ne!(encrypted, plaintext);

        let decrypted = encrypter.decrypt_str(Some(&encrypted), tenant).unwrap().unwrap();
        assert_eq!(decrypted, plaintext);
    }

    #[test]
    fn test_cross_tenant_isolation() {
        let master_key = vec![42u8; 32];
        let encrypter = CortexEncrypter::new(Some(master_key)).unwrap();

        let plaintext = "Top secret agent data";
        let encrypted = encrypter.encrypt_str(Some(plaintext), "tenant_A").unwrap().unwrap();

        // Decrypting with wrong tenant should fail
        let result = encrypter.decrypt_str(Some(&encrypted), "tenant_B");
        assert!(result.is_err());
    }

    #[test]
    fn test_sign_verify() {
        let keypair = ZKSwarmIdentity::generate_keypair();
        let payload = "deploy_contract_v2";

        let signature = ZKSwarmIdentity::sign_payload(payload, &keypair.private_key_b64).unwrap();
        
        // Verify with correct key
        assert!(ZKSwarmIdentity::verify_payload(payload, &keypair.public_key_b64, &signature));
        
        // Verify with wrong payload
        assert!(!ZKSwarmIdentity::verify_payload("deploy_contract_v3", &keypair.public_key_b64, &signature));
    }
}
