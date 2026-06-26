use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyDict;
use std::fs::OpenOptions;
use std::sync::{Arc, Mutex};
use memmap2::{MmapMut, MmapOptions};
use sha2::{Sha256, Digest};
use std::ptr;

fn strip_trailing_nulls(bytes: &[u8]) -> &[u8] {
    let mut len = bytes.len();
    while len > 0 && bytes[len - 1] == 0 {
        len -= 1;
    }
    &bytes[..len]
}

/// A thread-safe spatial-temporal swarm topology engine (memory-mapped) to bypass GIL.
#[pyclass]
pub struct UltramapSubstrate {
    mmap: Arc<Mutex<MmapMut>>,
    capacity: usize,
    node_size: usize,
}

#[pymethods]
impl UltramapSubstrate {
    #[new]
    #[pyo3(signature = (bin_path, capacity=None))]
    pub fn new(bin_path: &str, capacity: Option<usize>) -> PyResult<Self> {
        let capacity = capacity.unwrap_or(10000);
        let node_size = 128; // UESS v2: 128 bytes node size
        let tensor_size = capacity * node_size;

        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(bin_path)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to open ultramap file: {}", e)))?;

        if file.metadata().map_err(|e| PyRuntimeError::new_err(format!("Failed to read metadata: {}", e)))?.len() < tensor_size as u64 {
            file.set_len(tensor_size as u64)
                .map_err(|e| PyRuntimeError::new_err(format!("Failed to allocate ultramap file: {}", e)))?;
        }

        let mmap = unsafe {
            MmapOptions::new()
                .len(tensor_size)
                .map_mut(&file)
                .map_err(|e| PyRuntimeError::new_err(format!("Mmap failed: {}", e)))?
        };

        Ok(UltramapSubstrate {
            mmap: Arc::new(Mutex::new(mmap)),
            capacity,
            node_size,
        })
    }

    #[allow(clippy::too_many_arguments)]
    pub fn update_agent_position(&self, agent_idx: usize, x: f64, y: f64, z: f64, target: &str, entropy: f64) -> PyResult<bool> {
        if agent_idx >= self.capacity {
            return Ok(false);
        }

        let offset = agent_idx * self.node_size;
        let mut target_bytes = [0u8; 64];
        let len = target.len().min(64);
        target_bytes[..len].copy_from_slice(&target.as_bytes()[..len]);

        let x_bytes = x.to_ne_bytes();
        let y_bytes = y.to_ne_bytes();
        let z_bytes = z.to_ne_bytes();
        let entropy_bytes = entropy.to_ne_bytes();

        let mmap_arc = self.mmap.clone();

        {
            let mut mmap = mmap_arc.lock().unwrap();
            let ptr = mmap.as_mut_ptr();
            
            unsafe {
                let base = ptr.add(offset);
                ptr::copy_nonoverlapping(x_bytes.as_ptr(), base, 8);
                ptr::copy_nonoverlapping(y_bytes.as_ptr(), base.add(8), 8);
                ptr::copy_nonoverlapping(z_bytes.as_ptr(), base.add(16), 8);
                ptr::copy_nonoverlapping(target_bytes.as_ptr(), base.add(24), 64);
                ptr::copy_nonoverlapping(entropy_bytes.as_ptr(), base.add(88), 8);
            }
            
            mmap.flush().map_err(|e| PyRuntimeError::new_err(format!("[ultramap] msync failed: {}", e)))?;
        }

        Ok(true)
    }

    pub fn calculate_exergy_distance(&self, agent_idx: usize, target_hash: &str) -> PyResult<f64> {
        if agent_idx >= self.capacity {
            return Err(PyRuntimeError::new_err("Agent Index Out of Bounds"));
        }

        let offset = agent_idx * self.node_size;
        
        let mut x_bytes = [0u8; 8];
        let mut y_bytes = [0u8; 8];
        let mut z_bytes = [0u8; 8];
        let mut entropy_bytes = [0u8; 8];

        {
            let mmap = self.mmap.lock().unwrap();
            let ptr = mmap.as_ptr();
            unsafe {
                let base = ptr.add(offset);
                ptr::copy_nonoverlapping(base, x_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(8), y_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(16), z_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(88), entropy_bytes.as_mut_ptr(), 8);
            }
        }

        let x = f64::from_ne_bytes(x_bytes);
        let y = f64::from_ne_bytes(y_bytes);
        let z = f64::from_ne_bytes(z_bytes);
        let current_entropy = f64::from_ne_bytes(entropy_bytes);

        // Hash to deterministic coordinates
        let mut hasher = Sha256::new();
        hasher.update(target_hash.as_bytes());
        let hash_result = hasher.finalize();

        let mut target_int: u64 = 0;
        for i in 0..8 {
            target_int = (target_int << 8) | hash_result[i] as u64;
        }

        let tx = (target_int % 1000) as f64 / 10.0;
        let ty = ((target_int >> 4) % 1000) as f64 / 10.0;
        let tz = ((target_int >> 8) % 1000) as f64 / 10.0;

        let distance = ((tx - x).powi(2) + (ty - y).powi(2) + (tz - z).powi(2)).sqrt();
        let joules = distance * (1.0 / (current_entropy + 0.001));

        Ok(joules)
    }

    pub fn get_agent_state<'py>(&self, py: Python<'py>, agent_idx: usize) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        if agent_idx >= self.capacity {
            return Ok(dict);
        }

        let offset = agent_idx * self.node_size;
        
        let mut x_bytes = [0u8; 8];
        let mut y_bytes = [0u8; 8];
        let mut z_bytes = [0u8; 8];
        let mut target_raw = [0u8; 64];
        let mut entropy_bytes = [0u8; 8];
        let mut qd_bytes = [0u8; 8];
        let mut er_bytes = [0u8; 8];
        let mut ce_bytes = [0u8; 8];
        let mut cl_bytes = [0u8; 8];

        {
            let mmap = self.mmap.lock().unwrap();
            let ptr = mmap.as_ptr();
            unsafe {
                let base = ptr.add(offset);
                ptr::copy_nonoverlapping(base, x_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(8), y_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(16), z_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(24), target_raw.as_mut_ptr(), 64);
                ptr::copy_nonoverlapping(base.add(88), entropy_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(96), qd_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(104), er_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(112), ce_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(120), cl_bytes.as_mut_ptr(), 8);
            }
        }

        let x = f64::from_ne_bytes(x_bytes);
        let y = f64::from_ne_bytes(y_bytes);
        let z = f64::from_ne_bytes(z_bytes);
        let target_len_bytes = strip_trailing_nulls(&target_raw);
        let target = String::from_utf8_lossy(target_len_bytes).into_owned();
        let entropy = f64::from_ne_bytes(entropy_bytes);
        let queue_depth = f64::from_ne_bytes(qd_bytes);
        let error_rate = f64::from_ne_bytes(er_bytes);
        let causal_entropy = f64::from_ne_bytes(ce_bytes);
        let cpu_load = f64::from_ne_bytes(cl_bytes);

        dict.set_item("x", x)?;
        dict.set_item("y", y)?;
        dict.set_item("z", z)?;
        dict.set_item("target", target)?;
        dict.set_item("entropy", entropy)?;
        dict.set_item("queue_depth", queue_depth)?;
        dict.set_item("error_rate", error_rate)?;
        dict.set_item("causal_entropy", causal_entropy)?;
        dict.set_item("cpu_load", cpu_load)?;

        Ok(dict)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn update_control_vector(&self, agent_idx: usize, queue_depth: f64, error_rate: f64, causal_entropy: f64, cpu_load: f64) -> PyResult<bool> {
        if agent_idx >= self.capacity {
            return Ok(false);
        }

        let offset = agent_idx * self.node_size;
        
        let qd_bytes = queue_depth.to_ne_bytes();
        let er_bytes = error_rate.to_ne_bytes();
        let ce_bytes = causal_entropy.to_ne_bytes();
        let cl_bytes = cpu_load.to_ne_bytes();

        let mmap_arc = self.mmap.clone();

        {
            let mut mmap = mmap_arc.lock().unwrap();
            let ptr = mmap.as_mut_ptr();
            
            let mut x_bytes = [0u8; 8];
            let mut y_bytes = [0u8; 8];
            let mut z_bytes = [0u8; 8];

            unsafe {
                let base = ptr.add(offset);
                ptr::copy_nonoverlapping(base, x_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(8), y_bytes.as_mut_ptr(), 8);
                ptr::copy_nonoverlapping(base.add(16), z_bytes.as_mut_ptr(), 8);
            }

            let x = f64::from_ne_bytes(x_bytes);
            let y = f64::from_ne_bytes(y_bytes);
            let z = f64::from_ne_bytes(z_bytes);

            if x == 0.0 && y == 0.0 && z == 0.0 {
                return Ok(false);
            }

            unsafe {
                let base = ptr.add(offset);
                ptr::copy_nonoverlapping(qd_bytes.as_ptr(), base.add(96), 8);
                ptr::copy_nonoverlapping(er_bytes.as_ptr(), base.add(104), 8);
                ptr::copy_nonoverlapping(ce_bytes.as_ptr(), base.add(112), 8);
                ptr::copy_nonoverlapping(cl_bytes.as_ptr(), base.add(120), 8);
            }

            mmap.flush().map_err(|e| PyRuntimeError::new_err(format!("[ultramap] msync failed: {}", e)))?;
        }

        Ok(true)
    }

    pub fn get_address(&self) -> usize {
        let mmap = self.mmap.lock().unwrap();
        mmap.as_ptr() as usize
    }
}
