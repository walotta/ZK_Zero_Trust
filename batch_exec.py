#!/usr/bin/env python3
import os
import shutil
import subprocess
from datetime import datetime

# POLICY_PROJECT = os.path.join(os.path.expandvars('$HOME'), 'risc0/examples/policy')
POLICY_PROJECT = os.getcwd()

# Source directories
SOURCE_BASE     = os.path.join(POLICY_PROJECT, 'tools/xacml-to-rust/output')
INPUT_DEF_DIR   = os.path.join(SOURCE_BASE, 'input_definition')
POLICY_CODE_DIR = os.path.join(SOURCE_BASE, 'policies_code')
REQUESTS_DIR     = os.path.join(SOURCE_BASE, 'Requests')
RESPONSES_DIR    = os.path.join(SOURCE_BASE, 'Responses')

# Target Risc0 example project
TARGET_LIB  = os.path.join(POLICY_PROJECT, 'core',    'src',   'lib.rs')
TARGET_MAIN = os.path.join(POLICY_PROJECT, 'methods', 'guest', 'src', 'main.rs')
GUEST_DIR = os.path.join(POLICY_PROJECT, 'methods', 'guest', 'src')

# Ensure target directories exist
os.makedirs(os.path.dirname(TARGET_LIB),  exist_ok=True)
os.makedirs(os.path.dirname(TARGET_MAIN), exist_ok=True)

# Prepare log file with timestamp
timestamp = datetime.now().strftime("logs/batch_%m_%d_%H_%M.log")
log_path = os.path.join(POLICY_PROJECT, timestamp)
print(f"All cargo output will be redirected to {log_path}")

os.system(f"cp {os.path.join(SOURCE_BASE, POLICY_CODE_DIR)}/*.bin {GUEST_DIR}/.")

testcases_names = ['_'.join(f.split('.')[0].split('_')[1:]) for f in os.listdir(POLICY_CODE_DIR) if f.endswith(".rs")]
testcases_names.sort()
# testcases_names = ["IIC057"]
testcases = dict()

for tc in testcases_names:
    testcases[tc] = {
        'request': os.path.join(REQUESTS_DIR, f"Request_{tc}.json"),
        'response': os.path.join(RESPONSES_DIR, f"Response_{tc}.json"),
        'input_definition': os.path.join(INPUT_DEF_DIR, f"Policy_{tc}.xml.rs"),
        'policy_code': os.path.join(POLICY_CODE_DIR, f"Policy_{tc}.xml.rs")
    }
    for key, value in testcases[tc].items():
        if not os.path.exists(value):
            raise FileNotFoundError(f"Missing {key.replace('_', ' ')} for testcase {tc}: {value}")
print(f"Get {len(testcases)} testcases ready for execution.")

# Open log file once for all runs
with open(log_path, 'w') as log_file:
    # Iterate over all .rs files in input_definition
    fail_cnt = 0
    for key, value in testcases.items():

        print(f'Processing policy: {key}')
        log_file.write(f"\n# ---------- {key} ----------\n")
        log_file.flush()

        # Copy input definition to core/src/lib.rs
        os.system(f"cp {value['input_definition']} {TARGET_LIB}")

        # Copy policy code to methods/guest/src/main.rs
        os.system(f"cp {value['policy_code']} {TARGET_MAIN}")

        # Run `cargo run --release`, redirecting both stdout and stderr
        print('Running: cargo run --release')
        try:
            subprocess.run(
                ['cargo', 'run', '--release', '--', value['request'], value['response']],
                cwd=POLICY_PROJECT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=True
            )
        except subprocess.CalledProcessError as e:
            fail_cnt += 1
            log_file.write(f"Warning: cargo run failed with exit code {e.returncode}\n")

    log_file.write(f"\n# Summary: {len(testcases)} testcases processed, {fail_cnt} failures.\n")
    print('fail testcases:', fail_cnt)
print('All policies processed.')
print(f'Logs written to {log_path}')

