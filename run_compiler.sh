#!/bin/bash
# Step E0: Run the XACML-to-Rust compiler
# This script compiles XACML policies to Rust code for zkVM execution.
# It demonstrates the compiler pipeline described in the paper.

set -e

cd ~/ZK_Zero_Trust/tools/xacml-to-rust

echo "=== XACML-to-Rust Compiler ==="
echo ""

# --- Configuration ---
# Set USE_RSA=true for the RSA dataset (E1), false for no-RSA (E2)
USE_RSA=${1:-true}

if [ "$USE_RSA" = "true" ]; then
    OUTPUT_DIR="jwt_zkvm_testing_gen"
    RSA_FLAG="True"
    echo "Generating dataset WITH RSA verification (for E1, E3, E4)..."
else
    OUTPUT_DIR="zkvm_testing_without_rsa_gen"
    RSA_FLAG="False"
    echo "Generating dataset WITHOUT RSA verification (for E2)..."
fi

# Run compiler
rm -rf "$OUTPUT_DIR"

python3 -c "
import sys, os, subprocess, time
from collections import defaultdict
from datetime import datetime

USE_RSA_VERIFY = $RSA_FLAG
OUTPUT_FOLDER_NAME = '$OUTPUT_DIR'
base_dir = 'policy_test_set'
main_path = 'main.py'
os.makedirs('logs', exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'logs/compiler_{timestamp}.txt'

total = successes = failures = skips = 0

for folder in sorted(os.listdir(base_dir)):
    if folder.startswith('III'):
        continue
    folder_path = os.path.join(base_dir, folder)
    if not os.path.isdir(folder_path):
        skips += 1; continue
    policy_file = os.path.join(folder_path, f'Policy_{folder}.xml')
    request_file = os.path.join(folder_path, f'Request_{folder}.xml')
    response_file = os.path.join(folder_path, f'Response_{folder}.xml')
    if not all(os.path.exists(f) for f in [policy_file, request_file, response_file]):
        skips += 1; continue
    total += 1
    try:
        cmd = [sys.executable, main_path, policy_file, '-r', request_file, '-s', response_file, '-o', OUTPUT_FOLDER_NAME, '-j']
        if USE_RSA_VERIFY:
            cmd.append('-R')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            successes += 1
        else:
            failures += 1
    except:
        failures += 1

print(f'Total: {total}, Successful: {successes}, Failed: {failures}, Skipped: {skips}')
with open(log_file, 'w') as f:
    f.write(f'Total: {total}, Successful: {successes}, Failed: {failures}, Skipped: {skips}\n')
"

# Copy pre-generated JWT tokens (signed test data independent of compilation)
if [ "$USE_RSA" = "true" ]; then
    cp -r jwt_zkvm_testing/jwts "$OUTPUT_DIR/jwts"
    echo ""
    echo "JWT test tokens copied from repository (pre-signed, independent of compilation)."
fi

echo ""
echo "=== Compilation complete ==="
echo "Output directory: ~/ZK_Zero_Trust/tools/xacml-to-rust/$OUTPUT_DIR/"
echo ""
echo "To use this generated dataset for experiments, from ~/ZK_Zero_Trust run:"
if [ "$USE_RSA" = "true" ]; then
    echo "  sed -i 's|jwt_zkvm_testing\b|jwt_zkvm_testing_gen|' batch_exec.py"
else
    echo "  sed -i 's|jwt_zkvm_testing|zkvm_testing_without_rsa_gen|' batch_exec.py"
fi
echo "  python3 batch_exec.py"
echo "  git checkout -- batch_exec.py  # revert after"
