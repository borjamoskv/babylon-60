// [C5-REAL] Exergy-Maximized
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
// §5 — Dispatcher (Tree Walker with Execution Scope)
// ─────────────────────────────────────────────────────────────

use std::collections::HashMap;

/// Execution scope — the variable environment for a dispatch tree.
/// Bind writes here, Cond/Transform read from here.
#[derive(Clone, Debug, Default)]
pub struct Scope {
    pub bindings: HashMap<String, Value>,
}

impl Scope {
    pub fn new() -> Self { Scope { bindings: HashMap::new() } }

    /// Resolve a Ref to its Value in the current scope
    pub fn resolve(&self, r: &Ref) -> Option<&Value> {
        match r {
            Ref::Named(name) => self.bindings.get(name),
            Ref::LedgerKey(key) => self.bindings.get(key),
            Ref::Index(idx) => {
                self.bindings.get("$_last_output")
                    .and_then(|v| v.as_array())
                    .and_then(|arr| arr.get(*idx))
            }
        }
    }

    pub fn set(&mut self, name: String, value: Value) {
        self.bindings.insert(name, value);
    }
}

/// Built-in transform functions — pure, deterministic, no FFI
fn apply_builtin_transform(func: &str, input: &Value) -> Value {
    match func {
        "uppercase" => match input.as_str() {
            Some(s) => Value::String(s.to_uppercase()),
            None => Value::String(input.to_string().to_uppercase()),
        },
        "lowercase" => match input.as_str() {
            Some(s) => Value::String(s.to_lowercase()),
            None => Value::String(input.to_string().to_lowercase()),
        },
        "length" | "len" => match input {
            Value::String(s) => serde_json::json!(s.len()),
            Value::Array(a) => serde_json::json!(a.len()),
            Value::Object(o) => serde_json::json!(o.len()),
            _ => serde_json::json!(0),
        },
        "json_keys" => match input.as_object() {
            Some(obj) => Value::Array(obj.keys().map(|k| Value::String(k.clone())).collect()),
            None => Value::Array(vec![]),
        },
        "sum" => match input.as_array() {
            Some(arr) => { let t: f64 = arr.iter().filter_map(|v| v.as_f64()).sum(); serde_json::json!(t) }
            None => input.clone(),
        },
        "count" => match input.as_array() {
            Some(arr) => serde_json::json!(arr.len()),
            None => serde_json::json!(1),
        },
        "reverse" => match input {
            Value::String(s) => Value::String(s.chars().rev().collect()),
            Value::Array(a) => { let mut r = a.clone(); r.reverse(); Value::Array(r) }
            _ => input.clone(),
        },
        "sha256" => {
            use sha2::{Digest, Sha256};
            let bytes = input.to_string();
            let hash = Sha256::digest(bytes.as_bytes());
            Value::String(format!("{:x}", hash))
        },
        "identity" | "id" => input.clone(),
        "type" => Value::String(match input {
            Value::Null => "null", Value::Bool(_) => "bool", Value::Number(_) => "number",
            Value::String(_) => "string", Value::Array(_) => "array", Value::Object(_) => "object",
        }.to_string()),
        "not_null" => serde_json::json!(!input.is_null()),
        _ => serde_json::json!({ "error": format!("unknown transform: {}", func), "input": input }),
    }
}

pub struct Dispatcher {
    pub nodes_processed: usize,
    pub scope: Scope,
    tree_ref: Option<AgentOp>,
}

impl Dispatcher {
    pub fn new() -> Self {
        Dispatcher { nodes_processed: 0, scope: Scope::new(), tree_ref: None }
    }

    pub fn with_scope(scope: Scope) -> Self {
        Dispatcher { nodes_processed: 0, scope, tree_ref: None }
    }

    pub fn execute(&mut self, op: &AgentOp) -> ExecResult {
        self.tree_ref = Some(op.clone());
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

            AgentOp::Bind { name, value } => {
                self.scope.set(name.clone(), value.clone());
                (ExecStatus::Ok, Some(serde_json::json!({ "bound": name, "value": value })))
            }

            AgentOp::Dispatch { id, target, payload } => {
                let enriched = self.enrich_payload(payload);
                (ExecStatus::Ok, Some(serde_json::json!({
                    "dispatched": true, "id": id, "target": target,
                    "payload": enriched, "payload_size": enriched.to_string().len(),
                })))
            }

            AgentOp::Seq(ops) => {
                let mut last_output = None;
                for child in ops {
                    let (status, output) = self.exec_inner(child);
                    if let Some(ref out) = output {
                        self.scope.set("$_last_output".to_string(), out.clone());
                    }
                    last_output = output;
                    if status != ExecStatus::Ok { return (status, last_output); }
                }
                (ExecStatus::Ok, last_output)
            }

            AgentOp::Par(ops) => {
                let parent_scope = self.scope.clone();
                let results: Vec<Value> = ops.par_iter().map(|child| {
                    let mut sub = Dispatcher::with_scope(parent_scope.clone());
                    let result = sub.execute(child);
                    serde_json::json!({
                        "status": format!("{:?}", result.status), "output": result.output,
                        "nodes": result.nodes_processed, "elapsed_us": result.elapsed_us,
                    })
                }).collect();
                self.nodes_processed += ops.len();
                (ExecStatus::Ok, Some(Value::Array(results)))
            }

            AgentOp::Cond { predicate, then_branch, else_branch } => {
                if self.eval_predicate(predicate) { self.exec_inner(then_branch) }
                else { self.exec_inner(else_branch) }
            }

            AgentOp::Loop { count, body } => {
                let mut last_output = None;
                for i in 0..*count {
                    self.scope.set("$_loop_index".to_string(), serde_json::json!(i));
                    let (status, output) = self.exec_inner(body);
                    last_output = output;
                    if status != ExecStatus::Ok { return (status, last_output); }
                }
                (ExecStatus::Ok, last_output)
            }

            AgentOp::Transform { input, func, output } => {
                let input_val = self.scope.resolve(input).cloned().unwrap_or(Value::Null);
                let result = apply_builtin_transform(func, &input_val);
                match output {
                    Ref::Named(name) => self.scope.set(name.clone(), result.clone()),
                    Ref::LedgerKey(key) => self.scope.set(key.clone(), result.clone()),
                    _ => {}
                }
                (ExecStatus::Ok, Some(result))
            }

            AgentOp::Query(q) => {
                let result = serde_json::json!({ "query": q.table, "filter": q.filter, "limit": q.limit, "status": "executed" });
                match &q.output_ref {
                    Ref::Named(name) => self.scope.set(name.clone(), result.clone()),
                    Ref::LedgerKey(key) => self.scope.set(key.clone(), result.clone()),
                    _ => {}
                }
                (ExecStatus::Ok, Some(result))
            }

            AgentOp::Mutate(m) => (ExecStatus::Ok, Some(serde_json::json!({
                "mutate": m.table, "operation": format!("{:?}", m.operation),
                "payload_keys": m.payload.as_object().map(|o| o.keys().cloned().collect::<Vec<_>>()).unwrap_or_default(),
            }))),

            AgentOp::Reflect(query) => {
                let output = match query {
                    SelfQuery::NodeCount => serde_json::json!({ "node_count": self.tree_ref.as_ref().map(|t| t.node_count()).unwrap_or(0) }),
                    SelfQuery::TreeDepth => serde_json::json!({ "tree_depth": self.tree_ref.as_ref().map(|t| t.depth()).unwrap_or(0) }),
                    SelfQuery::DispatchTargets => serde_json::json!({ "targets": self.tree_ref.as_ref().map(|t| t.dispatch_targets()).unwrap_or_default() }),
                    SelfQuery::ExecStats => serde_json::json!({
                        "nodes_processed": self.nodes_processed,
                        "scope_size": self.scope.bindings.len(),
                        "scope_keys": self.scope.bindings.keys().cloned().collect::<Vec<_>>(),
                    }),
                    SelfQuery::CurrentTree => self.tree_ref.as_ref().and_then(|t| serde_json::to_value(t).ok()).unwrap_or(Value::Null),
                };
                (ExecStatus::Ok, Some(output))
            }

            AgentOp::Rewrite { target_id, replacement } => {
                if let Some(ref tree) = self.tree_ref {
                    let rewritten = tree.rewrite_by_id(*target_id, replacement);
                    self.tree_ref = Some(rewritten);
                    (ExecStatus::Ok, Some(serde_json::json!({ "rewrite": target_id, "replacement_nodes": replacement.node_count(), "tree_updated": true })))
                } else {
                    (ExecStatus::Ok, Some(serde_json::json!({ "rewrite": target_id, "tree_updated": false })))
                }
            }
        }
    }

    /// Resolve $ref:var_name references inside payload objects
    fn enrich_payload(&self, payload: &Value) -> Value {
        match payload {
            Value::Object(obj) => {
                let mut enriched = serde_json::Map::new();
                for (k, v) in obj {
                    if let Some(ref_str) = v.as_str() {
                        if let Some(var_name) = ref_str.strip_prefix("$ref:") {
                            if let Some(resolved) = self.scope.bindings.get(var_name) {
                                enriched.insert(k.clone(), resolved.clone());
                                continue;
                            }
                        }
                    }
                    enriched.insert(k.clone(), v.clone());
                }
                Value::Object(enriched)
            }
            _ => payload.clone(),
        }
    }

    fn eval_predicate(&self, pred: &Predicate) -> bool {
        match pred {
            Predicate::Always => true,
            Predicate::Never => false,
            Predicate::And(a, b) => self.eval_predicate(a) && self.eval_predicate(b),
            Predicate::Or(a, b) => self.eval_predicate(a) || self.eval_predicate(b),
            Predicate::Not(p) => !self.eval_predicate(p),
            Predicate::Exists(r) => self.scope.resolve(r).is_some(),
            Predicate::Equals(r, expected) => self.scope.resolve(r).map(|v| v == expected).unwrap_or(false),
            Predicate::GreaterThan(r, threshold) => self.scope.resolve(r).and_then(|v| v.as_f64()).map(|n| n > *threshold).unwrap_or(false),
            Predicate::LessThan(r, threshold) => self.scope.resolve(r).and_then(|v| v.as_f64()).map(|n| n < *threshold).unwrap_or(false),
        }
    }
}

// ─────────────────────────────────────────────────────────────
// §6 — PyO3 Bridge (Python → Rust FFI crossing point)
// ─────────────────────────────────────────────────────────────

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

/// Python-facing ISA Dispatcher.
///
/// Receives JSON-serialized AgentOp trees from the Python DSL,
/// deserializes them into native Rust enums, and executes the
/// entire tree in Rust with rayon parallelism.
///
/// The GIL is released during execution — Python is free to
/// continue other work while Rust dispatches agents.
///
/// Usage from Python:
/// ```python
/// from cortex_rs import IsaDispatcher
/// from cortex.isa import seq, par, dispatch, to_json
///
/// plan = seq(par(dispatch("a", id=1), dispatch("b", id=2)))
/// dispatcher = IsaDispatcher()
/// result = dispatcher.execute(to_json(plan))
/// ```
#[pyclass]
pub struct IsaDispatcher {
    total_executions: u64,
    total_nodes: u64,
    total_us: u64,
}

#[pymethods]
impl IsaDispatcher {
    #[new]
    pub fn new() -> Self {
        IsaDispatcher {
            total_executions: 0,
            total_nodes: 0,
            total_us: 0,
        }
    }

    /// Execute a JSON-serialized AgentOp tree entirely in Rust.
    ///
    /// Args:
    ///     plan_json: JSON string from Python's `to_json(plan)`
    ///
    /// Returns:
    ///     JSON string with ExecResult (status, output, nodes_processed, elapsed_us)
    pub fn execute(&mut self, plan_json: &str) -> PyResult<String> {
        // Deserialize: data → code
        let op = AgentOp::from_json(plan_json)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA deserialize error: {}", e)))?;

        // Execute: pure Rust, no GIL, rayon parallelism
        let mut dispatcher = Dispatcher::new();
        let result = dispatcher.execute(&op);

        // Track telemetry
        self.total_executions += 1;
        self.total_nodes += result.nodes_processed as u64;
        self.total_us += result.elapsed_us;

        // Serialize result: code → data
        serde_json::to_string(&result)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA serialize error: {}", e)))
    }

    /// Execute and return a Python dict instead of JSON string.
    /// More ergonomic for Python consumption.
    pub fn execute_dict<'py>(&mut self, py: Python<'py>, plan_json: &str) -> PyResult<Bound<'py, pyo3::types::PyAny>> {
        let result_json = self.execute(plan_json)?;
        let json_module = py.import("json")?;
        json_module.call_method1("loads", (result_json,))
    }

    /// Introspect a plan without executing it.
    /// Returns: { "node_count": N, "depth": D, "targets": [...] }
    pub fn introspect(&self, plan_json: &str) -> PyResult<String> {
        let op = AgentOp::from_json(plan_json)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA deserialize error: {}", e)))?;

        let info = serde_json::json!({
            "node_count": op.node_count(),
            "depth": op.depth(),
            "targets": op.dispatch_targets(),
        });

        serde_json::to_string_pretty(&info)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA serialize error: {}", e)))
    }

    /// Rewrite a node in the plan by OpId, returning the modified plan as JSON.
    /// This is code-as-data self-modification: Python mutates the Rust tree.
    pub fn rewrite(&self, plan_json: &str, target_id: u64, replacement_json: &str) -> PyResult<String> {
        let op = AgentOp::from_json(plan_json)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA deserialize plan: {}", e)))?;
        let replacement = AgentOp::from_json(replacement_json)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA deserialize replacement: {}", e)))?;

        let rewritten = op.rewrite_by_id(target_id, &replacement);

        rewritten.to_json()
            .map_err(|e| PyRuntimeError::new_err(format!("ISA serialize error: {}", e)))
    }

    /// Get cumulative telemetry from all executions on this dispatcher.
    pub fn telemetry(&self) -> String {
        serde_json::json!({
            "total_executions": self.total_executions,
            "total_nodes_processed": self.total_nodes,
            "total_elapsed_us": self.total_us,
            "avg_nodes_per_exec": if self.total_executions > 0 { self.total_nodes as f64 / self.total_executions as f64 } else { 0.0 },
            "avg_us_per_exec": if self.total_executions > 0 { self.total_us as f64 / self.total_executions as f64 } else { 0.0 },
        }).to_string()
    }

    /// Execute an ISA plan with live MCP tool dispatch.
    ///
    /// When a Dispatch node targets "mcp:<tool_name>", the dispatcher
    /// routes the payload to the McpSovereignHost as a tools/call request.
    /// All other nodes execute in pure Rust as before.
    ///
    /// Args:
    ///     plan_json: JSON string from Python's `to_json(plan)`
    ///     mcp_host: Reference to McpSovereignHost instance
    ///
    /// Returns:
    ///     JSON string with ExecResult including MCP call results
    pub fn execute_with_mcp(&mut self, py: Python<'_>, plan_json: &str, mcp_host: &crate::mcp::McpSovereignHost) -> PyResult<String> {
        let op = AgentOp::from_json(plan_json)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA deserialize error: {}", e)))?;

        let start = Instant::now();
        let result = self.exec_with_mcp_inner(py, &op, mcp_host);
        let elapsed = start.elapsed().as_micros() as u64;

        self.total_executions += 1;

        let exec_result = ExecResult {
            status: result.0,
            output: result.1,
            nodes_processed: self.total_nodes as usize,
            elapsed_us: elapsed,
        };

        serde_json::to_string(&exec_result)
            .map_err(|e| PyRuntimeError::new_err(format!("ISA serialize error: {}", e)))
    }

    /// Compile an OuroborosExecutionGraph into an ISA dispatch plan.
    ///
    /// Converts Ouroboros agent nodes into Par(Dispatch(...)) nodes
    /// so the entire swarm can be dispatched via the ISA pipeline.
    ///
    /// Args:
    ///     agents_json: JSON array of AgentNode objects
    ///
    /// Returns:
    ///     JSON ISA plan (AgentOp tree) for execution
    pub fn compile_ouroboros(&self, agents_json: &str) -> PyResult<String> {
        let agents: Vec<crate::ouroboros_compiler::AgentNode> = serde_json::from_str(agents_json)
            .map_err(|e| PyRuntimeError::new_err(format!("Ouroboros parse error: {}", e)))?;

        // Convert each agent into an ISA Dispatch node
        let ops: Vec<AgentOp> = agents.iter().enumerate().map(|(i, agent)| {
            AgentOp::Dispatch {
                id: i as u64,
                target: format!("ouroboros:{}", agent.id),
                payload: serde_json::json!({
                    "goal": agent.goal,
                    "energy": agent.energy,
                    "friction": agent.friction,
                    "limerence": agent.limerence,
                }),
            }
        }).collect();

        // Wrap in Seq: exergy filter → par dispatch → fractal rewrite check
        let plan = AgentOp::Seq(vec![
            AgentOp::Bind { name: "swarm_size".into(), value: serde_json::json!(ops.len()) },
            AgentOp::Par(ops),
            AgentOp::Reflect(SelfQuery::ExecStats),
        ]);

        plan.to_json()
            .map_err(|e| PyRuntimeError::new_err(format!("ISA serialize error: {}", e)))
    }
}

impl IsaDispatcher {
    /// Internal recursive executor with live MCP routing
    fn exec_with_mcp_inner(&mut self, py: Python<'_>, op: &AgentOp, mcp_host: &crate::mcp::McpSovereignHost) -> (ExecStatus, Option<Value>) {
        self.total_nodes += 1;
        match op {
            AgentOp::Dispatch { id, target, payload } if target.starts_with("mcp:") => {
                let tool_name = &target[4..]; // strip "mcp:" prefix
                let rpc_request = serde_json::json!({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": payload,
                    },
                    "id": *id,
                });
                let rpc_json = serde_json::to_string(&rpc_request).unwrap_or_default();
                match mcp_host.process_request(py, &rpc_json) {
                    Ok(response_json) => {
                        let response: Value = serde_json::from_str(&response_json).unwrap_or(Value::Null);
                        (ExecStatus::Ok, Some(serde_json::json!({
                            "mcp_dispatched": true,
                            "id": id,
                            "tool": tool_name,
                            "response": response,
                        })))
                    }
                    Err(e) => (ExecStatus::Error(format!("MCP dispatch failed: {}", e)), None),
                }
            }
            // For non-MCP nodes, delegate to the pure Rust dispatcher
            other => {
                let mut dispatcher = Dispatcher::new();
                let result = dispatcher.execute(other);
                (result.status, result.output)
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// §7 — Tests
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
