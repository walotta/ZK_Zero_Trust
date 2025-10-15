// Copyright 2024 RISC Zero, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
use policy_core::Inputs;
use policy_methods::{POLICY_ELF, POLICY_ID};
use risc0_zkvm::{default_prover, ExecutorEnv};
use std::time::Instant;
use std::env;
use std::process;
use std::fs;
use serde::Deserialize;
// use std::io::stdin;

use regex_automata::dfa::dense::DFA;
use regex_automata::nfa::thompson;
use regex_automata::{dfa::Automaton, Input};
use base64::{Engine as _, engine::general_purpose};

#[derive(Deserialize)]
struct Response {
    decision: bool,
}

fn _create_dfa_example() -> Result<(), Box<dyn std::error::Error>> {
    let re = r"B.* O.* Simpson";
    // let re = r"J.* K.* Hibbert";
    let nfa = thompson::NFA::compiler().build(re)?;
    let dfa = DFA::builder().build_from_nfa(&nfa)?;

    #[cfg(target_endian = "little")]
    let (bytes, pad) = {
        let (b, p) = dfa.to_bytes_little_endian();
        (b, p)
    };
    println!("DFA bytes: {:?}, {:?}", bytes, pad);

    let base64_encoded = general_purpose::STANDARD.encode(&bytes);
    println!("Base64 encoded DFA bytes: {}", base64_encoded);

    let decoded_bytes = general_purpose::STANDARD.decode(&base64_encoded)?;
    #[cfg(target_endian = "little")]
    let slice = if pad <= decoded_bytes.len() { &decoded_bytes[pad..] } else { &decoded_bytes[..] };
    let dfa_new: DFA<&[u32]> = DFA::from_bytes(slice)?.0;

    // Test the DFA with some example strings
    let test_strings = vec![
        "John K. Hibbert",
        "Jane K. Hibbert",
        "Jack Kevin Hibbert",
        "Bob Smith",
    ];

    for test_str in test_strings {
        let input = Input::new(test_str);
        let result = dfa_new.try_search_fwd(&input)?;
        match result {
            Some(m) => println!("'{}' matches at offset {}", test_str, m.offset()),
            None => println!("'{}' does not match", test_str),
        }
    }

    Ok(())
}

fn main() {
    // Create and test DFA
    // if let Err(e) = _create_dfa_example() {
    //     eprintln!("DFA creation failed: {}", e);
    // }

    let args: Vec<String> = env::args().collect();

    if args.len() != 3 {
        eprintln!("Usage: {} <request_file> <responses_file>", args[0]);
        process::exit(1);
    }

    let request_file = &args[1];
    let responses_file = &args[2];

    // Read and parse JSON from request file
    let json_content = match fs::read_to_string(request_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("Error reading request file '{}': {}", request_file, e);
            process::exit(1);
        }
    };

    let init_inp: Inputs = match serde_json::from_str(&json_content) {
        Ok(inputs) => inputs,
        Err(e) => {
            eprintln!("Error parsing JSON from request file '{}': {}", request_file, e);
            process::exit(1);
        }
    };

    let responses_content = match fs::read_to_string(responses_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("Error reading responses file '{}': {}", responses_file, e);
            process::exit(1);
        }
    };

    let response: Response = match serde_json::from_str(&responses_content) {
        Ok(response) => response,
        Err(e) => {
            eprintln!("Error parsing JSON from responses file '{}': {}", responses_file, e);
            process::exit(1);
        }
    };

    let decision = if response.decision {
        "Permit".to_string()
    } else {
        "Deny".to_string()
    };

    println!("Parsed inputs: {:?}", init_inp);
    let permit = policy_verify(init_inp.clone());
    println!("Permit decision: {}/{}", permit, decision);
    if permit != decision {
        println!("Permit does not match the decision in the responses file.");
        process::exit(1);
    }
}

fn policy_verify(inp: Inputs) -> String {
    // println!("policy verify for subject_id: {}, resource_id: {},action_id: {}", inp.subject_id, inp.resource_id, inp.action_id);
    let env = ExecutorEnv::builder()
        .write(&inp)
        .unwrap()
        .build()
        .unwrap();

    // Obtain the default prover.
    let prover = default_prover();

    // Produce a receipt by proving the specified ELF binary.

    let gen_start_time = Instant::now();
    let prove_info = prover.prove(env, POLICY_ELF).unwrap();
    let gen_end_time = Instant::now();

    let verify_start_time = Instant::now();
    prove_info.receipt.verify(POLICY_ID).unwrap();
    let verify_end_time = Instant::now();


    println!("Number of segments: {}", prove_info.stats.segments);
    println!("Total cycles: {}", prove_info.stats.total_cycles);
    println!("User cycles: {}", prove_info.stats.user_cycles);
    println!("Proof size: {} bytes", prove_info.receipt.inner.composite().unwrap().seal_size());
    println!("Gen time elapsed: {:?}", gen_end_time.duration_since(gen_start_time));
    println!("Verify time elapsed: {:?}", verify_end_time.duration_since(verify_start_time));
    // println!("{:?}", prove_info.receipt.inner.composite().unwrap());

    let permit = prove_info.receipt.journal.decode().unwrap();
    if permit {
        "Permit".to_string()
    } else {
        "Deny".to_string()
    }
}
