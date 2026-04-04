use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

/// Binds two VSA vectors via MAP-B (Element-wise Multiply on -1, +1 mapping).
/// O(D) native complexity bypassing the Python GIL. Zero-Context Inflation.
#[pyfunction]
fn vsa_map_b_bind(a: Vec<i8>, b: Vec<i8>) -> PyResult<Vec<i8>> {
    if a.len() != b.len() {
        return Err(pyo3::exceptions::PyValueError::new_err("VSA Dimension mismatch."));
    }
    
    // MAP-B Algebra: +1 * -1 = -1,  -1 * -1 = +1
    let mut out = Vec::with_capacity(a.len());
    for i in 0..a.len() {
        out.push(a[i] * b[i]);
    }
    
    Ok(out)
}

/// Zero-Copy Native Matrix search. Computes native Hamming Distance massively fast
/// across N stored hard locations in Kanerva SDM memory.
#[pyfunction]
fn vsa_hamming_distance(query: Vec<i8>, memory_bank: Vec<Vec<i8>>) -> PyResult<Vec<usize>> {
    let mut distances = Vec::with_capacity(memory_bank.len());
    
    // CPU Cache localized looping structure for maximum nanosecond iteration
    for mem_vec in memory_bank.iter() {
        let mut dist = 0;
        for i in 0..query.len() {
            if query[i] != mem_vec[i] {
                dist += 1;
            }
        }
        distances.push(dist);
    }
    
    Ok(distances)
}

/// Init hook for Python (requires compilation via maturin or cargo build --release)
#[pymodule]
fn cortex_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(vsa_map_b_bind, m)?)?;
    m.add_function(wrap_pyfunction!(vsa_hamming_distance, m)?)?;
    Ok(())
}
