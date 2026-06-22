// [C5-REAL] Exergy-Maximized — Author: Borja Moskv
// CORTEX Desktop — Filesystem Watcher (Trust Membrane Layer 1)
// Uses macOS FSEvents via the `notify` crate to detect ALL disk mutations.

use notify::{
    Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher,
};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::mpsc;
use tracing::{debug, error, info, warn};

/// Raw filesystem event from the OS.
#[derive(Debug, Clone)]
pub struct FsEvent {
    pub path: PathBuf,
    pub kind: FsEventKind,
    pub timestamp_ms: u64,
}

/// Simplified filesystem event kinds relevant to the Trust Membrane.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FsEventKind {
    /// File was created.
    Create,
    /// File content was modified.
    Modify,
    /// File was deleted.
    Remove,
    /// File was renamed (source or destination).
    Rename,
    /// Unknown or other event.
    Other,
}

impl From<EventKind> for FsEventKind {
    fn from(kind: EventKind) -> Self {
        match kind {
            EventKind::Create(_) => FsEventKind::Create,
            EventKind::Modify(_) => FsEventKind::Modify,
            EventKind::Remove(_) => FsEventKind::Remove,
            _ => FsEventKind::Other,
        }
    }
}

/// The filesystem watcher daemon.
/// Listens to FSEvents on macOS and emits raw FsEvent structs.
pub struct TrustMembraneWatcher {
    watched_dirs: Vec<PathBuf>,
    event_tx: mpsc::Sender<FsEvent>,
}

impl TrustMembraneWatcher {
    pub fn new(watched_dirs: Vec<PathBuf>, event_tx: mpsc::Sender<FsEvent>) -> Self {
        Self {
            watched_dirs,
            event_tx,
        }
    }

    /// Start watching. This blocks the current thread.
    /// Call from a dedicated thread, not from async context directly.
    pub fn start_blocking(&self) -> Result<(), Box<dyn std::error::Error>> {
        let tx = self.event_tx.clone();

        let (notify_tx, notify_rx) = std::sync::mpsc::channel::<Result<Event, notify::Error>>();

        let mut watcher = RecommendedWatcher::new(
            move |res| {
                let _ = notify_tx.send(res);
            },
            Config::default(),
        )?;

        for dir in &self.watched_dirs {
            if dir.exists() {
                info!("[MEMBRANE] Watching directory: {}", dir.display());
                watcher.watch(dir, RecursiveMode::Recursive)?;
            } else {
                warn!("[MEMBRANE] Directory does not exist, skipping: {}", dir.display());
            }
        }

        info!(
            "[MEMBRANE] FSEvents watcher active. Monitoring {} directories.",
            self.watched_dirs.len()
        );

        // Event loop — runs until the sender is dropped
        for res in notify_rx {
            match res {
                Ok(event) => {
                    let kind: FsEventKind = event.kind.into();

                    // Skip irrelevant events
                    if kind == FsEventKind::Other {
                        continue;
                    }

                    let timestamp_ms = SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_millis() as u64;

                    for path in event.paths {
                        // Skip hidden files, .git internals, node_modules, __pycache__
                        if should_ignore(&path) {
                            continue;
                        }

                        let fs_event = FsEvent {
                            path,
                            kind,
                            timestamp_ms,
                        };

                        debug!("[MEMBRANE] FsEvent: {:?} → {}", fs_event.kind, fs_event.path.display());

                        // Non-blocking send — drop event if channel is full (backpressure)
                        if tx.try_send(fs_event).is_err() {
                            warn!("[MEMBRANE] Event channel full, dropping event (backpressure)");
                        }
                    }
                }
                Err(e) => {
                    error!("[MEMBRANE] FSEvents error: {:?}", e);
                }
            }
        }

        Ok(())
    }
}

/// Filter out paths that should never trigger trust evaluation.
fn should_ignore(path: &PathBuf) -> bool {
    let path_str = path.to_string_lossy();

    // Git internals
    if path_str.contains("/.git/") {
        return true;
    }

    // Node modules
    if path_str.contains("/node_modules/") {
        return true;
    }

    // Python cache
    if path_str.contains("/__pycache__/") || path_str.contains("/.pytest_cache/") {
        return true;
    }

    // Rust build artifacts
    if path_str.contains("/target/") {
        return true;
    }

    // IDE config
    if path_str.contains("/.vscode/") || path_str.contains("/.idea/") {
        return true;
    }

    // OS metadata
    if path_str.contains(".DS_Store") || path_str.contains(".Spotlight-") {
        return true;
    }

    // Ruff cache
    if path_str.contains("/.ruff_cache/") {
        return true;
    }

    // Virtual environments
    if path_str.contains("/.venv/") || path_str.contains("/venv/") {
        return true;
    }

    // SQLite WAL/SHM (internal DB operations)
    if path_str.ends_with("-wal") || path_str.ends_with("-shm") || path_str.ends_with("-journal") {
        return true;
    }

    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_should_ignore_git() {
        assert!(should_ignore(&PathBuf::from("/project/.git/objects/abc")));
        assert!(!should_ignore(&PathBuf::from("/project/src/main.rs")));
    }

    #[test]
    fn test_should_ignore_node_modules() {
        assert!(should_ignore(&PathBuf::from("/project/node_modules/foo/bar.js")));
    }

    #[test]
    fn test_should_ignore_pycache() {
        assert!(should_ignore(&PathBuf::from("/project/__pycache__/mod.pyc")));
    }

    #[test]
    fn test_should_not_ignore_source() {
        assert!(!should_ignore(&PathBuf::from("/project/cortex/engine/mtk_core.py")));
        assert!(!should_ignore(&PathBuf::from("/project/desktop/src-tauri/src/main.rs")));
    }

    #[test]
    fn test_fseventkind_from_notify() {
        assert_eq!(FsEventKind::from(EventKind::Create(notify::event::CreateKind::File)), FsEventKind::Create);
    }
}
