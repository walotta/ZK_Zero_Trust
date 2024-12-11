use matrix_core::{Outputs, Inputs};
use risc0_zkvm::guest::env;

fn main() {
    let inp: Inputs = env::read();
    let mut out: Vec<usize> = Vec::with_capacity(inp.m*inp.p);
    for i in 0..inp.m{
        for j in 0..inp.p{
            assert!(i*inp.p+j==out.len());
            out.push(inp.data[i*inp.n] * inp.data[inp.m*inp.n+j]);
            for k in 1..inp.n{
                out[i*inp.p+j] += inp.data[i*inp.n+k] * inp.data[inp.m*inp.n+k*inp.p+j]
            }
        }
    }
    let res: Outputs = Outputs{m: inp.m, p: inp.p, data: out};
    env::commit(&res);
}