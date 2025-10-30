// use base64::engine::general_purpose::URL_SAFE_NO_PAD;
// use base64::Engine;
use risc0_zkvm::guest::env;
// use rsa::{pkcs1v15::{Signature, VerifyingKey}, BigUint, RsaPublicKey};
// use sha2::Sha256;
// use signature::Verifier;

// static MODULUS: &[u8] = include_bytes!("modulus.bin");
// static EXPONENT: &[u8] = include_bytes!("exponent.bin");
const JWT_FIELD: &[&str] = &["subject_id", "iss"];

fn main() {
    // Read the JWT string from the host.
    let payload_str: String = env::read();
    let positions: Vec<usize> = env::read();

    // Verify quote positions and extract values
    let mut extracted_values = Vec::new();
    for (i, key) in JWT_FIELD.iter().enumerate() {
        let key_start = positions[i * 4];
        let key_end = positions[i * 4 + 1];
        let value_start = positions[i * 4 + 2];
        let value_end = positions[i * 4 + 3];

        // Verify the positions correspond to the expected key-value pair
        let key_part = &payload_str[key_start..=key_end];
        let expected_key = format!("\"{}\"", key);
        assert_eq!(key_part, expected_key, "Key position verification failed");

        // Verify the separator between key and value (should only contain spaces and colon)
        let separator = &payload_str[key_end + 1..value_start];
        assert!(separator.chars().all(|c| c == ' ' || c == ':'), "Separator should only contain spaces and colon");
        let colon_count = separator.chars().filter(|&c| c == ':').count();
        assert_eq!(colon_count, 1, "Separator must contain exactly one colon");

        // Verify value quotes are correct
        assert_eq!(&payload_str[value_start..value_start+1], "\"", "Value should start with quote");
        assert_eq!(&payload_str[value_end..value_end+1], "\"", "Value should end with quote");

        // Extract the value (without quotes)
        let value = &payload_str[value_start+1..value_end];
        extracted_values.push(value.to_string());
    }

    // Commit the extracted values instead of full payload
    env::commit(&extracted_values);
}

