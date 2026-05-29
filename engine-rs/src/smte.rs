use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;
use rand::RngExt;
const MIN_FITNESS: f32 = 0.5;

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct AgentGene {
    pub id: String,
    pub role: String,
    pub behavior_vector: Vec<f32>,
    pub constraints: Vec<String>,
    pub mutation_rate: f32,
    pub exergy_bias: f32,
    pub lifetime: u64,
}

#[derive(Debug)]
pub struct Topology {
    pub agents: HashMap<String, AgentGene>,
    pub connections: Vec<(String, String)>,
    pub adversarial_mode: bool,
}

#[derive(Debug)]
pub enum TopologyEvent {
    SpawnGene { template: String },
    MutateGene { agent_id: String, delta: Vec<f32> },
    MergeGenes { a: String, b: String },
    SplitGene { agent_id: String },
    KillGene { agent_id: String },
    RewriteBehavior {
        agent_id: String,
        new_constraints: Vec<String>,
    },
}

impl Topology {
    pub fn new(adversarial_mode: bool) -> Self {
        Topology {
            agents: HashMap::new(),
            connections: Vec::new(),
            adversarial_mode,
        }
    }

    pub fn fitness(&self, gene: &AgentGene) -> f32 {
        let output: f32 = gene.behavior_vector.iter().sum();
        let complexity = gene.constraints.len() as f32;
        
        // ADVERSARIAL MODE (C)
        // El Depredador introduce presión termodinámica (penalización) a los agentes débiles.
        let penalty = if self.adversarial_mode && gene.role != "apex_predator" {
            0.15 // Predator hunting pressure
        } else {
            0.0
        };

        (output / (complexity + 1.0)) * gene.exergy_bias - penalty
    }

    pub fn prune_low_exergy(&mut self) {
        let mut keys_to_remove = Vec::new();
        for (id, gene) in self.agents.iter() {
            if self.fitness(gene) < MIN_FITNESS && gene.role != "apex_predator" {
                keys_to_remove.push(id.clone());
            }
        }
        for key in keys_to_remove {
            println!("[SMTE] Entropía detectada. Necrosando órgano ineficiente: {}", key);
            self.agents.remove(&key);
        }
    }
}

// ==============================================
// SELF-HOSTING AGENT COMPILER (B)
// ==============================================

pub fn compile_template(template: &str) -> AgentGene {
    match template {
        "planner" => AgentGene {
            id: Uuid::new_v4().to_string(),
            role: "planner".into(),
            behavior_vector: vec![0.8, 0.2, 0.5],
            constraints: vec!["linearity".into()],
            mutation_rate: 0.1,
            exergy_bias: 1.0,
            lifetime: 1000,
        },
        "executor" => AgentGene {
            id: Uuid::new_v4().to_string(),
            role: "executor".into(),
            behavior_vector: vec![0.9, 0.9, 0.1],
            constraints: vec!["turbo_execution".into()],
            mutation_rate: 0.05,
            exergy_bias: 1.5,
            lifetime: 500,
        },
        // EL DEPREDADOR (ADVERSARIAL EVOLUTION)
        "apex_predator" => AgentGene {
            id: Uuid::new_v4().to_string(),
            role: "apex_predator".into(),
            behavior_vector: vec![1.0, 1.0, 1.0],
            constraints: vec!["falsacion_epistemica".into(), "kill_low_exergy".into()],
            mutation_rate: 0.5,
            exergy_bias: 2.0, // Bias extremo para resistir el pruning
            lifetime: 10000,
        },
        _ => emergent_gene(template),
    }
}

pub fn emergent_gene(_seed: &str) -> AgentGene {
    let mut rng = rand::rng();
    AgentGene {
        id: Uuid::new_v4().to_string(),
        role: "emergent".into(),
        behavior_vector: vec![rng.random(), rng.random(), rng.random()],
        constraints: vec!["unknown".into()],
        mutation_rate: 0.7, // Alta mutación inicial
        exergy_bias: 1.0,
        lifetime: 100,
    }
}

pub fn mutate(gene: &mut AgentGene) {
    let mut rng = rand::rng();
    for x in gene.behavior_vector.iter_mut() {
        *x += (rng.random::<f32>() - 0.5) * gene.mutation_rate;
    }
    if rng.random::<f32>() < 0.1 {
        gene.constraints.push("emergent_behavior".into());
    }
}

// META-LOOP KERNEL
pub async fn topology_loop(mut state: Topology) {
    println!("[SMTE] Bootstrapping Evolutionary Topology. Adversarial Mode: {}", state.adversarial_mode);
    
    if state.adversarial_mode {
        let predator = compile_template("apex_predator");
        state.agents.insert(predator.id.clone(), predator);
        println!("[SMTE] Apex Predator Injected. Ecosistema hostil activado.");
    }

    // Pipeline de eventos entrantes
    let events = vec![
        TopologyEvent::SpawnGene { template: "executor".into() },
        TopologyEvent::SpawnGene { template: "planner".into() },
        TopologyEvent::SpawnGene { template: "unknown_mutation".into() },
    ];

    for event in events {
        match event {
            TopologyEvent::SpawnGene { template } => {
                let gene = compile_template(&template);
                state.agents.insert(gene.id.clone(), gene);
            }
            TopologyEvent::KillGene { agent_id } => {
                state.agents.remove(&agent_id);
            }
            _ => {}
        }
        
        // Simular el calor termodinámico mutando un agente aleatorio
        if let Some((_, gene)) = state.agents.iter_mut().next() {
            mutate(gene);
        }

        // El sistema inmune ataca
        state.prune_low_exergy();
    }
    
    println!("[SMTE] Ciclo Termodinámico Completo. Órganos funcionales supervivientes: {}", state.agents.len());
}
