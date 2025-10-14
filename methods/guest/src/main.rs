use policy_core::Inputs;
use regex_automata::dfa::{dense::DFA, Automaton};
use regex_automata::Input;
use risc0_zkvm::guest::env;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use rsa::{pkcs1v15::{Signature, VerifyingKey}, BigUint, RsaPublicKey};
use sha2::Sha256;
use signature::Verifier;

fn eval_regex(regex_input: &str, regex_exp: &[u8]) -> bool {
    match DFA::from_bytes(regex_exp) {
        Ok((dfa, _)) => {
            let input = Input::new(regex_input);
            match dfa.try_search_fwd(&input) {
                Ok(result) => result.is_some(),
                Err(_) => false,
            }
        }
        Err(_) => false,
    }
}

const MODULUS_B64: &str = "6scD7VyKosMBqvDwZZDIGmjGAzn6nUK83PsaVwtOBqrJBDqOGcqqFpiKdqV9N_SjZVEslzo8_0gq5MYqNp3fzkHBIUr_7oTgVlfpXGJOspV4abPTeoXQYYVSJT_RyPQLTPZ17O_D-cvGEC0bjFN--Aa8iPnz4lU8sD-oeCqEuZDHTHQgmZhM-_kVIiysfDz968R5rXUi_G44arVbXIwRZUC0SCZq96syQIxedGUkWRvQyehHnxuBS69xCSDBqxK66c3DXy0aWpVvW1Q0oaMcnzUPFl-g-LqULt5L1BFfDYVcICXms12HQFola2rho-I67-UnFecVsWTTQ8LgBQV0GQ";
const EXPONENT_B64: &str = "AQAB";
const JWT_FIELD: &[&str] = &["subject_id"];

fn extract_jwt(token: &str, positions: &Vec<usize>) -> Vec<String> {
    let mut parts = token.split('.');
    let header_b64 = parts.next().expect("jwt header");
    let payload_b64 = parts.next().expect("jwt payload");
    let signature_b64 = parts.next().expect("jwt signature");
    assert!(parts.next().is_none(), "jwt should have exactly 3 parts");

    let engine = URL_SAFE_NO_PAD;
    let _header = engine.decode(header_b64).expect("header base64");
    let payload = engine.decode(payload_b64).expect("payload base64");
    let signature_bytes = engine.decode(signature_b64).expect("signature base64");

    let n_bytes = engine.decode(MODULUS_B64).expect("modulus base64");
    let e_bytes = engine.decode(EXPONENT_B64).expect("exponent base64");
    let n = BigUint::from_bytes_be(&n_bytes);
    let e = BigUint::from_bytes_be(&e_bytes);
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
    return extracted_values;
}

static RE_2648DA3939BEBE6640528CB1A7924ED9: &[u8] =
    include_bytes!("RE_2648DA3939BEBE6640528CB1A7924ED9.bin");

static RE_ADEA8ABAFA89413F0FAB690611A89A56: &[u8] =
    include_bytes!("RE_ADEA8ABAFA89413F0FAB690611A89A56.bin");

#[derive(Debug, PartialEq)]
enum Result {
    Permit,
    Deny,
    NotApplicable,
}

fn evaluate_cond_policy_rule(inp: &Inputs, jwt_dict: &Vec<String>) -> bool {
    (eval_regex(
        &jwt_dict[0],
        &RE_2648DA3939BEBE6640528CB1A7924ED9,
    )) || (eval_regex(
        &jwt_dict[0],
        &RE_ADEA8ABAFA89413F0FAB690611A89A56,
    ))
}

fn evaluate_rule_policy_rule(inp: &Inputs, jwt_dict: &Vec<String>) -> Result {
    if evaluate_cond_policy_rule(inp, jwt_dict) {
        return Result::Permit;
    } else {
        return Result::NotApplicable;
    }
}

fn evaluate_policy_policy(inp: &Inputs, jwt_dict: &Vec<String>) -> Result {
    let results = vec![evaluate_rule_policy_rule(inp, jwt_dict)];

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
    let jwt_positions: Vec<usize> = env::read();
    let jwt_dict: Vec<String> = extract_jwt(&inp.jwt, &jwt_positions);  // if no jwt field used, put this None

    let decision = match evaluate_policy_policy(&inp, &jwt_dict) {
        Result::Permit => true,
        _ => false,
    };

    env::commit(&decision);
}
