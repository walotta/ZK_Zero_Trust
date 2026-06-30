# Zero-Knowledge Zero Trust

# How to run

1. install `risc0`: https://github.com/risc0/risc0

```bash
curl -L https://risczero.com/install | bash
rzup install
```

2. Clone `xacml-to-rust` compiler under tools
```bash
git clone https://github.com/osaidameer/xacml-to-rust.git tools/xacml-to-rust
```
Then generate the policy datasets by running the compiler (see artifact appendix for details):
```bash
bash run_compiler.sh true
bash run_compiler.sh false
```

3. Running with batch

```bash
python batch_exec.py
```

4. Analyze the results

The running result will show as a log file under `logs` folder. You need to move the log file to `data/end2end` folder for analysis.

```bash
mv logs/<log_file_name> data/end2end/end2end.log
python data/end2end/extract.py
```