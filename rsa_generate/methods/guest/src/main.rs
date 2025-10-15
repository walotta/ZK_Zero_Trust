use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use risc0_zkvm::guest::env;
use rsa::{pkcs1v15::{Signature, VerifyingKey}, BigUint, RsaPublicKey};
use sha2::Sha256;
use signature::Verifier;

// const MODULUS_B64: &str = "zcQwXx3EevOSkfH0VSWqtfmWTL4c2oIzW6u83qKO1W7XjLgTqpryL5vNCaxbVTkpU-GZctit0n6kj570tfny_sy6pb2q9wlvFBmDVyD-nL5oNjP5s3qEfvy15Bl9vMGFf3zycqMaVg_7VRVwK5d8QzpnVC0AGT10QdHnyGCadfPJqazTuVRp1f3ecK7bg7596sgVb8d9Wpaz2XPykQPfphsEb40vcp1tPN95-eRCgA24PwfUaKYHQQFMEQY_atJWbffyJ91zsBRy8fEQdfuQVZIRVQgO7FTsmLmQAHxR1dl2jP8B6zonWmtqWoMHoZfa-kmTPB4wNHa8EaLvtQ1060qYFmQWWumfNFnG7HNq2gTHt1cN1HCwstRGIaU_ZHubM_FKH_gLfJPKNW0KWML9mQQzf4AVov0Yfvk89WxY8ilSRx6KodJuIKKqwVh_58PJPLmBqszEfkTjtyxPwP8X8xRXfSz-vTU6vESCk3O6TRknoJkC2BJZ_ONQ0U5dxLcx";
const EXPONENT_B64: &str = "AQAB";
const MODULUS_B64: &str = "6scD7VyKosMBqvDwZZDIGmjGAzn6nUK83PsaVwtOBqrJBDqOGcqqFpiKdqV9N_SjZVEslzo8_0gq5MYqNp3fzkHBIUr_7oTgVlfpXGJOspV4abPTeoXQYYVSJT_RyPQLTPZ17O_D-cvGEC0bjFN--Aa8iPnz4lU8sD-oeCqEuZDHTHQgmZhM-_kVIiysfDz968R5rXUi_G44arVbXIwRZUC0SCZq96syQIxedGUkWRvQyehHnxuBS69xCSDBqxK66c3DXy0aWpVvW1Q0oaMcnzUPFl-g-LqULt5L1BFfDYVcICXms12HQFola2rho-I67-UnFecVsWTTQ8LgBQV0GQ";

fn main() {
    // Read the JWT string from the host.
    let token: String = env::read();
    let keys: Vec<String> = env::read();
    let positions: Vec<usize> = env::read();

    let mut parts = token.split('.');
    let header_b64 = parts.next().expect("jwt header");
    let payload_b64 = parts.next().expect("jwt payload");
    let signature_b64 = parts.next().expect("jwt signature");
    assert!(parts.next().is_none(), "jwt should have exactly 3 parts");

    let engine = URL_SAFE_NO_PAD;
    let _header = engine.decode(header_b64).expect("header base64");
    let payload = engine.decode(payload_b64).expect("payload base64");
    let signature_bytes = engine.decode(signature_b64).expect("signature base64");

    let public_key = build_public_key();
    let verifying_key = VerifyingKey::<Sha256>::new(public_key);
    let signature = Signature::try_from(signature_bytes.as_slice()).expect("signature format");

    let signed_data = format!("{}.{}", header_b64, payload_b64);
    verifying_key
        .verify(signed_data.as_bytes(), &signature)
        .expect("RSA signature check");

    let payload_str = String::from_utf8(payload).expect("payload utf8");

    // Verify quote positions and extract values
    let mut extracted_values = Vec::new();
    for (i, key) in keys.iter().enumerate() {
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
    env::commit(&keys);
    env::commit(&extracted_values);
}

fn build_public_key() -> RsaPublicKey {
    let engine = URL_SAFE_NO_PAD;
    let n_bytes = engine.decode(MODULUS_B64).expect("modulus base64");
    let e_bytes = engine.decode(EXPONENT_B64).expect("exponent base64");
    let n = BigUint::from_bytes_be(&n_bytes);
    let e = BigUint::from_bytes_be(&e_bytes);
    RsaPublicKey::new(n, e).expect("valid RSA public key")
}
