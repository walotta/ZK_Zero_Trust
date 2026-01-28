use jwt_rsa_verify_methods::{RSA_VERIFY_ELF, RSA_VERIFY_ID};
use regex::Regex;
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
use std::{fs, path::Path, time::Instant};

fn find_key_value_quotes(json: &str, key: &str) -> Option<(usize, usize, usize, usize)> {
    let pattern = format!(r#""{}"\s*:\s*"((?:\\.|[^"\\])*)""#, regex::escape(key));
    let re = Regex::new(&pattern).unwrap();
    if let Some(caps) = re.captures(json) {
        let mkey = Regex::new(&format!(r#""{}""#, regex::escape(key)))
            .unwrap()
            .find(json)?;
        let key_start = mkey.start();
        let key_end = mkey.end() - 1;
        if let Some(mval) = caps.get(1) {
            let value_start = mval.start() - 1;
            let value_end = mval.end();
            return Some((key_start, key_end, value_start, value_end));
        }
    }
    None
}

fn load_payload_and_keys() -> (String, Vec<String>) {
    let payload_path = Path::new("data/payload.json");
    let payload_str =
        fs::read_to_string(payload_path).expect("payload.json should be present and readable");

    let keys_path = Path::new("data/fields.txt");
    let keys_contents =
        fs::read_to_string(keys_path).expect("fields.txt should be present and readable");
    let keys: Vec<String> = keys_contents
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(|line| line.to_string())
        .collect();

    (payload_str, keys)
}

pub fn prove_signature_verification() -> (Receipt, Vec<String>) {
    let (payload_str, keys) = load_payload_and_keys();
    // Pass as flat arrays for efficiency
    let mut positions = Vec::new();

    for key in keys.iter() {
        let key_pos = find_key_value_quotes(&payload_str, key)
            .unwrap_or_else(|| panic!("could not compute positions for key {key}"));
        positions.extend_from_slice(&[key_pos.0, key_pos.1, key_pos.2, key_pos.3]);
    }

    let env = ExecutorEnv::builder()
        .write(&payload_str)
        .expect("write jwt to env")
        .write(&positions)
        .expect("write positions to env")
        .build()
        .expect("build executor env");

    let prover = default_prover();
    let start = Instant::now();
    let prove_info = prover
        .prove(env, RSA_VERIFY_ELF)
        .expect("prove signature verification");
    let elapsed = start.elapsed();
    println!("Number of segments: {}", prove_info.stats.segments);
    println!("Total cycles: {}", prove_info.stats.total_cycles);
    println!("User cycles: {}", prove_info.stats.user_cycles);
    println!(
        "Proof size: {} bytes",
        prove_info.receipt.inner.composite().unwrap().seal_size()
    );
    println!(
        "Gen time elapsed: {:?}",
        elapsed
    );



    let committed: Vec<String> = prove_info.receipt
        .journal
        .decode()
        .expect("journal should decode to extracted values");

    (prove_info.receipt, committed)
}

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let (receipt, extracted_values) = prove_signature_verification();

    receipt
        .verify(RSA_VERIFY_ID)
        .expect("Proof of RSA signature verification should succeed");

    println!("Verified JWT extracted values: {:?}", extracted_values);
}
