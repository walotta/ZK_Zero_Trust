use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use policy_core::Inputs;
use risc0_zkvm::guest::env;
use rsa::{
    pkcs1v15::{Signature, VerifyingKey},
    BigUint, RsaPublicKey,
};
use sha2::Sha256;
use signature::Verifier;

fn jwt_field_check(inp: &Inputs, extracted_values: &[String]) -> bool {
    for (i, field) in JWT_FIELD.iter().enumerate() {
        match *field {
            "sub" => {
                if extracted_values[i] != inp.access_subject_subject_id {
                    return false;
                }
            }
            "role" => {
                if extracted_values[i] != inp.access_subject_role {
                    return false;
                }
            }
            "age" => {
                // Age might be numeric — convert if needed
                if extracted_values[i] != inp.access_subject_age.to_string() {
                    return false;
                }
            }
            _ => unreachable!("Unknown field — should be impossible due to codegen"),
        }
    }

    true
}
static MODULUS: &[u8] = include_bytes!("modulus.bin");
static EXPONENT: &[u8] = include_bytes!("exponent.bin");
const JWT_FIELD: &[&str] = &["sub"];

fn extract_jwt(token: &str, positions: &Vec<usize>, inp: &Inputs) -> bool {
    let mut parts = token.split('.');
    let header_b64 = parts.next().expect("jwt header");
    let payload_b64 = parts.next().expect("jwt payload");
    let signature_b64 = parts.next().expect("jwt signature");
    assert!(parts.next().is_none(), "jwt should have exactly 3 parts");

    let engine = URL_SAFE_NO_PAD;
    let _header = engine.decode(header_b64).expect("header base64");
    let payload = engine.decode(payload_b64).expect("payload base64");
    let signature_bytes = engine.decode(signature_b64).expect("signature base64");

    // let n_bytes = engine.decode(MODULUS_B64).expect("modulus base64");
    // let e_bytes = engine.decode(EXPONENT_B64).expect("exponent base64");
    // let n = BigUint::from_bytes_be(&n_bytes);
    // let e = BigUint::from_bytes_be(&e_bytes);
    let n = BigUint::from_bytes_be(MODULUS);
    let e = BigUint::from_bytes_be(EXPONENT);
    let public_key = RsaPublicKey::new(n, e).expect("valid RSA public key");
    let verifying_key = VerifyingKey::<Sha256>::new(public_key);
    let signature = Signature::try_from(signature_bytes.as_slice()).expect("signature format");

    let signed_data = format!("{}.{}", header_b64, payload_b64);
    verifying_key
        .verify(signed_data.as_bytes(), &signature)
        .expect("RSA signature check");

    let payload_str = String::from_utf8(payload).expect("payload utf8");

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
        assert!(
            separator.chars().all(|c| c == ' ' || c == ':'),
            "Separator should only contain spaces and colon"
        );
        let colon_count = separator.chars().filter(|&c| c == ':').count();
        assert_eq!(colon_count, 1, "Separator must contain exactly one colon");

        // Verify value quotes are correct
        assert_eq!(
            &payload_str[value_start..value_start + 1],
            "\"",
            "Value should start with quote"
        );
        assert_eq!(
            &payload_str[value_end..value_end + 1],
            "\"",
            "Value should end with quote"
        );

        // Extract the value (without quotes)
        let value = &payload_str[value_start + 1..value_end];
        extracted_values.push(value.to_string());
    }

    return jwt_field_check(&inp, &extracted_values);
}

#[derive(Debug, PartialEq)]
enum Result {
    Permit,
    Deny,
    NotApplicable,
}

fn evaluate_target_policy_rule(inp: &Inputs) -> bool {
    (("Julius Hibbert" == inp.access_subject_subject_id)
        && ("http://medico.com/record/patient/BartSimpson" == inp.resource_resource_id)
        && (("read" == inp.action_action_id) || ("write" == inp.action_action_id)))
}

fn evaluate_rule_policy_rule(inp: &Inputs) -> Result {
    if !evaluate_target_policy_rule(inp) {
        return Result::NotApplicable;
    }

    return Result::Permit;
}

fn evaluate_target_policy(inp: &Inputs) -> bool {
    true
}

fn evaluate_policy_policy(inp: &Inputs) -> Result {
    if !evaluate_target_policy(inp) {
        return Result::NotApplicable;
    }

    let results = vec![evaluate_rule_policy_rule(inp)];

    //deny-overrides
    let mut atleast_one_permit = false;
    for res in &results {
        if *res == Result::Deny {
            return Result::Deny;
        } else if *res == Result::Permit {
            atleast_one_permit = true;
        }
    }
    if atleast_one_permit {
        return Result::Permit;
    }
    return Result::NotApplicable;
}

fn main() {
    let inp: Inputs = env::read();

    let decision = match evaluate_policy_policy(&inp) {
        Result::Permit => true,
        _ => false,
    };

    let jwt: String = env::read();
    let jwt_positions: Vec<usize> = env::read();
    if !extract_jwt(&jwt, &jwt_positions, &inp) {
        decision = false;
    }

    env::commit(&decision);
    env::commit(&inp);
}
