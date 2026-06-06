// [C5-REAL] Exergy-Maximized
use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::message::Message;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{info, warn, error};

// --- EVENTS ---
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrictionPayload {
    pub signal: f64,
    pub entropy: f64,
    pub target: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RewritePayload {
    pub compression: bool,
    pub signal_density: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum EventType {
    #[serde(rename = "FRICTION_SEEN")]
    FrictionSeen(FrictionPayload),
    #[serde(rename = "SELF_REWRITE")]
    SelfRewrite(RewritePayload),
    #[serde(rename = "PRUNE")]
    Prune,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub event_id: String,
    pub agent_id: String,
    #[serde(flatten)]
    pub event_type: EventType,
    pub timestamp: u64,
}

// --- STATE RECONSTRUCTOR ---
#[derive(Debug, Clone)]
pub struct AgentState {
    pub id: String,
    pub signal_density: f64, // U = Utilidad
    pub entropy_pressure: f64, // C = Coste
    pub is_alive: bool,
}

impl AgentState {
    pub fn new(id: String) -> Self {
        Self {
            id,
            signal_density: 0.0,
            entropy_pressure: 0.0,
            is_alive: true,
        }
    }

    pub fn fold(&mut self, event: &Event) {
        if !self.is_alive {
            return;
        }
        match &event.event_type {
            EventType::FrictionSeen(payload) => {
                self.signal_density += payload.signal;
                self.entropy_pressure += payload.entropy;
            }
            EventType::SelfRewrite(payload) => {
                if payload.compression {
                    self.entropy_pressure *= 0.5; // Compresión reduce el coste de mantenimiento
                }
                self.signal_density = payload.signal_density;
            }
            EventType::Prune => {
                self.is_alive = false;
            }
        }
    }
}

// --- KERNEL MEMORY ---
pub struct StreamKernel {
    pub state_store: HashMap<String, AgentState>,
}

impl StreamKernel {
    pub fn new() -> Self {
        Self {
            state_store: HashMap::new(),
        }
    }

    pub fn process_event(&mut self, event: Event) {
        let state = self
            .state_store
            .entry(event.agent_id.clone())
            .or_insert_with(|| AgentState::new(event.agent_id.clone()));

        state.fold(&event);

        info!(
            "Agent {} state updated | Signal (U): {:.2} | Entropy (C): {:.2} | Alive: {}",
            state.id, state.signal_density, state.entropy_pressure, state.is_alive
        );

        // Ouroboros Pruning Logic (Dynamic Utility > Cost)
        // Si C > U (con margen), el agente es limerente y requiere compresión estática.
        if state.is_alive && state.entropy_pressure > state.signal_density * 2.0 + 10.0 {
            warn!("⚠️ Agent {} es limerente (C > U). Generando señal de PRUNE/REWRITE.", state.id);
            // In a full active DAG engine, we emit an event to system.pruning here.
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    info!("⚡ Starting OUROBOROS STREAM KERNEL (Redpanda Backend)...");

    let brokers = std::env::var("KAFKA_BROKERS").unwrap_or_else(|_| "localhost:9092".to_string());

    let consumer: StreamConsumer = ClientConfig::new()
        .set("group.id", "ouroboros_kernel_group")
        .set("bootstrap.servers", &brokers)
        .set("enable.partition.eof", "false")
        .set("session.timeout.ms", "6000")
        .set("enable.auto.commit", "true")
        // No auto-offset reset defined explicitly, defaults to latest.
        // For event sourcing we would typically replay from earliest.
        .set("auto.offset.reset", "earliest")
        .create()?;

    let topics = ["system.friction", "system.pruning", "system.rewrites"];
    consumer.subscribe(&topics)?;

    info!("Subscribed to topics: {:?}", topics);
    info!("Waiting for events...");

    let mut kernel = StreamKernel::new();

    loop {
        match consumer.recv().await {
            Err(e) => warn!("Kafka error: {}", e),
            Ok(m) => {
                let payload = match m.payload_view::<str>() {
                    None => "",
                    Some(Ok(s)) => s,
                    Some(Err(e)) => {
                        warn!("Error while deserializing message payload: {:?}", e);
                        ""
                    }
                };

                if !payload.is_empty() {
                    match serde_json::from_str::<Event>(payload) {
                        Ok(event) => kernel.process_event(event),
                        Err(e) => error!("Failed to parse event: {} | Payload: {}", e, payload),
                    }
                }
            }
        }
    }
}
