use base64::{engine::general_purpose, Engine as _};
use regex::Regex;
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
use std::time::Instant;

use jwt_rsa_verify_methods::RSA_VERIFY_ELF;

#[derive(Debug)]
pub struct JwtProofResult {
    pub receipt: Receipt,
    pub journal: Vec<u8>,
    pub keys: Vec<String>,
    pub extracted_values: Vec<String>,
}

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

pub fn prove_signature_verification(jwt: &str, jwt_fields: &[String]) -> JwtProofResult {
    let mut jwtparts = jwt.split('.');
    let _header = jwtparts.next().ok_or("missing header in jwt");
    let payload_str = String::from_utf8(
        general_purpose::URL_SAFE_NO_PAD
            .decode(jwtparts.next().ok_or("missing body in jwt").unwrap())
            .unwrap(),
    )
    .unwrap();

    let mut positions = Vec::new();

    for key in jwt_fields {
        let key_pos = find_key_value_quotes(&payload_str, key).unwrap();
        positions.extend_from_slice(&[key_pos.0, key_pos.1, key_pos.2, key_pos.3]);
    }

    let jwt_owned = jwt.to_owned();
    let field_names: Vec<String> = jwt_fields.iter().cloned().collect();

    let env = ExecutorEnv::builder()
        .write(&jwt_owned)
        .expect("write jwt to env")
        .write(&field_names)
        .expect("write keys to env")
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
    println!("Proving time: {:?}", elapsed);
    println!("Total cycles: {}", prove_info.stats.total_cycles);
    println!("User cycles: {}", prove_info.stats.user_cycles);

    let (keys, extracted_values): (Vec<String>, Vec<String>) = prove_info
        .receipt
        .journal
        .decode()
        .expect("journal should decode to extracted values");
    let journal = prove_info.receipt.journal.bytes.clone();

    JwtProofResult {
        receipt: prove_info.receipt,
        journal,
        keys,
        extracted_values,
    }
}
