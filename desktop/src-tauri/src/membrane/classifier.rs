// [C5-REAL] Exergy-Maximized — Author: Borja Moskv
// CORTEX Desktop — Process Tree Classifier (Trust Membrane Layer 2)
// Inspects the macOS process tree to determine if a file mutation
// was caused by a human (SELF) or an AI agent (NON-SELF).

use std::collections::HashSet;
use std::path::Path;
use tracing::{debug, warn};

/// Classification of a filesystem mutation's origin.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MutationClassification {
    /// The mutation was caused by direct human interaction (editor keystroke → save).
    Human,
    /// The mutation was caused by a known AI agent process.
    AiAgent,
    /// The mutation was caused by a build tool, compiler, or automated process.
    BuildTool,
    /// The mutation's origin could not be determined.
    Unknown,
}

impl MutationClassification {
    /// Returns true if this mutation requires Trust Membrane evaluation.
    pub fn requires_evaluation(&self) -> bool {
        matches!(self, Self::AiAgent | Self::Unknown)
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Human => "SELF",
            Self::AiAgent => "NON-SELF",
            Self::BuildTool => "BUILD",
            Self::Unknown => "UNKNOWN",
        }
    }
}

/// Inspects the macOS process tree to classify mutation sources.
pub struct ProcessClassifier {
    /// Process names known to be AI agents.
    ai_signatures: HashSet<String>,
    /// Process names known to be build tools (safe, deterministic).
    build_signatures: HashSet<String>,
}

impl ProcessClassifier {
    pub fn new(ai_signatures: Vec<String>) -> Self {
        let build_sigs: HashSet<String> = [
            "rustc", "cargo", "gcc", "clang", "make", "cmake",
            "tsc", "esbuild", "vite", "webpack", "rollup",
            "ruff", "black", "isort", "prettier",
            "pytest", "jest", "mocha",
            "git", "ssh", "scp",
            "brew", "apt", "dpkg",
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();

        Self {
            ai_signatures: ai_signatures.into_iter().collect(),
            build_signatures: build_sigs,
        }
    }

    /// Classify a file mutation by inspecting the process tree of the writer.
    ///
    /// Strategy:
    /// 1. Use `lsof` to find which PID has the file open for writing.
    /// 2. Walk up the process tree (ppid chain) to find the root ancestor.
    /// 3. Match process names against known AI agent signatures.
    ///
    /// Fallback: If we can't determine the writer, classify as Unknown.
    pub fn classify_mutation(&self, file_path: &Path) -> (MutationClassification, Option<u32>, Option<String>) {
        // Try to find the writing process via lsof
        match self.find_writer_pid(file_path) {
            Some((pid, process_name)) => {
                let classification = self.classify_process(&process_name, pid);
                debug!(
                    "[CLASSIFIER] {} → PID {} ({}) → {:?}",
                    file_path.display(),
                    pid,
                    process_name,
                    classification
                );
                (classification, Some(pid), Some(process_name))
            }
            None => {
                debug!(
                    "[CLASSIFIER] {} → No writer PID found → UNKNOWN",
                    file_path.display()
                );
                (MutationClassification::Unknown, None, None)
            }
        }
    }

    /// Classify a process by name and its ancestor chain.
    fn classify_process(&self, process_name: &str, pid: u32) -> MutationClassification {
        let name_lower = process_name.to_lowercase();

        // Direct AI agent match
        if self.ai_signatures.iter().any(|sig| name_lower.contains(&sig.to_lowercase())) {
            return MutationClassification::AiAgent;
        }

        // Direct build tool match
        if self.build_signatures.iter().any(|sig| name_lower.contains(&sig.to_lowercase())) {
            return MutationClassification::BuildTool;
        }

        // Walk the process tree upward to find AI ancestors
        if let Some(ancestor_class) = self.walk_ancestor_tree(pid) {
            return ancestor_class;
        }

        // For node/python processes, check command line args for AI indicators
        if name_lower == "node" || name_lower == "python3" || name_lower == "python" {
            if let Some(cmdline) = self.get_process_cmdline(pid) {
                let cmd_lower = cmdline.to_lowercase();
                // AI agent command line indicators
                let ai_indicators = [
                    "cursor", "copilot", "claude", "anthropic", "openai",
                    "codeium", "windsurf", "aider", "continue", "tabby",
                    "agent", "assistant", "llm", "inference",
                    "antigravity",  // MOSKV-1 self-detection
                ];
                for indicator in &ai_indicators {
                    if cmd_lower.contains(indicator) {
                        return MutationClassification::AiAgent;
                    }
                }
            }
        }

        MutationClassification::Unknown
    }

    /// Walk up the process tree via ppid to check for AI ancestors.
    fn walk_ancestor_tree(&self, start_pid: u32) -> Option<MutationClassification> {
        let mut current_pid = start_pid;
        let mut depth = 0;
        let max_depth = 10; // Prevent infinite loops

        while depth < max_depth {
            let (ppid, parent_name) = match self.get_parent_process(current_pid) {
                Some(info) => info,
                None => break,
            };

            // Reached init/launchd
            if ppid <= 1 {
                break;
            }

            let parent_lower = parent_name.to_lowercase();

            // Check if parent is an AI agent
            if self.ai_signatures.iter().any(|sig| parent_lower.contains(&sig.to_lowercase())) {
                return Some(MutationClassification::AiAgent);
            }

            current_pid = ppid;
            depth += 1;
        }

        None
    }

    /// Get the parent PID and process name for a given PID.
    /// Uses `ps` command on macOS.
    fn get_parent_process(&self, pid: u32) -> Option<(u32, String)> {
        let output = std::process::Command::new("ps")
            .args(["-o", "ppid=,comm=", "-p", &pid.to_string()])
            .output()
            .ok()?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let trimmed = stdout.trim();
        if trimmed.is_empty() {
            return None;
        }

        let mut parts = trimmed.splitn(2, char::is_whitespace);
        let ppid: u32 = parts.next()?.trim().parse().ok()?;
        let comm = parts.next()?.trim().to_string();

        Some((ppid, comm))
    }

    /// Find which process has a file open for writing.
    /// Uses `lsof` on macOS.
    fn find_writer_pid(&self, file_path: &Path) -> Option<(u32, String)> {
        let path_str = file_path.to_string_lossy();

        // lsof -t returns just PIDs, but we need the process name too
        let output = std::process::Command::new("lsof")
            .args(["-F", "pc", &path_str])
            .output()
            .ok()?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut pid: Option<u32> = None;
        let mut comm: Option<String> = None;

        for line in stdout.lines() {
            if let Some(p) = line.strip_prefix('p') {
                pid = p.parse().ok();
            }
            if let Some(c) = line.strip_prefix('c') {
                comm = Some(c.to_string());
            }
        }

        match (pid, comm) {
            (Some(p), Some(c)) => Some((p, c)),
            (Some(p), None) => {
                // Fallback: get process name from ps
                let name = self.get_process_name(p).unwrap_or_else(|| "unknown".to_string());
                Some((p, name))
            }
            _ => None,
        }
    }

    /// Get process name by PID.
    fn get_process_name(&self, pid: u32) -> Option<String> {
        let output = std::process::Command::new("ps")
            .args(["-o", "comm=", "-p", &pid.to_string()])
            .output()
            .ok()?;

        let name = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if name.is_empty() {
            None
        } else {
            Some(name)
        }
    }

    /// Get the full command line of a process.
    fn get_process_cmdline(&self, pid: u32) -> Option<String> {
        let output = std::process::Command::new("ps")
            .args(["-o", "args=", "-p", &pid.to_string()])
            .output()
            .ok()?;

        let cmdline = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if cmdline.is_empty() {
            None
        } else {
            Some(cmdline)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classification_requires_evaluation() {
        assert!(MutationClassification::AiAgent.requires_evaluation());
        assert!(MutationClassification::Unknown.requires_evaluation());
        assert!(!MutationClassification::Human.requires_evaluation());
        assert!(!MutationClassification::BuildTool.requires_evaluation());
    }

    #[test]
    fn test_classifier_direct_match() {
        let classifier = ProcessClassifier::new(vec!["cursor".into(), "claude".into()]);

        // Direct process name match (no PID walk, just name check)
        assert_eq!(
            classifier.classify_process("cursor", 999),
            MutationClassification::AiAgent,
        );
        assert_eq!(
            classifier.classify_process("rustc", 999),
            MutationClassification::BuildTool,
        );
    }

    #[test]
    fn test_as_str() {
        assert_eq!(MutationClassification::Human.as_str(), "SELF");
        assert_eq!(MutationClassification::AiAgent.as_str(), "NON-SELF");
    }
}
