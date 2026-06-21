use std::collections::HashMap;
use uuid::Uuid;

/// CORTEX-SWARM v3: THERMODYNAMIC EPISTEMIC FIELD
/// Physics Engine for Epistemic Phase Transitions.

#[derive(Clone, Debug)]
pub struct TruthKernel {
    pub hash: String,
    pub logic_baseline: f64,
}

#[derive(Clone, Debug)]
pub struct EpistemicNode {
    pub id: Uuid,
    pub truth_value: TruthKernel,
    pub entropy_budget: f64, // ε*
    pub drift_vector: Vec<f64>,
}

impl EpistemicNode {
    pub fn new(budget: f64) -> Self {
        Self {
            id: Uuid::new_v4(),
            truth_value: TruthKernel {
                hash: "genesis".to_string(),
                logic_baseline: 1.0,
            },
            entropy_budget: budget,
            drift_vector: vec![0.0, 0.0, 0.0],
        }
    }

    /// Exploratory mutation regenerates budget, coherence consumes it.
    pub fn metabolize_entropy(&mut self, coherence_cost: f64, exploration_yield: f64) {
        self.entropy_budget -= coherence_cost;
        self.entropy_budget += exploration_yield;
    }
}

/// Conflict Ecology Engine
pub struct ConflictEcology {
    pub nodes: HashMap<Uuid, EpistemicNode>,
    pub global_entropy_pressure: f64,
}

impl ConflictEcology {
    pub fn new(pressure: f64) -> Self {
        Self {
            nodes: HashMap::new(),
            global_entropy_pressure: pressure,
        }
    }

    /// merge(A, B) -> {C1, C2, C3}
    /// Conflicts are not resolved, they are ecologized.
    pub fn ecologize_merge(&self, a: &EpistemicNode, b: &EpistemicNode) -> Vec<EpistemicNode> {
        let mut trajectories = Vec::new();
        
        // Trajectory 1: Dominant A
        let mut c1 = a.clone();
        c1.entropy_budget *= 0.9; // Friction cost
        trajectories.push(c1);

        // Trajectory 2: Dominant B
        let mut c2 = b.clone();
        c2.entropy_budget *= 0.9;
        trajectories.push(c2);

        // Trajectory 3: Chaotic Synthesis
        let mut c3 = EpistemicNode::new((a.entropy_budget + b.entropy_budget) * 0.5);
        c3.truth_value.hash = "chaotic_synthesis".to_string();
        trajectories.push(c3);

        trajectories
    }

    /// Simulates a phase transition where coherence is negotiated.
    pub fn epistemic_phase_transition(&mut self) {
        // In a true simulation, this computes T(x) = ∫ stability(x, t) dt 
        // over bounded entropy window to prune nodes that exhausted their budget.
        let mut deceased = Vec::new();
        for (id, node) in self.nodes.iter_mut() {
            node.metabolize_entropy(0.1, 0.05);
            if node.entropy_budget <= 0.0 {
                deceased.push(*id);
            }
        }

        for id in deceased {
            self.nodes.remove(&id);
        }
    }
}
