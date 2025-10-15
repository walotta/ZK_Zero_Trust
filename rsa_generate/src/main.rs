use jwt_rsa_verify::{prove_signature_verification, JwtProofResult};
use jwt_rsa_verify_methods::RSA_VERIFY_ID;

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    const SAMPLE_JWT: &str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjBjMTk0NzIyNjk5MzQ0ZGE5YjdhMDQ3NGE1MmViMzQyIn0.eyJpc3MiOiJodHRwczovL2xvZ2luLmV4YW1wbGUuY29tLyIsInN1YmplY3RfaWQiOiJKdWxpdXMgSGliYmVydCIsImF1ZCI6ImFwaTovL3BheW1lbnRzLXNlcnZpY2UiLCJleHAiOjE3NjA1NTA1MDYsImlhdCI6MTc2MDU0NjkwNiwiYXV0aF90aW1lIjoxNzYwNTQ2ODA2LCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibm9uY2UiOiIzZTRmMGY2Ny1iYzVhLTQxM2QtYjUyOC05M2ZkMWM3MWZkNGUiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwicm9sZXMiOiJhZG1pbiJ9.Ma40rE17qDi2PfJVX11QF-v-SIcqF3lG0j-_anZqOAwyvQt7Pj8KoLwSOcXRCN169kYuNyzYBXzgJt3raYc4mpytSZWY_xpxBKh8141vuZZGGq2A1aN-0Fe_oxXsp2JrBqrI-VrOkSmKsYmkX7DyXCl0fdbtPLBS3gd81DLn3pg50Epbg5sP5vPCwWpZeY2EOs4qayLiAaIGZgj-cgRxI286Kwayei1LhIiZAayOrYZJE-WvQmC7oChcRgzoNIjt9VzSmHlZIAlU0gJZyzky7Ipa5oqvMV0S2Shp9C2kAJbKU-ZKYSOI_EtCsij24P-QCG4O2heWIK3ahiVOSIdbkg";
    const SAMPLE_FIELDS: &[&str] = &["subject_id"];

    let field_names: Vec<String> = SAMPLE_FIELDS.iter().map(|s| s.to_string()).collect();
    let JwtProofResult {
        receipt,
        keys,
        extracted_values,
        ..
    } = prove_signature_verification(SAMPLE_JWT, &field_names);

    receipt
        .verify(RSA_VERIFY_ID)
        .expect("Proof of RSA signature verification should succeed");

    println!("Verified JWT field           : {:?}", keys);
    println!("Verified JWT extracted values: {:?}", extracted_values);
}
