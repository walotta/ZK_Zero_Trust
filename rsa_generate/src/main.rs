use jwt_rsa_verify::prove_signature_verification;
use jwt_rsa_verify_methods::RSA_VERIFY_ID;

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let (receipt, keys, extracted_values) = prove_signature_verification();

    receipt
        .verify(RSA_VERIFY_ID)
        .expect("Proof of RSA signature verification should succeed");

    println!("Verified JWT field           : {:?}", keys);
    println!("Verified JWT extracted values: {:?}", extracted_values);
}
