use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use rdkafka::config::ClientConfig;
use rdkafka::producer::{BaseProducer, BaseRecord, Producer};
use std::time::Duration;

#[pyclass]
pub struct OuroborosStreamKernel {
    producer: BaseProducer,
    topic: String,
}

#[pymethods]
impl OuroborosStreamKernel {
    #[new]
    #[pyo3(signature = (brokers, topic))]
    pub fn new(brokers: &str, topic: &str) -> PyResult<Self> {
        let producer: BaseProducer = ClientConfig::new()
            .set("bootstrap.servers", brokers)
            .set("message.timeout.ms", "5000")
            .set("queue.buffering.max.ms", "0") // 0 latency
            .create()
            .map_err(|e| PyRuntimeError::new_err(format!("Kafka Producer Error: {}", e)))?;

        Ok(OuroborosStreamKernel {
            producer,
            topic: topic.to_string(),
        })
    }

    pub fn emit_friction(&self, agent_id: &str, signal: f64, entropy: f64, target: &str) -> PyResult<()> {
        let payload = format!(
            r#"{{"type":"FRICTION_SEEN","agent_id":"{}","signal":{},"entropy":{},"target":"{}"}}"#,
            agent_id, signal, entropy, target
        );

        let record = BaseRecord::to(&self.topic)
            .key(agent_id)
            .payload(&payload);

        self.producer
            .send(record)
            .map_err(|(e, _)| PyRuntimeError::new_err(format!("Failed to emit friction: {}", e)))?;
        Ok(())
    }

    pub fn emit_rewrite(&self, agent_id: &str, compression: bool, signal_density: f64) -> PyResult<()> {
        let payload = format!(
            r#"{{"type":"SELF_REWRITE","agent_id":"{}","compression":{},"signal_density":{}}}"#,
            agent_id, compression, signal_density
        );

        let record = BaseRecord::to(&self.topic)
            .key(agent_id)
            .payload(&payload);

        self.producer
            .send(record)
            .map_err(|(e, _)| PyRuntimeError::new_err(format!("Failed to emit rewrite: {}", e)))?;
        Ok(())
    }

    pub fn flush(&self) -> PyResult<()> {
        let _ = self.producer.flush(Duration::from_secs(5));
        Ok(())
    }
}
