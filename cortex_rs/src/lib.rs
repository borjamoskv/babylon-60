use memmap2::{MmapMut, MmapOptions};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use sha2::{Digest, Sha256};
use std::fs::OpenOptions;
use std::sync::{Arc, Mutex};

fn strip_trailing_nulls(slice: &[u8]) -> &[u8] {
    if let Some(pos) = slice.iter().rposition(|&x| x != 0) {
        &slice[..=pos]
    } else {
        &[]
    }
}

/// A thread-safe Rust extension handling direct-silicon execution of the VSA Tensor
/// (Memory-Mapped file) and SQLite integration to bypass the Python GIL.
#[pyclass]
pub struct CortexRsSubstrate {
    mmap: Arc<Mutex<MmapMut>>,
    dimension: usize,
}

#[pymethods]
impl CortexRsSubstrate {
    #[new]
    #[pyo3(signature = (bin_path, dimension))]
    pub fn new(bin_path: &str, dimension: usize) -> PyResult<Self> {
        let tensor_size = dimension * 8; // 8 bytes per f64

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(bin_path)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to open VSA BIN: {}", e)))?;

        // Ensure pre-allocation
        if file.metadata().map_err(|e| PyRuntimeError::new_err(format!("Failed to read metadata: {}", e)))?.len() < tensor_size as u64 {
            file.set_len(tensor_size as u64)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to allocate tensor size: {}", e)))?;
        }

        let mmap = unsafe {
            MmapOptions::new()
                .len(tensor_size)
                .map_mut(&file)
                .map_err(|e| PyRuntimeError::new_err(format!("Mmap failed: {}", e)))?
        };

        Ok(CortexRsSubstrate {
            mmap: Arc::new(Mutex::new(mmap)),
            dimension,
        })
    }

    /// Read the VSA tensor values as a Python List
    pub fn read_tensor<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let mmap = self.mmap.lock().unwrap();
        let slice: &[f64] = unsafe {
            std::slice::from_raw_parts(mmap.as_ptr() as *const f64, self.dimension)
        };
        PyList::new(py, slice)
    }

    /// Apply standard VSA decay vector multiplication (Zero-copy Rust implementation)
    pub fn apply_decay(&self, rate: f64) -> PyResult<()> {
        let mut mmap = self.mmap.lock().unwrap();
        let slice: &mut [f64] = unsafe {
            std::slice::from_raw_parts_mut(mmap.as_mut_ptr() as *mut f64, self.dimension)
        };
        for val in slice.iter_mut() {
            if *val > 0.001 {
                *val *= rate;
            } else if *val > 0.0 {
                *val = 0.0;
            }
        }
        Ok(())
    }

    pub fn record(&self, key: &str, value: &str) -> PyResult<()> {
        let ctx_string = format!("{}:{}", key, value);

        // SHA-256 Hash
        let mut hasher = Sha256::new();
        hasher.update(ctx_string.as_bytes());
        let hash_result = hasher.finalize();

        // Python-identical big-integer modulo VSA_DIMENSION
        let mut remainder: u32 = 0;
        for byte in hash_result.iter() {
            remainder = ((remainder << 8) + *byte as u32) % (self.dimension as u32);
        }
        let idx = remainder as usize;

        // Zero-copy direct mmap write
        {
            let mut mmap = self.mmap.lock().unwrap();
            let slice: &mut [f64] = unsafe {
                std::slice::from_raw_parts_mut(mmap.as_mut_ptr() as *mut f64, self.dimension)
            };
            slice[idx] += 1.0;
        }

        Ok(())
    }

    /// Expose the underlying memory address for zero-copy ctypes/memoryview integrations in Python
    pub fn get_address(&self) -> usize {
        let mmap = self.mmap.lock().unwrap();
        mmap.as_ptr() as usize
    }
}

/// A zero-copy task outbox ring buffer to bypass serialization and SQLite read contention
#[pyclass]
pub struct ZeroCopyRingBuffer {
    mmap: Arc<Mutex<MmapMut>>,
    capacity: usize,
    task_size: usize,
}

#[pymethods]
impl ZeroCopyRingBuffer {
    #[new]
    #[pyo3(signature = (bin_path, capacity=None))]
    pub fn new(bin_path: &str, capacity: Option<usize>) -> PyResult<Self> {
        let capacity = capacity.unwrap_or(10000);
        let task_size = 256;
        let total_size = capacity * task_size;

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(bin_path)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to open ring buffer file: {}", e)))?;

        if file.metadata().map_err(|e| PyRuntimeError::new_err(format!("Failed to read metadata: {}", e)))?.len() < total_size as u64 {
            file.set_len(total_size as u64)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to allocate ring buffer file: {}", e)))?;
        }

        let mmap = unsafe {
            MmapOptions::new()
                .len(total_size)
                .map_mut(&file)
                .map_err(|e| PyRuntimeError::new_err(format!("Mmap failed: {}", e)))?
        };

        Ok(ZeroCopyRingBuffer {
            mmap: Arc::new(Mutex::new(mmap)),
            capacity,
            task_size,
        })
    }

    /// Enqueue a task to the ring buffer by writing directly to mapped memory
    pub fn enqueue(&self, agent_id: &[u8], payload: &[u8]) -> PyResult<bool> {
        let mut mmap = self.mmap.lock().unwrap();
        let buffer: &mut [u8] = unsafe {
            std::slice::from_raw_parts_mut(mmap.as_mut_ptr(), self.capacity * self.task_size)
        };

        for i in 0..self.capacity {
            let offset = i * self.task_size;
            if buffer[offset] == 0 { // Free
                buffer[offset] = 1; // Pending

                // Write native float timestamp
                let timestamp = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs_f64())
                    .unwrap_or(0.0);
                let ts_bytes = timestamp.to_ne_bytes();
                buffer[offset + 1..offset + 9].copy_from_slice(&ts_bytes);

                // Write agent ID hash (64 bytes)
                let mut agent_bytes = [0u8; 64];
                let len = agent_id.len().min(64);
                agent_bytes[..len].copy_from_slice(&agent_id[..len]);
                buffer[offset + 9..offset + 73].copy_from_slice(&agent_bytes);

                // Write binary payload (183 bytes)
                let mut payload_bytes = [0u8; 183];
                let len = payload.len().min(183);
                payload_bytes[..len].copy_from_slice(&payload[..len]);
                buffer[offset + 73..offset + 256].copy_from_slice(&payload_bytes);

                return Ok(true);
            }
        }
        Ok(false)
    }

    /// Fetch pending tasks and transition status to 'processing' (2) in memory
    pub fn fetch_pending<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let mut mmap = self.mmap.lock().unwrap();
        let buffer: &mut [u8] = unsafe {
            std::slice::from_raw_parts_mut(mmap.as_mut_ptr(), self.capacity * self.task_size)
        };

        let list = PyList::empty(py);

        for i in 0..self.capacity {
            let offset = i * self.task_size;
            if buffer[offset] == 1 { // Pending
                buffer[offset] = 2; // Processing

                let mut ts_bytes = [0u8; 8];
                ts_bytes.copy_from_slice(&buffer[offset + 1..offset + 9]);
                let ts = f64::from_ne_bytes(ts_bytes);

                let agent_raw = &buffer[offset + 9..offset + 73];
                let agent_id = strip_trailing_nulls(agent_raw);

                let payload_raw = &buffer[offset + 73..offset + 256];
                let payload = strip_trailing_nulls(payload_raw);

                let py_agent = pyo3::types::PyBytes::new(py, agent_id);
                let py_payload = pyo3::types::PyBytes::new(py, payload);
                let tuple = (i, ts, py_agent, py_payload);
                list.append(tuple)?;
                buffer[offset] = 0; // Free it
            }
        }

        Ok(list)
    }

    /// Expose the underlying memory address for zero-copy ctypes/memoryview integrations in Python
    pub fn get_address(&self) -> usize {
        let mmap = self.mmap.lock().unwrap();
        mmap.as_ptr() as usize
    }
}

/// The main Python module initialization
#[pymodule]
fn cortex_rs(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CortexRsSubstrate>()?;
    m.add_class::<ZeroCopyRingBuffer>()?;
    Ok(())
}
