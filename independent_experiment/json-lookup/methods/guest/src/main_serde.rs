mod key_table;

use key_table::KEY_TABLE;
use risc0_zkvm::guest::env;
use serde_json::Value;

fn main() {
    let payload_str: String = env::read();
    let positions: Vec<usize> = env::read();
    let key_count = positions.len() / 4;
    assert!(
        key_count <= KEY_TABLE.len(),
        "positions exceed known key table"
    );

    let payload: Value =
        serde_json::from_str(&payload_str).expect("payload must be a valid JSON object");
    let obj = payload
        .as_object()
        .expect("payload must be a JSON object at the top level");

    let mut extracted_values = Vec::with_capacity(key_count);
    for key in KEY_TABLE.iter().take(key_count) {
        let value = obj
            .get(*key)
            .unwrap_or_else(|| panic!("missing key {key} in payload"));
        let string_value = value
            .as_str()
            .unwrap_or_else(|| panic!("value for {key} must be a JSON string"));
        extracted_values.push(string_value.to_string());
    }

    env::commit(&extracted_values);
}
