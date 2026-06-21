pub mod ast;
pub mod merkle;

use pyo3::prelude::*;

#[pymodule]
fn cortex_core_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ast::hash_ast, m)?)?;
    m.add_function(wrap_pyfunction!(merkle::batch_merkle_root, m)?)?;
    Ok(())
}
