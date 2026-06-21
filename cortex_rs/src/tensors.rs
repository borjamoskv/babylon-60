use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

/// Descomposición LU con pivoteo parcial escrita en Rust puro (Zero-Dependency).
/// [GOAT-MATH-002] & [GOAT-MATH-090]
fn lu_determinant(matrix: &mut Vec<Vec<f64>>) -> Result<f64, String> {
    let n = matrix.len();
    if n == 0 {
        return Ok(1.0);
    }
    for row in matrix.iter() {
        if row.len() != n {
            return Err("Matrix must be square".to_string());
        }
    }

    let mut det = 1.0;
    
    for i in 0..n {
        // Pivot selection
        let mut pivot = i;
        for j in (i + 1)..n {
            if matrix[j][i].abs() > matrix[pivot][i].abs() {
                pivot = j;
            }
        }

        if matrix[pivot][i].abs() < 1e-12 {
            return Ok(0.0); // Singular matrix
        }

        if pivot != i {
            matrix.swap(i, pivot);
            det = -det; // Permutation changes sign
        }

        det *= matrix[i][i];

        // Elimination
        for j in (i + 1)..n {
            let factor = matrix[j][i] / matrix[i][i];
            for k in (i + 1)..n {
                let val = factor * matrix[i][k];
                matrix[j][k] -= val;
            }
        }
    }

    Ok(det)
}

#[pyfunction]
pub fn calculate_jacobian_determinant(mut matrix: Vec<Vec<f64>>) -> PyResult<f64> {
    lu_determinant(&mut matrix)
        .map_err(|e| PyValueError::new_err(format!("Calculation failed: {}", e)))
}

#[pyfunction]
pub fn calculate_log_jacobian_determinant(mut matrix: Vec<Vec<f64>>) -> PyResult<f64> {
    let det = lu_determinant(&mut matrix)
        .map_err(|e| PyValueError::new_err(format!("Calculation failed: {}", e)))?;
        
    if det.abs() < 1e-12 {
        return Err(PyValueError::new_err("Matrix is singular, log-det is undefined"));
    }
    
    Ok(det.abs().ln())
}
