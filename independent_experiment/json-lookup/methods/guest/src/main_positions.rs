mod key_table;

use key_table::KEY_TABLE;
use risc0_zkvm::guest::env;

fn main() {
    let payload_str: String = env::read();
    let positions: Vec<usize> = env::read();

    assert_eq!(
        positions.len() % 4,
        0,
        "positions length must be divisible by four"
    );
    let chunk_count = positions.len() / 4;
    assert!(
        chunk_count <= KEY_TABLE.len(),
        "positions exceed known key table"
    );

    let mut extracted_values = Vec::with_capacity(chunk_count);
    for (key, chunk) in KEY_TABLE.iter().zip(positions.chunks_exact(4)) {
        extracted_values.push(verify_and_extract(&payload_str, chunk, key));
    }

    env::commit(&extracted_values);
}

fn verify_and_extract(payload: &str, chunk: &[usize], key: &str) -> String {
    let key_start = chunk[0];
    let key_end = chunk[1];
    let value_start = chunk[2];
    let value_end = chunk[3];

    let key_part = &payload[key_start..=key_end];
    let expected_key = format!("\"{}\"", key);
    assert_eq!(key_part, expected_key, "Key position verification failed");

    let separator = &payload[key_end + 1..value_start];
    assert!(
        separator.chars().all(|c| c == ' ' || c == ':'),
        "Separator should only contain spaces and colon"
    );
    let colon_count = separator.chars().filter(|&c| c == ':').count();
    assert_eq!(colon_count, 1, "Separator must contain exactly one colon");

    assert_eq!(
        &payload[value_start..value_start + 1],
        "\"",
        "Value should start with quote"
    );
    assert_eq!(
        &payload[value_end..value_end + 1],
        "\"",
        "Value should end with quote"
    );

    payload[value_start + 1..value_end].to_string()
}
