use jwt_rsa_verify_methods::RSA_VERIFY_ID;

use jwt_rsa_verify_methods::RSA_VERIFY_ELF;
// use regex::Regex;
use risc0_zkvm::{default_prover, ExecutorEnv};
// use rsa::{BigUint, RsaPrivateKey};
// use serde::{Deserialize, Serialize};
use std::time::Instant;

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let mut args = std::env::args();
    let program = args.next().unwrap_or_else(|| String::from("regex-eval"));
    let eval_str = args.collect::<Vec<_>>().join(" ");

    if eval_str.is_empty() {
        eprintln!("Usage: {program} <string-to-evaluate>");
        std::process::exit(1);
    }

    println!("[input] {}", eval_str);

    let env = ExecutorEnv::builder()
        .write(&eval_str)
        .expect("write jwt to env")
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
    println!("Gen time elapsed: {:?}", elapsed);

    let receipt = prove_info.receipt;

    let regex_matched: bool = receipt
        .journal
        .decode()
        .expect("journal should decode to regex evaluation result");

    let verify_start = Instant::now();
    receipt
        .verify(RSA_VERIFY_ID)
        .expect("Proof of RSA signature verification should succeed");
    println!("Verify time elapsed: {:?}", verify_start.elapsed());    

    println!("Regex matched: {}", regex_matched);
}
