use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use risc0_zkvm::guest::env;
use rsa::{pkcs1v15::{Signature, VerifyingKey}, BigUint, RsaPublicKey};
use sha2::Sha256;
use signature::Verifier;

static MODULUS: &[u8] = include_bytes!("modulus.bin");
static EXPONENT: &[u8] = include_bytes!("exponent.bin");

fn main() {
    // Read the JWT string from the host.
    let token: String = env::read();

    let mut parts = token.split('.');
    let header_b64 = parts.next().expect("jwt header");
    let payload_b64 = parts.next().expect("jwt payload");
    let signature_b64 = parts.next().expect("jwt signature");
    assert!(parts.next().is_none(), "jwt should have exactly 3 parts");

    let engine = URL_SAFE_NO_PAD;
    let _header = engine.decode(header_b64).expect("header base64");
    let payload = engine.decode(payload_b64).expect("payload base64");
    let signature_bytes = engine.decode(signature_b64).expect("signature base64");

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
    env::commit(&payload_str);
}

