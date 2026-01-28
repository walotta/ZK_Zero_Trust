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

4. Analyze the results

The running result will show as a log file under `logs` folder. You need to move the log file to `data/end2end` folder for analysis.

```bash
mv logs/<log_file_name> data/end2end/end2end.log
python data/end2end/extract.py
```