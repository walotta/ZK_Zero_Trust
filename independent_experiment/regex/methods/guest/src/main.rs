use risc0_zkvm::guest::env;
use regex_automata::dfa::{dense::DFA, Automaton};
use regex_automata::Input;

fn eval_regex(regex_input: &String, regex_exp: &[u8]) -> bool {
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

static REGEX_BYTES: &[u8] = include_bytes!("regex.bin");
// static REGEX_BYTES: &[u8] = include_bytes!("RE_2648DA3939BEBE6640528CB1A7924ED9.bin");

fn main() {
    let eval_str: String = env::read();
    // assert_eq!(eval_str, "Julius Hibbert");
    // env::commit(&eval_str.eq("Julius Hibbert"));
    // env::commit(&eval_regex(&"Julius Hibbert", &REGEX_BYTES));
    env::commit(&eval_regex(&eval_str, &REGEX_BYTES));
}
