use jwt_rsa_verify_methods::RSA_VERIFY_ID;

use jwt_rsa_verify_methods::RSA_VERIFY_ELF;
// use regex::Regex;
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
// use rsa::{BigUint, RsaPrivateKey};
// use serde::{Deserialize, Serialize};
use std::time::Instant;

pub fn prove_signature_verification() -> (Receipt, String) {
    let jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjBjMTk0NzIyNjk5MzQ0ZGE5YjdhMDQ3NGE1MmViMzQyIn0.eyJpc3MiOiJodHRwczovL2xvZ2luLmV4YW1wbGUuY29tLyIsInN1YmplY3RfaWQiOiJKdWxpdXMgSGliYmVydCIsImF1ZCI6ImFwaTovL3BheW1lbnRzLXNlcnZpY2UiLCJleHAiOjE3NjA0ODU3ODIsImlhdCI6MTc2MDQ4MjE4MiwiYXV0aF90aW1lIjoxNzYwNDgyMDgyLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibm9uY2UiOiIzZTRmMGY2Ny1iYzVhLTQxM2QtYjUyOC05M2ZkMWM3MWZkNGUiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwicm9sZXMiOiJhZG1pbiJ9.qXhyC0cvLzfxjhEjjYkzel0nFT3eVGt7Q8UauFpv5Tt7YvijTDsfpE6OZP8MXL0qwAFeKGMFAxqnYp8axUXj2lr3Fk8AUiSHv5a8-xLLhBmmhzsGi-Xl1RHdiysq3nSkywxDVRRP5WPL_mbzkrhR5PJj8g9FLOhLXesNMYg83Sog0xle13g3epryrzHqi9aufMTFaFI2Tvxe20TUJGK6X80cY7z6kJ8SErDa1aIY96Jg94gKA15bRwBqY-aFbskBE7DfHUQYy13xuQFYIPTZKj14AVEi1Lj5fBVfCaIjz21OeUyF-HCYTNfYZSAwnFHI-P8e6Lm8FgBmjLdt-zX8Dg";

    let env = ExecutorEnv::builder()
        .write(&jwt)
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
    println!(
        "Gen time elapsed: {:?}",
        elapsed
    );



    let committed: String = prove_info.receipt
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

    println!("Inner json: {}", extracted_values);
}
