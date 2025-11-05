use regex_automata::dfa::dense::DFA;
use regex_automata::nfa::thompson;
use std::error::Error;

pub fn _create_dfa(pattern: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let nfa = thompson::NFA::compiler().build(pattern)?;
    let dfa = DFA::builder().build_from_nfa(&nfa)?;

    #[cfg(target_endian = "little")]
    let (bytes, pad) = {
        let (b, p) = dfa.to_bytes_little_endian();
        (b, p)
    };
    assert_eq!(pad, 0);
    Ok(bytes.to_vec())
}

pub fn _create_dfa_string(pattern: &str) -> Result<String, Box<dyn Error>> {
    let bytes = _create_dfa(pattern)?;
    let s = bytes.iter()
                 .map(|b| b.to_string())
                 .collect::<Vec<_>>()
                 .join(",");
    Ok(format!("[{}]", s))
}

#[cfg(feature = "python")]
mod py {
    use super::*;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    fn create_dfa_bytes(pattern: &str) -> PyResult<pyo3::Py<pyo3::types::PyBytes>> {
        Python::with_gil(|py| {
            // println!("{:?}", pattern);
            let bytes = _create_dfa(pattern);
            // println!("{:?}", bytes);
            bytes
                .map(|buf| pyo3::types::PyBytes::new_bound(py, &buf).into())
                .map_err(|e| PyValueError::new_err(format!("failed to build DFA: {e}")))
        })
    }

    #[pyfunction]
    fn create_dfa_str(pattern: &str) -> PyResult<String> {
        _create_dfa_string(pattern)
            .map_err(|e| PyValueError::new_err(format!("invalid UTF-8 or build error: {e}")))
    }


    #[pymodule]
    fn compile_regex(_py: Python, m: &PyModule) -> PyResult<()> {
        m.add_function(pyo3::wrap_pyfunction!(create_dfa_str, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(create_dfa_bytes, m)?)?;
        Ok(())
    }
}
