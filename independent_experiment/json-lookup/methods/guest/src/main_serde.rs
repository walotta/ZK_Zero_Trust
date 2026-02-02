mod key_table;

use key_table::Outputs;
use risc0_zkvm::guest::env;

fn main() {
    let payload_str: String = env::read();
    // let _: Vec<usize> = env::read(); // Positions unused for serde-based extraction.

    let outputs: Outputs =
        serde_json::from_str(&payload_str).expect("payload must be a valid JSON object");
    let extracted_values = outputs.into_vec();

    env::commit(&extracted_values);
}
