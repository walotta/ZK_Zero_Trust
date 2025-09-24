#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

POLICY_PROJECT = Path.cwd()
OUTPUT_BASE = POLICY_PROJECT / "output"
INPUT_DEF_DIR = OUTPUT_BASE / "input_definition"
POLICY_CODE_DIR = OUTPUT_BASE / "policies_code"
REQUESTS_DIR = OUTPUT_BASE / "requests"
RESPONSES_DIR = OUTPUT_BASE / "responses"
POLICY_TEST_SET = POLICY_PROJECT / "tools" / "xacml-to-rust" / "policy_test_set"
XACML_TO_RUST_MAIN = POLICY_PROJECT / "tools" / "xacml-to-rust" / "main.py"
TARGET_LIB = POLICY_PROJECT / "core" / "src" / "lib.rs"
TARGET_MAIN = POLICY_PROJECT / "methods" / "guest" / "src" / "main.rs"
GUEST_DIR = POLICY_PROJECT / "methods" / "guest" / "src"
LOGS_DIR = POLICY_PROJECT / "logs"


def find_file_with_pattern(policy_dir: Path, exact_name: str, pattern: str) -> Path:
    """Find a file with exact name or pattern, preferring exact name."""
    exact_file = policy_dir / exact_name
    if exact_file.exists():
        return exact_file

    pattern_files = list(policy_dir.glob(pattern))
    if len(pattern_files) == 1:
        return pattern_files[0]
    elif len(pattern_files) > 1:
        raise FileNotFoundError(f"Multiple {pattern} files found in {policy_dir}: {[f.name for f in pattern_files]}. Use exact name {exact_name} or ensure only one {pattern} file exists.")
    else:
        raise FileNotFoundError(f"No {exact_name} or {pattern} file found in {policy_dir}")


def validate_policy_directory(policy_dir: Path) -> tuple[str, Path, Path, Path]:
    """Validate policy directory and return the testcase name and file paths."""
    if not policy_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

    if not policy_dir.is_dir():
        raise ValueError(f"Path is not a directory: {policy_dir}")

    # Extract testcase name from directory name
    testcase_name = policy_dir.name

    # Find required files (exact name preferred, then pattern)
    try:
        policy_file = find_file_with_pattern(policy_dir, "Policy.xml", "Policy_*.xml")
        request_file = find_file_with_pattern(policy_dir, "Request.xml", "Request_*.xml")
        response_file = find_file_with_pattern(policy_dir, "Response.xml", "Response_*.xml")
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))

    return testcase_name, policy_file, request_file, response_file


def get_compiled_artifacts(testcase_name: str) -> dict:
    """Get paths to compiled artifacts for a testcase."""
    return {
        "input_definition": INPUT_DEF_DIR / f"Policy_{testcase_name}.rs",
        "policy_code": POLICY_CODE_DIR / f"Policy_{testcase_name}.rs",
        "request": REQUESTS_DIR / f"Policy_{testcase_name}.json",
        "response": RESPONSES_DIR / f"Policy_{testcase_name}.json",
    }


def ensure_directories() -> None:
    TARGET_LIB.parent.mkdir(parents=True, exist_ok=True)
    TARGET_MAIN.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    INPUT_DEF_DIR.mkdir(parents=True, exist_ok=True)
    POLICY_CODE_DIR.mkdir(parents=True, exist_ok=True)
    # Output directories will be created by the compiler


def compile_policy(policy_file: Path, request_file: Path, response_file: Path, log_file) -> bool:
    """Compile the specific policy for the given files."""

    # Compile command - use relative path since we're running from xacml-to-rust dir
    cmd = [
        "python3", "main.py",
        str(policy_file),
        "-r", str(request_file),
        "-s", str(response_file),
        "-o", str(OUTPUT_BASE)
    ]

    print(f"Compiling policy: {' '.join(cmd)}")
    # Run from xacml-to-rust directory so it can find templates
    xacml_dir = POLICY_PROJECT / "tools" / "xacml-to-rust"
    result = subprocess.run(cmd, cwd=str(xacml_dir), capture_output=True, text=True)

    # Log the compilation output
    log_file.write(f"\n=== COMPILATION OUTPUT ===\n")
    log_file.write(f"Command: {' '.join(cmd)}\n")
    log_file.write(f"Return code: {result.returncode}\n")
    log_file.write(f"STDOUT:\n{result.stdout}\n")
    log_file.write(f"STDERR:\n{result.stderr}\n")
    log_file.write(f"=== END COMPILATION OUTPUT ===\n\n")
    log_file.flush()

    if result.returncode != 0:
        print(f"Compilation failed with return code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        return False

    print("Compilation successful")
    return True


def copy_guest_bins() -> None:
    """Mirror any compiled guest binaries into the guest directory."""
    for bin_file in POLICY_CODE_DIR.glob("*.bin"):
        os.system(f"cp '{bin_file}' '{GUEST_DIR / bin_file.name}'")


def stream_process(cmd: list[str], cwd: Path, log_file) -> int:
    """Run command, streaming combined output to stdout and log."""
    process = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None  # for type checkers
    try:
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
            log_file.flush()
    except KeyboardInterrupt:
        process.terminate()
        raise
    return process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single policy testcase.")
    parser.add_argument("policy_dir", help="Path to the directory containing policy files (Policy_*.xml, Request_*.xml, Response_*.xml)")
    parser.add_argument("--clean", action="store_true", help="Clean and rebuild before running")
    args = parser.parse_args()

    ensure_directories()

    # Validate policy directory and get file paths
    try:
        policy_dir = Path(args.policy_dir).resolve()
        testcase_name, policy_file, request_file, response_file = validate_policy_directory(policy_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return 1
    log_filename = datetime.now().strftime("one_shot_%m_%d_%H_%M.log")
    log_path = LOGS_DIR / log_filename
    print(f"All cargo output will be mirrored to {log_path}")

    with log_path.open("w", encoding="utf-8") as log_file:
        def emit(message: str) -> None:
            print(message)
            log_file.write(message + "\n")
            log_file.flush()

        emit(f"# ---------- {testcase_name} ----------")
        emit(f"Policy directory: {policy_dir}")
        emit("Compiling policy...")

        # Compile the policy
        if not compile_policy(policy_file, request_file, response_file, log_file):
            emit("Policy compilation failed.")
            return 1

        emit("Policy compiled successfully.")
        emit("Preparing artefacts...")

        # Get compiled artifacts
        artefacts = get_compiled_artifacts(testcase_name)
        copy_guest_bins()

        os.system(f"cp '{artefacts['input_definition']}' '{TARGET_LIB}'")
        os.system(f"cp '{artefacts['policy_code']}' '{TARGET_MAIN}'")
        emit("Copied input definition and policy code.")

        if args.clean:
            emit("Cleaning previous build...")
            clean_cmd = ["cargo", "clean"]
            clean_returncode = stream_process(clean_cmd, POLICY_PROJECT, log_file)
            if clean_returncode != 0:
                emit(f"Clean failed with status {clean_returncode}.")
                return clean_returncode

        cmd = [
            "cargo",
            "run",
            "--release",
            "--",
            str(artefacts["request"]),
            str(artefacts["response"]),
        ]
        emit(f"Running: {' '.join(cmd)}")

        returncode = stream_process(cmd, POLICY_PROJECT, log_file)
        emit(f"Command exited with status {returncode}.")

    if returncode != 0:
        return returncode

    print("One-shot execution completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
