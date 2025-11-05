use compile_regex::{_create_dfa_string};

fn main() {
    let re = r"J.* K.* Hibbert";
    // println!("{:?}", _create_dfa(re).unwrap());
    match _create_dfa_string(re) {
        Ok(s) => println!("{s}"),
        Err(e) => eprintln!("{e}"),
    }
}
