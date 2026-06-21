use crossbeam_channel::{unbounded, Sender};
use std::fs::OpenOptions;
use std::io::{BufWriter, Write};
use std::thread;

pub struct RealityWriter {
    sender: Sender<String>,
}

impl RealityWriter {
    pub fn new(ledger_path: &str) -> Self {
        let (sender, receiver) = unbounded::<String>();
        let path = ledger_path.to_string();

        thread::spawn(move || {
            let file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&path)
                .expect("Failed to open ledger file for append");
            let mut writer = BufWriter::new(file);

            for msg in receiver {
                if let Err(e) = writeln!(writer, "{}", msg) {
                    eprintln!("Failed to write to epistemic ledger: {}", e);
                }
                if let Err(e) = writer.flush() {
                    eprintln!("Failed to flush epistemic ledger: {}", e);
                }
            }
        });

        Self { sender }
    }

    pub fn write_claim(&self, claim_json: &str) {
        if let Err(e) = self.sender.send(claim_json.to_string()) {
            eprintln!("Failed to send claim to async writer: {}", e);
        }
    }
}
