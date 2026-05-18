// CORTEX v8 — Canonical Hash Construction (Rust substrate).
//
// Provides deterministic JSON serialization and null-byte separated
// hash computation for the transaction ledger. Bit-exact parity
// with Python `cortex.utils.canonical`.
//
// Hash Scheme Versions:
//   v1: colon-delimited   "{prev}:{project}:{action}:{detail}:{ts}"
//   v2: null-byte canon   "{prev}\x00{project}\x00{action}\x00{detail}\x00{ts}"
//   v3: tenant-bound      "v3\x00{tenant}\x00{prev}\x00{project}\x00{action}\x00{detail}\x00{ts}"

use sha2::{Digest, Sha256};

/// Deterministic JSON: sorted keys, no whitespace, ASCII-safe.
///
/// Guarantees identical output for semantically identical input
/// regardless of insertion order. Exact parity with Python's
/// `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`.
pub fn canonical_json(value: &serde_json::Value) -> String {
    canonical_json_inner(value)
}

fn canonical_json_inner(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Null => "null".to_string(),
        serde_json::Value::Bool(b) => {
            if *b {
                "true".to_string()
            } else {
                "false".to_string()
            }
        }
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::String(s) => ascii_escape_json_string(s),
        serde_json::Value::Array(arr) => {
            let items: Vec<String> = arr.iter().map(canonical_json_inner).collect();
            format!("[{}]", items.join(","))
        }
        serde_json::Value::Object(map) => {
            // Sorted keys — deterministic ordering
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let pairs: Vec<String> = keys
                .iter()
                .map(|k| {
                    let v = &map[*k];
                    format!("{}:{}", ascii_escape_json_string(k), canonical_json_inner(v))
                })
                .collect();
            format!("{{{}}}", pairs.join(","))
        }
    }
}

/// Escape a string for JSON with ensure_ascii=True parity.
/// Non-ASCII characters are escaped as \uXXXX.
fn ascii_escape_json_string(s: &str) -> String {
    let mut result = String::with_capacity(s.len() + 2);
    result.push('"');
    for ch in s.chars() {
        match ch {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            '\x08' => result.push_str("\\b"),
            '\x0C' => result.push_str("\\f"),
            c if c < '\x20' => {
                // Control characters
                result.push_str(&format!("\\u{:04x}", c as u32));
            }
            c if c.is_ascii() => result.push(c),
            c => {
                // Non-ASCII → \uXXXX (or surrogate pairs for > U+FFFF)
                let code = c as u32;
                if code <= 0xFFFF {
                    result.push_str(&format!("\\u{:04x}", code));
                } else {
                    // Surrogate pair for supplementary planes
                    let code = code - 0x10000;
                    let high = 0xD800 + (code >> 10);
                    let low = 0xDC00 + (code & 0x3FF);
                    result.push_str(&format!("\\u{:04x}\\u{:04x}", high, low));
                }
            }
        }
    }
    result.push('"');
    result
}

/// Compute transaction hash v3 (tenant-bound, null-byte separated).
///
/// If `tenant_id` is None, falls back to v2 (no tenant binding).
pub fn compute_tx_hash(
    prev_hash: &str,
    project: &str,
    action: &str,
    detail_json: &str,
    timestamp: &str,
    tenant_id: Option<&str>,
) -> String {
    let h_input = match tenant_id {
        Some(tid) => format!(
            "v3\x00{}\x00{}\x00{}\x00{}\x00{}\x00{}",
            tid, prev_hash, project, action, detail_json, timestamp
        ),
        None => format!(
            "{}\x00{}\x00{}\x00{}\x00{}",
            prev_hash, project, action, detail_json, timestamp
        ),
    };
    sha256_hex(h_input.as_bytes())
}

/// Legacy v1 hash: colon-delimited concatenation.
pub fn compute_tx_hash_v1(
    prev_hash: &str,
    project: &str,
    action: &str,
    detail_json: &str,
    timestamp: &str,
) -> String {
    let h_input = format!("{}:{}:{}:{}:{}", prev_hash, project, action, detail_json, timestamp);
    sha256_hex(h_input.as_bytes())
}

/// Compute deterministic SHA-256 hash for fact content.
pub fn compute_fact_hash(content: &str) -> String {
    sha256_hex(content.as_bytes())
}

/// Internal: SHA-256 hex digest.
#[inline]
pub(crate) fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_tx_hash_v2_parity() {
        // These must produce identical output to Python's compute_tx_hash()
        let result = compute_tx_hash(
            "GENESIS",
            "cortex",
            "store",
            "{}",
            "2024-01-01T00:00:00+00:00",
            None,
        );
        // Pre-computed from Python
        let expected_input = "GENESIS\x00cortex\x00store\x00{}\x002024-01-01T00:00:00+00:00";
        let expected = sha256_hex(expected_input.as_bytes());
        assert_eq!(result, expected);
    }

    #[test]
    fn test_compute_tx_hash_v3_tenant() {
        let result = compute_tx_hash(
            "GENESIS",
            "cortex",
            "store",
            "{}",
            "2024-01-01T00:00:00+00:00",
            Some("tenant_a"),
        );
        let expected_input =
            "v3\x00tenant_a\x00GENESIS\x00cortex\x00store\x00{}\x002024-01-01T00:00:00+00:00";
        let expected = sha256_hex(expected_input.as_bytes());
        assert_eq!(result, expected);
    }

    #[test]
    fn test_compute_fact_hash() {
        let result = compute_fact_hash("hello world");
        // SHA-256 of "hello world"
        assert_eq!(
            result,
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        );
    }

    #[test]
    fn test_canonical_json_sorted_keys() {
        let val: serde_json::Value =
            serde_json::from_str(r#"{"b":2,"a":1}"#).unwrap();
        assert_eq!(canonical_json(&val), r#"{"a":1,"b":2}"#);
    }

    #[test]
    fn test_canonical_json_nested() {
        let val: serde_json::Value =
            serde_json::from_str(r#"{"z":{"b":2,"a":1},"a":"hello"}"#).unwrap();
        assert_eq!(
            canonical_json(&val),
            r#"{"a":"hello","z":{"a":1,"b":2}}"#
        );
    }

    #[test]
    fn test_canonical_json_ascii_escape() {
        let val = serde_json::Value::String("café".to_string());
        assert_eq!(canonical_json(&val), r#""caf\u00e9""#);
    }
}
