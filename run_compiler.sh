#!/bin/bash
set -e

cd ~/ZK_Zero_Trust/tools/xacml-to-rust

# Build compile_regex if not already installed
if ! python3 -c "import compile_regex" 2>/dev/null; then
    echo "Building compile_regex extension..."
    (cd compile_regex && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --features python 2>&1 | tail -2)
    echo ""
fi

echo "=== XACML-to-Rust Compiler ==="
echo ""

USE_RSA=${1:-true}

if [ "$USE_RSA" = "true" ]; then
    OUTPUT_DIR="jwt_zkvm_testing"
    RSA_FLAG="True"
    echo "Generating dataset WITH RSA verification (for E1, E3, E4)..."
else
    OUTPUT_DIR="zkvm_testing_without_rsa"
    RSA_FLAG="False"
    echo "Generating dataset WITHOUT RSA verification (for E2)..."
fi

JWT_SRC="test_jwts"
JWT_BACKUP="/tmp/prezta_jwts_backup"
if [ -d "$JWT_SRC" ]; then
    rm -rf "$JWT_BACKUP"
    cp -r "$JWT_SRC" "$JWT_BACKUP"
elif [ ! -d "$JWT_BACKUP" ]; then
    echo "ERROR: JWT source not found at $JWT_SRC and no backup exists"
    exit 1
fi

rm -rf "$OUTPUT_DIR"

python3 -c "
import sys, os, subprocess, time
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

cp -r "$JWT_BACKUP" "$OUTPUT_DIR/jwts"

echo ""
echo "=== Compilation complete ==="
echo "Output: tools/xacml-to-rust/$OUTPUT_DIR/"
echo ""
echo "Experiments can now be run directly from ~/ZK_Zero_Trust:"
if [ "$USE_RSA" = "true" ]; then
    echo "  python3 batch_exec.py                    # E1"
else
    echo "  sed -i 's|jwt_zkvm_testing|zkvm_testing_without_rsa|' batch_exec.py"
    echo "  rm -rf target/"
    echo "  python3 batch_exec.py                    # E2"
    echo "  git checkout -- batch_exec.py"
fi
