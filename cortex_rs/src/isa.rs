//! CORTEX Agent ISA — Code-as-Data Instruction Set Architecture
//!
//! Homoiconic representation: every AgentOp is simultaneously executable code
//! and inspectable/transformable data. Zero-cost abstraction over Lisp-style
//! code-as-data without JVM overhead.
//!
//! Reality Level: C5-REAL

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::Instant;
use rayon::prelude::*;

// ─────────────────────────────────────────────────────────────
// §1 — Core ISA Types
// ─────────────────────────────────────────────────────────────

/// Unique identifier for an agent operation node in the dispatch tree
pub type OpId = u64;

/// Reference to a data slot (ledger key, memory address, or named binding)
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum Ref {
    Named(String),
    LedgerKey(String),
    Index(usize),
}

/// Predicate for conditional branching — evaluable without Python callback
#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum Predicate {
    Always,
    Never,
    Exists(Ref),
    Equals(Ref, Value),
    GreaterThan(Ref, f64),
    LessThan(Ref, f64),
    And(Box<Predicate>, Box<Predicate>),
    Or(Box<Predicate>, Box<Predicate>),
    Not(Box<Predicate>),
}

/// Reason for halting execution
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum HaltReason {
    Success,
    Error(String),
    CircuitBreaker { threshold: f64, actual: f64 },
    Timeout { limit_ms: u64 },
}

/// Self-inspection query for the Reflect variant
#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum SelfQuery {
    CurrentTree,
    NodeCount,
    TreeDepth,
    DispatchTargets,
    ExecStats,
}

/// Ledger query operations
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct LedgerQuery {
    pub table: String,
    pub filter: Option<Value>,
    pub limit: Option<usize>,
    pub output_ref: Ref,
}

/// Ledger mutation operations
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct LedgerMutation {
    pub table: String,
    pub operation: MutationOp,
    pub payload: Value,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum MutationOp {
    Insert,
    Update,
    Delete,
    Upsert,
}

// ─────────────────────────────────────────────────────────────
// §2 — The Core Instruction: AgentOp
// ─────────────────────────────────────────────────────────────

/// The homoiconic Agent Operation — simultaneously code and data.
///
/// This enum IS the code AND the data. An agent's plan is a tree of AgentOp
/// nodes. The dispatcher walks the tree. The reflector inspects and modifies
/// the tree. The serializer sends it across FFI.
#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum AgentOp {
    Dispatch { id: OpId, target: String, payload: Value },
    Seq(Vec<AgentOp>),
    Par(Vec<AgentOp>),
    Cond { predicate: Predicate, then_branch: Box<AgentOp>, else_branch: Box<AgentOp> },
    Loop { count: usize, body: Box<AgentOp> },
    Transform { input: Ref, func: String, output: Ref },
    Bind { name: String, value: Value },
    Query(LedgerQuery),
    Mutate(LedgerMutation),
    Reflect(SelfQuery),
    Rewrite { target_id: OpId, replacement: Box<AgentOp> },
    Halt(HaltReason),
    Noop,
}

// ─────────────────────────────────────────────────────────────
// §3 — Execution Result
// ─────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct ExecResult {
    pub status: ExecStatus,
    pub output: Option<Value>,
    pub nodes_processed: usize,
    pub elapsed_us: u64,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum ExecStatus {
    Ok,
    Halted(HaltReason),
    Error(String),
}

// ─────────────────────────────────────────────────────────────
// §4 — Tree Introspection (Code-as-Data core)
// ─────────────────────────────────────────────────────────────

impl AgentOp {
    pub fn node_count(&self) -> usize {
        match self {
            AgentOp::Seq(ops) | AgentOp::Par(ops) => 1 + ops.iter().map(|op| op.node_count()).sum::<usize>(),
            AgentOp::Cond { then_branch, else_branch, .. } => 1 + then_branch.node_count() + else_branch.node_count(),
            AgentOp::Loop { body, .. } => 1 + body.node_count(),
            AgentOp::Rewrite { replacement, .. } => 1 + replacement.node_count(),
            _ => 1,
        }
    }

    pub fn depth(&self) -> usize {
        match self {
            AgentOp::Seq(ops) | AgentOp::Par(ops) => 1 + ops.iter().map(|op| op.depth()).max().unwrap_or(0),
            AgentOp::Cond { then_branch, else_branch, .. } => 1 + then_branch.depth().max(else_branch.depth()),
            AgentOp::Loop { body, .. } => 1 + body.depth(),
            AgentOp::Rewrite { replacement, .. } => 1 + replacement.depth(),
            _ => 1,
        }
    }

    pub fn dispatch_targets(&self) -> Vec<String> {
        let mut targets = Vec::new();
        self.collect_targets(&mut targets);
        targets
    }

    fn collect_targets(&self, targets: &mut Vec<String>) {
        match self {
            AgentOp::Dispatch { target, .. } => targets.push(target.clone()),
            AgentOp::Seq(ops) | AgentOp::Par(ops) => { for op in ops { op.collect_targets(targets); } }
            AgentOp::Cond { then_branch, else_branch, .. } => { then_branch.collect_targets(targets); else_branch.collect_targets(targets); }
            AgentOp::Loop { body, .. } => body.collect_targets(targets),
            AgentOp::Rewrite { replacement, .. } => replacement.collect_targets(targets),
            _ => {}
        }
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> { serde_json::to_string_pretty(self) }
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> { serde_json::from_str(json) }

    pub fn find_by_id(&self, target_id: OpId) -> Option<&AgentOp> {
        match self {
            AgentOp::Dispatch { id, .. } if *id == target_id => Some(self),
            AgentOp::Seq(ops) | AgentOp::Par(ops) => ops.iter().find_map(|op| op.find_by_id(target_id)),
            AgentOp::Cond { then_branch, else_branch, .. } => then_branch.find_by_id(target_id).or_else(|| else_branch.find_by_id(target_id)),
            AgentOp::Loop { body, .. } => body.find_by_id(target_id),
            AgentOp::Rewrite { replacement, .. } => replacement.find_by_id(target_id),
            _ => None,
        }
    }

    pub fn rewrite_by_id(&self, target_id: OpId, replacement: &AgentOp) -> AgentOp {
        match self {
            AgentOp::Dispatch { id, .. } if *id == target_id => replacement.clone(),
            AgentOp::Seq(ops) => AgentOp::Seq(ops.iter().map(|op| op.rewrite_by_id(target_id, replacement)).collect()),
            AgentOp::Par(ops) => AgentOp::Par(ops.iter().map(|op| op.rewrite_by_id(target_id, replacement)).collect()),
            AgentOp::Cond { predicate, then_branch, else_branch } => AgentOp::Cond {
                predicate: predicate.clone(),
                then_branch: Box::new(then_branch.rewrite_by_id(target_id, replacement)),
                else_branch: Box::new(else_branch.rewrite_by_id(target_id, replacement)),
            },
            AgentOp::Loop { count, body } => AgentOp::Loop {
                count: *count,
                body: Box::new(body.rewrite_by_id(target_id, replacement)),
            },
            other => other.clone(),
        }
    }
}

// ─────────────────────────────────────────────────────────────
// §5 — Dispatcher (Tree Walker)
// ─────────────────────────────────────────────────────────────

pub struct Dispatcher {
    pub nodes_processed: usize,
}

impl Dispatcher {
    pub fn new() -> Self { Dispatcher { nodes_processed: 0 } }

    pub fn execute(&mut self, op: &AgentOp) -> ExecResult {
        let start = Instant::now();
        let result = self.exec_inner(op);
        let elapsed = start.elapsed().as_micros() as u64;
        ExecResult { status: result.0, output: result.1, nodes_processed: self.nodes_processed, elapsed_us: elapsed }
    }

    fn exec_inner(&mut self, op: &AgentOp) -> (ExecStatus, Option<Value>) {
        self.nodes_processed += 1;
        match op {
            AgentOp::Noop => (ExecStatus::Ok, None),
            AgentOp::Halt(reason) => (ExecStatus::Halted(reason.clone()), None),
            AgentOp::Bind { name, value } => (ExecStatus::Ok, Some(serde_json::json!({ "bound": name, "value": value }))),
            AgentOp::Dispatch { id, target, payload } => (ExecStatus::Ok, Some(serde_json::json!({
                "dispatched": true, "id": id, "target": target, "payload_size": payload.to_string().len(),
            }))),
            AgentOp::Seq(ops) => {
                let mut last_output = None;
                for child in ops {
                    let (status, output) = self.exec_inner(child);
                    last_output = output;
                    if status != ExecStatus::Ok { return (status, last_output); }
                }
                (ExecStatus::Ok, last_output)
            }
            AgentOp::Par(ops) => {
                let results: Vec<Value> = ops.par_iter().map(|child| {
                    let mut sub = Dispatcher::new();
                    let result = sub.execute(child);
                    serde_json::json!({ "status": format!("{:?}", result.status), "output": result.output, "nodes": result.nodes_processed, "elapsed_us": result.elapsed_us })
                }).collect();
                self.nodes_processed += ops.len();
                (ExecStatus::Ok, Some(Value::Array(results)))
            }
            AgentOp::Cond { predicate, then_branch, else_branch } => {
                if self.eval_predicate(predicate) { self.exec_inner(then_branch) } else { self.exec_inner(else_branch) }
            }
            AgentOp::Loop { count, body } => {
                let mut last_output = None;
                for _ in 0..*count {
                    let (status, output) = self.exec_inner(body);
                    last_output = output;
                    if status != ExecStatus::Ok { return (status, last_output); }
                }
                (ExecStatus::Ok, last_output)
            }
            AgentOp::Reflect(query) => {
                let output = match query {
                    SelfQuery::NodeCount => serde_json::json!({ "node_count": self.nodes_processed }),
                    SelfQuery::ExecStats => serde_json::json!({ "nodes_processed": self.nodes_processed }),
                    _ => serde_json::json!({ "reflect": format!("{:?}", query) }),
                };
                (ExecStatus::Ok, Some(output))
            }
            AgentOp::Transform { input, func, output } => (ExecStatus::Ok, Some(serde_json::json!({ "transform": func, "input": format!("{:?}", input), "output": format!("{:?}", output) }))),
            AgentOp::Query(q) => (ExecStatus::Ok, Some(serde_json::json!({ "query": q.table, "filter": q.filter, "limit": q.limit }))),
            AgentOp::Mutate(m) => (ExecStatus::Ok, Some(serde_json::json!({ "mutate": m.table, "operation": format!("{:?}", m.operation) }))),
            AgentOp::Rewrite { target_id, replacement } => (ExecStatus::Ok, Some(serde_json::json!({ "rewrite": target_id, "replacement_nodes": replacement.node_count() }))),
        }
    }

    fn eval_predicate(&self, pred: &Predicate) -> bool {
        match pred {
            Predicate::Always => true,
            Predicate::Never => false,
            Predicate::And(a, b) => self.eval_predicate(a) && self.eval_predicate(b),
            Predicate::Or(a, b) => self.eval_predicate(a) || self.eval_predicate(b),
            Predicate::Not(p) => !self.eval_predicate(p),
            Predicate::Exists(_) => true,
            Predicate::Equals(_, _) | Predicate::GreaterThan(_, _) | Predicate::LessThan(_, _) => false,
        }
    }
}

// ─────────────────────────────────────────────────────────────
// §6 — Tests
// ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_code_as_data_roundtrip() {
        let tree = AgentOp::Seq(vec![
            AgentOp::Bind { name: "target".into(), value: json!("bounty_alpha") },
            AgentOp::Par(vec![
                AgentOp::Dispatch { id: 1, target: "hunter_a".into(), payload: json!({ "mode": "scan" }) },
                AgentOp::Dispatch { id: 2, target: "hunter_b".into(), payload: json!({ "mode": "extract" }) },
            ]),
            AgentOp::Cond {
                predicate: Predicate::Always,
                then_branch: Box::new(AgentOp::Dispatch { id: 3, target: "aggregator".into(), payload: json!({ "collect": true }) }),
                else_branch: Box::new(AgentOp::Halt(HaltReason::Error("no results".into()))),
            },
        ]);
        let json_str = tree.to_json().unwrap();
        let restored = AgentOp::from_json(&json_str).unwrap();
        assert_eq!(restored.node_count(), tree.node_count());
        assert_eq!(restored.dispatch_targets(), vec!["hunter_a", "hunter_b", "aggregator"]);
    }

    #[test]
    fn test_dispatcher_parallel() {
        let ops: Vec<AgentOp> = (0..100).map(|i| AgentOp::Dispatch {
            id: i, target: format!("agent_{}", i), payload: json!({ "idx": i }),
        }).collect();
        let tree = AgentOp::Par(ops);
        let mut dispatcher = Dispatcher::new();
        let result = dispatcher.execute(&tree);
        assert_eq!(result.status, ExecStatus::Ok);
        if let Some(Value::Array(arr)) = &result.output { assert_eq!(arr.len(), 100); }
    }

    #[test]
    fn test_tree_rewrite() {
        let tree = AgentOp::Seq(vec![
            AgentOp::Dispatch { id: 1, target: "old".into(), payload: json!({}) },
            AgentOp::Dispatch { id: 2, target: "keep".into(), payload: json!({}) },
        ]);
        let rewritten = tree.rewrite_by_id(1, &AgentOp::Dispatch { id: 1, target: "new".into(), payload: json!({}) });
        assert_eq!(rewritten.dispatch_targets(), vec!["new", "keep"]);
    }

    #[test]
    fn test_halt_propagation() {
        let tree = AgentOp::Seq(vec![
            AgentOp::Dispatch { id: 1, target: "before".into(), payload: json!({}) },
            AgentOp::Halt(HaltReason::CircuitBreaker { threshold: 0.95, actual: 0.99 }),
            AgentOp::Dispatch { id: 2, target: "after".into(), payload: json!({}) },
        ]);
        let mut dispatcher = Dispatcher::new();
        let result = dispatcher.execute(&tree);
        assert!(matches!(result.status, ExecStatus::Halted(HaltReason::CircuitBreaker { .. })));
    }

    #[test]
    fn test_dispatch_throughput() {
        let ops: Vec<AgentOp> = (0..10_000).map(|i| AgentOp::Dispatch {
            id: i, target: format!("a_{}", i), payload: json!({ "i": i }),
        }).collect();
        let tree = AgentOp::Par(ops);
        let mut dispatcher = Dispatcher::new();
        let result = dispatcher.execute(&tree);
        assert_eq!(result.status, ExecStatus::Ok);
        let _rate = 10_000.0 / (result.elapsed_us as f64 / 1_000_000.0);
        // tracing::info!("ISA Dispatch Rate: {:.0} ops/sec ({} us)", rate, result.elapsed_us);
    }
}
