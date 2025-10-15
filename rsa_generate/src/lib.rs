use jwt_rsa_verify_methods::RSA_VERIFY_ELF;
use regex::Regex;
use risc0_zkvm::{default_prover, ExecutorEnv, Receipt};
use std::time::Instant;
use base64::{engine::general_purpose, Engine as _};

const JWT: &str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjBjMTk0NzIyNjk5MzQ0ZGE5YjdhMDQ3NGE1MmViMzQyIn0.eyJpc3MiOiJodHRwczovL2xvZ2luLmV4YW1wbGUuY29tLyIsInN1YmplY3RfaWQiOiJKdWxpdXMgSGliYmVydCIsImF1ZCI6ImFwaTovL3BheW1lbnRzLXNlcnZpY2UiLCJleHAiOjE3NjA1NTA1MDYsImlhdCI6MTc2MDU0NjkwNiwiYXV0aF90aW1lIjoxNzYwNTQ2ODA2LCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibm9uY2UiOiIzZTRmMGY2Ny1iYzVhLTQxM2QtYjUyOC05M2ZkMWM3MWZkNGUiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwicm9sZXMiOiJhZG1pbiJ9.Ma40rE17qDi2PfJVX11QF-v-SIcqF3lG0j-_anZqOAwyvQt7Pj8KoLwSOcXRCN169kYuNyzYBXzgJt3raYc4mpytSZWY_xpxBKh8141vuZZGGq2A1aN-0Fe_oxXsp2JrBqrI-VrOkSmKsYmkX7DyXCl0fdbtPLBS3gd81DLn3pg50Epbg5sP5vPCwWpZeY2EOs4qayLiAaIGZgj-cgRxI286Kwayei1LhIiZAayOrYZJE-WvQmC7oChcRgzoNIjt9VzSmHlZIAlU0gJZyzky7Ipa5oqvMV0S2Shp9C2kAJbKU-ZKYSOI_EtCsij24P-QCG4O2heWIK3ahiVOSIdbkg";
const JWT_FIELD: &[&str] = &["subject_id"];

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

pub fn prove_signature_verification() -> (Receipt, Vec<String>, Vec<String>) {

    let mut jwtparts = JWT.split('.');
    let _header = jwtparts.next().ok_or("missing header in jwt");
    let payload_str = String::from_utf8(
        general_purpose::URL_SAFE_NO_PAD
            .decode(jwtparts.next().ok_or("missing body in jwt").unwrap())
            .unwrap(),
    )
    .unwrap();

    let mut positions = Vec::new();

    for key in JWT_FIELD {
        let key_pos = find_key_value_quotes(&payload_str, key).unwrap();
        positions.extend_from_slice(&[key_pos.0, key_pos.1, key_pos.2, key_pos.3]);
    }

    let env = ExecutorEnv::builder()
        .write(&JWT)
        .expect("write jwt to env")
        .write(&JWT_FIELD)
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

    (prove_info.receipt, keys, extracted_values)
}
