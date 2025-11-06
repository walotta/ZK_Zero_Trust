use risc0_zkvm::guest::env;
use regex::Regex;

static REGEX_EXP: &str = include_str!("regex.txt");

fn main() {
    let eval_str: String = env::read();
    env::commit(&Regex::new(REGEX_EXP)
        .unwrap()
        .is_match(&eval_str));
}
