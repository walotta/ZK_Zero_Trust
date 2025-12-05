# Zero-Knowledge Zero Trust

# How to run

1. install `risc0`: https://github.com/risc0/risc0

```bash
curl -L https://risczero.com/install | bash
rzup install
```

2. Makesure `xacml-to-rust` installed under tools
```bash
git submodule update --init --recursive
```
The compiled example policies is already under this submodule, you could also re-compile following the readme of `xacml-to-rust`

3. Running with batch

```bash
python batch_exec.py
```
