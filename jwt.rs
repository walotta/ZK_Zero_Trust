// Generated JWT constants (N/E via include_bytes!, no base64 at runtime)
static SECRET_KEY: &str = r#"
{
  "alg": "RS256",
  "d": "UZjotwLuViJTfo9t5cbbnT4j7_QjM6wBywXkwjL2I-AQrE0TnUgwNFlA6nqa2itG7Mw5JLhDgfAZpFhxTHkzU1LMJl-UMthwxeGZBBhQxMWpS4eJ7S_73CEDi1mydlbHZLDWDIrKgJN_m5ip1ewhGV_x_-NrjZLVXGZLjbQtW_aYuEasMx4Rtb9tIj-pXNXVftKRq7MlfJIPgLYmg6HWh7ma8_wEbQ2P9JL2UHwaIhFC3aElJqGysUMmrTbZYDEyMJ6Far4uoj_WpbmfOMSU36TNvQHY1S26a_Tq3AqZWT07cxxuTMGN_vRifZbb9xPZSFMAp_sbKBztinEp5VW1Fw",
  "dp": "qZVI41hnVFK8Zb1moMBCUrKAHSsAJLtcBi6TndMA1Wv-bZSfmXKBNklcgSyeqPo6tHUDXfBUn3SaUy8EICKMi7kueGlJztvearRMk2SxFazMRLIAgBQeUXCAs95_7ZwJEqcm19QfvwvcFgzyYP4BGhvk4FUzTgjQc9dnUkVOyp0",
  "dq": "ENirr0Kc8hWqmqGsTA7HJ4ETOht6AsehPCr9n-fZEHRhzkakUp3qEtT6OW-pjCxFluZz73OKfm665TP2b27q3Zulo7o8H-WlyJR1cKIJpXzuaLna95eIvXUkqIPz4n5tK3Vs25PMyOK1Mrk9o3AvOlcCMLd0rOaQVKzoAcBLSW8",
  "e": "AQAB",
  "key_ops": [
    "sign"
  ],
  "kty": "RSA",
  "n": "6scD7VyKosMBqvDwZZDIGmjGAzn6nUK83PsaVwtOBqrJBDqOGcqqFpiKdqV9N_SjZVEslzo8_0gq5MYqNp3fzkHBIUr_7oTgVlfpXGJOspV4abPTeoXQYYVSJT_RyPQLTPZ17O_D-cvGEC0bjFN--Aa8iPnz4lU8sD-oeCqEuZDHTHQgmZhM-_kVIiysfDz968R5rXUi_G44arVbXIwRZUC0SCZq96syQIxedGUkWRvQyehHnxuBS69xCSDBqxK66c3DXy0aWpVvW1Q0oaMcnzUPFl-g-LqULt5L1BFfDYVcICXms12HQFola2rho-I67-UnFecVsWTTQ8LgBQV0GQ",
  "p": "-Ga638V4j2ubNZmD39xQcOe4xkNXI82y_q0Oo20yUaosel7CC8DBlLLabEikRHt46i0EbC8dmlIyU6io_bcWLciO0pRu9LcIZxj6DyKqLTwrQ7k30kC8zUmgp-SOvtRnk_nIih2izOFQuJxRsakoHBZ4ELgfPG7mkKqduOrTCds",
  "q": "8fWYNGrVHrkRWkk2AzO9QLM8Q-y1AQu5-LgersnqIvo8Z3rYEaE5Us_BEzyz-HjVXvxJtuyHbqYHSiko3ZKAuxPf361oTb8gYmtFWVfuBTGlUU8IVBIyNk00cARJS9AuVcJqimNSyoFEW7KY-d_yOlxgQhHrQwA8xgCZbHb_Xhs",
  "qi": "sQ2mb8dMBstHbLlnyheKL-D2NjD-LDalOmrm0igDPJKA2lHxnAiKmQIQbH1H9YH_-fA2cg8q3GCi0ziRL0VcWNQ2lFCRFMx3_xj8pRHWgLdvar4NH85Rq_C3Ex0upV79Sm7f6bh_6o6sDOclWGGJO1POzAPyncGPkiY1tvdgqck",
  "use": "sig",
  "kid": "0c194722699344da9b7a0474a52eb342"
}
"#;

static PUBLIC_KEY: &str = r#" { "alg": "RS256", "e": "AQAB", "key_ops": ["verify"], "kty": "RSA", "n": "6scD7VyKosMBqvDwZZDIGmjGAzn6nUK83PsaVwtOBqrJBDqOGcqqFpiKdqV9N_SjZVEslzo8_0gq5MYqNp3fzkHBIUr_7oTgVlfpXGJOspV4abPTeoXQYYVSJT_RyPQLTPZ17O_D-cvGEC0bjFN--Aa8iPnz4lU8sD-oeCqEuZDHTHQgmZhM-_kVIiysfDz968R5rXUi_G44arVbXIwRZUC0SCZq96syQIxedGUkWRvQyehHnxuBS69xCSDBqxK66c3DXy0aWpVvW1Q0oaMcnzUPFl-g-LqULt5L1BFfDYVcICXms12HQFola2rho-I67-UnFecVsWTTQ8LgBQV0GQ", "use": "sig", "kid": "0c194722699344da9b7a0474a52eb342" } "#;

pub const JWT: &str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjBjMTk0NzIyNjk5MzQ0ZGE5YjdhMDQ3NGE1MmViMzQyIn0.eyJpc3MiOiJodHRwczovL2xvZ2luLmV4YW1wbGUuY29tLyIsInN1YmplY3RfaWQiOiJKdWxpdXMgSGliYmVydCIsImF1ZCI6ImFwaTovL3BheW1lbnRzLXNlcnZpY2UiLCJleHAiOjE3NjE4NjE3NTcsImlhdCI6MTc2MTg1ODE1NywiYXV0aF90aW1lIjoxNzYxODU4MDU3LCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibm9uY2UiOiIzZTRmMGY2Ny1iYzVhLTQxM2QtYjUyOC05M2ZkMWM3MWZkNGUiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIG9mZmxpbmVfYWNjZXNzIiwicm9sZXMiOiJhZG1pbiJ9.cmFikrqrKYH63nA9QHuukGJ4MFZakICPUs6PH0KkBmlhENfES6ZWZ4g9u1C2poozY392yC4GxGMuTfQqulGyuJRYAVOB552DIqVsqNFC3PdSAmE8RPsqSuePnMmeQs0NxBiaVC2dGcfLd0CDA80lXJ5cNazUroEzSRz69MZgWf9QX63ImIRG7uyzVHzVswHUgddvMVVRQ0CAilNjOAXNUzdXsIuEb20XJDjBWzRisAF2WfQZSIj5mkc2JbrWx2fthv66VP9PGqSqpjD6hNOeJ2KYnbjKaKX2Ah7s43myA1xNIenO_BckkuGt5gctV2p0SQ6QAzIZqs-hQODcDbZPVw";
pub const KEY_ID: &str = "0c194722699344da9b7a0474a52eb342";

pub static N_BYTES: &[u8] = include_bytes!("keys/modulus.bin");
pub static E_BYTES: &[u8] = include_bytes!("keys/exponent.bin");
