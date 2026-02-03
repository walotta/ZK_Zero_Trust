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

use regex_automata::dfa::{dense::DFA, Automaton};
use regex_automata::Input;

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

static RE_E8667202B740D84E03552D30B7B93A62: &[u8] =
    include_bytes!("RE_E8667202B740D84E03552D30B7B93A62.bin");

static RE_9BAAFAEEB1212012972ABC54D5797FBD: &[u8] =
    include_bytes!("RE_9BAAFAEEB1212012972ABC54D5797FBD.bin");

use serde::Deserialize;

#[derive(Deserialize)]
struct JwtPayload {
    sub: Option<String>,
    role: Option<String>,
    age: Option<String>,
}

fn jwt_field_check(inp: &Inputs, jwt: &JwtPayload) -> bool {
    for field in JWT_FIELD.iter() {
        match *field {
            "sub" => {
                if jwt.sub.as_deref() != Some(inp.access_subject_subject_id.as_str()) {
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

fn extract_jwt(token: &str, inp: &Inputs) -> bool {
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

    // this is the case where a policy expects a subject, role, or age field, but the request was missing the required field
    //if positions.is_empty() {
    //    return true;
    //}
    let jwt_struct: JwtPayload = serde_json::from_str(&payload_str).expect("invalid JWT JSON");

    return jwt_field_check(&inp, &jwt_struct);
}

#[derive(Debug, PartialEq)]
enum Result {
    Permit,
    Deny,
    NotApplicable,
}

fn evaluate_cond_policy_rule(inp: &Inputs) -> bool {
    (eval_regex(
        &inp.access_subject_subject_id,
        &RE_E8667202B740D84E03552D30B7B93A62,
    )) || (eval_regex(
        &inp.access_subject_subject_id,
        &RE_9BAAFAEEB1212012972ABC54D5797FBD,
    ))
}

fn evaluate_rule_policy_rule(inp: &Inputs) -> Result {
    if evaluate_cond_policy_rule(inp) {
        return Result::Permit;
    } else {
        return Result::NotApplicable;
    }
}

fn evaluate_target_policy(_inp: &Inputs) -> bool {
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

    let mut decision = match evaluate_policy_policy(&inp) {
        Result::Permit => true,
        _ => false,
    };

    let jwt: String = env::read();
    if !extract_jwt(&jwt, &inp) {
        decision = false;
    }

    env::commit(&decision);
    env::commit(&inp);
}
