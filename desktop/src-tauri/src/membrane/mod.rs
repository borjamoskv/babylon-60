// [C5-REAL] Exergy-Maximized — Author: Borja Moskv
// CORTEX Desktop — Trust Membrane Core
// The physical immune system between AI agents and your filesystem.

mod watcher;
mod classifier;
mod taint;
mod ipc;
mod tray;

use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::mpsc;

pub use classifier::{MutationClassification, ProcessClassifier};
pub use taint::TaintTagger;
pub use watcher::{FsEvent, FsEventKind, TrustMembraneWatcher};

/// A filesystem mutation event enriched with trust classification.
#[derive(Debug, Clone)]
pub struct TrustEvent {
    /// The file path that was mutated.
    pub path: PathBuf,
    /// What kind of filesystem event occurred.
    pub kind: FsEventKind,
    /// Classification: was this a human (SELF) or AI agent (NON-SELF)?
    pub classification: MutationClassification,
    /// The PID of the process that performed the write.
    pub source_pid: Option<u32>,
    /// The process name that performed the write.
    pub source_process: Option<String>,
    /// Timestamp (milliseconds since epoch).
    pub timestamp_ms: u64,
    /// SHA-256 hash of the file content after mutation (if applicable).
    pub content_hash: Option<String>,
}

/// Configuration for the Trust Membrane daemon.
#[derive(Debug, Clone)]
pub struct MembraneConfig {
    /// Directories to monitor for filesystem mutations.
    pub watched_dirs: Vec<PathBuf>,
    /// Process names known to be AI agents (NON-SELF).
    pub ai_process_signatures: Vec<String>,
    /// Whether to actively block suspicious mutations (Phase 2).
    pub enforcement_mode: bool,
    /// Unix domain socket path for IPC with CORTEX Python engine.
    pub ipc_socket_path: PathBuf,
    /// Whether to tag files with xattr taint markers.
    pub enable_xattr_taint: bool,
}

impl Default for MembraneConfig {
    fn default() -> Self {
        Self {
            watched_dirs: vec![
                PathBuf::from(std::env::var("HOME").unwrap_or_default())
                    .join("10_PROJECTS"),
            ],
            ai_process_signatures: vec![
                // Cursor / VS Code AI subprocess identifiers
                "cursor".into(),
                "code-insiders".into(),
                "code".into(),
                // Claude Code / Anthropic
                "claude".into(),
                "claude-code".into(),
                "antigravity".into(),
                // GitHub Copilot
                "copilot".into(),
                "copilot-agent".into(),
                // Devin / Cognition
                "devin".into(),
                // Windsurf / Codeium
                "windsurf".into(),
                "codeium".into(),
                // Generic AI agent process names
                "aider".into(),
                "continue".into(),
                "tabby".into(),
                // Python AI processes
                "python3".into(), // Flagged for deeper inspection
                "node".into(),    // Flagged for deeper inspection
            ],
            enforcement_mode: false, // Phase 1: observe only
            ipc_socket_path: PathBuf::from("/tmp/cortex_membrane.sock"),
            enable_xattr_taint: true,
        }
    }
}

/// The Trust Membrane daemon. Orchestrates watching, classification, and taint tracking.
pub struct TrustMembrane {
    config: Arc<MembraneConfig>,
    event_tx: mpsc::Sender<TrustEvent>,
    event_rx: Option<mpsc::Receiver<TrustEvent>>,
}

impl TrustMembrane {
    pub fn new(config: MembraneConfig) -> Self {
        let (tx, rx) = mpsc::channel(4096);
        Self {
            config: Arc::new(config),
            event_tx: tx,
            event_rx: Some(rx),
        }
    }

    /// Take ownership of the event receiver (for the consumer/UI side).
    pub fn take_event_rx(&mut self) -> Option<mpsc::Receiver<TrustEvent>> {
        self.event_rx.take()
    }

    /// Get a clone of the event sender (for the watcher side).
    pub fn event_sender(&self) -> mpsc::Sender<TrustEvent> {
        self.event_tx.clone()
    }

    /// Get the membrane configuration.
    pub fn config(&self) -> &MembraneConfig {
        &self.config
    }
}
