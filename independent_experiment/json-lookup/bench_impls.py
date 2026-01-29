#!/usr/bin/env python3
"""Benchmark the custom position-checking guest against the serde version."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PAYLOAD_PATH = DATA_DIR / "payload.json"
FIELDS_PATH = DATA_DIR / "fields.txt"
GUEST_MAIN = ROOT / "methods/guest/src/main.rs"
KEY_TABLE_PATH = ROOT / "methods/guest/src/key_table.rs"
TABLE_PATH = ROOT / "bench_results.md"
DEFAULT_SIZES = [2, 4, 8, 16, 32, 64, 128, 256]

NAMED_DATASETS = {
    "JWT_8": {
        "payload": [
            ("iss", "https://login.example.com/"),
            ("subject_id", "Mock User"),
            ("aud", "api://payments-service"),
            ("exp", "1760485782"),
            ("iat", "1760482182"),
            ("auth_time", "1760482082"),
            ("email", "user@example.com"),
            ("roles", "admin"),
        ],
        "keys": [
            "iss",
            "subject_id",
            "aud",
            "exp",
            "iat",
            "auth_time",
            "email",
            "roles",
        ],
    },
    "JWT_ORI": {
        "payload": [
            ("iss", "https://login.example.com/"),
            ("subject_id", "Julius Hibbert"),
            ("aud", "api://payments-service"),
            ("exp", "1760485782"),
            ("iat", "1760482182"),
            ("auth_time", "1760482082"),
            ("email", "user@example.com"),
            ("email_verified", "true"),
            ("nonce", "3e4f0f67-bc5a-413d-b528-93fd1c71fd4e"),
            ("scope", "openid profile email offline_access"),
            ("roles", "admin"),
        ],
        "keys": [
            "iss",
            "subject_id",
            "aud",
            "exp",
            "iat",
            "auth_time",
            "email",
            "email_verified",
            "nonce",
            "scope",
            "roles",
        ],
    },
    "JWT_MIN": {
        "payload": [
            ("iss", "https://login.example.com/"),
            ("subject_id", "Julius Hibbert"),
            ("aud", "api://payments-service"),
            ("exp", "1760485782"),
            ("iat", "1760482182"),
            ("auth_time", "1760482082"),
            ("email", "user@example.com"),
            ("email_verified", "true"),
            ("nonce", "3e4f0f67-bc5a-413d-b528-93fd1c71fd4e"),
            ("scope", "openid profile email offline_access"),
            ("roles", "admin"),
        ],
        "keys": [
            "subject_id",
            "iss",
        ],
    },
}

VARIANTS = {
    "impl": ROOT / "methods/guest/src/main_old_long.rs",
    "serde": ROOT / "methods/guest/src/main_positions.rs",
}


def write_key_table(keys: list[str]) -> None:
    lines = [
        "pub const KEY_TABLE: &[&str] = &[",
        *[f'    "{key}",' for key in keys],
        "];",
    ]
    KEY_TABLE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dataset(payload_entries: list[tuple[str, str]], keys: list[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    payload = {key: value for key, value in payload_entries}
    PAYLOAD_PATH.write_text(json.dumps(payload), encoding="utf-8")
    FIELDS_PATH.write_text("\n".join(keys) + "\n", encoding="utf-8")
    write_key_table(keys)


def generate_entries_for_size(size: int) -> tuple[list[tuple[str, str]], list[str]]:
    fields = [f"field_{i:03d}" for i in range(1, size + 1)]
    entries = [(name, f"value_{i:03d}") for i, name in enumerate(fields, start=1)]
    return entries, fields


def run_variant(label: str, source_path: Path) -> int:
    print(f"Running {label} variant ...", flush=True)
    shutil.copyfile(source_path, GUEST_MAIN)

    result = subprocess.run(
        ["cargo", "run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout + "\n" + result.stderr
    match = re.search(r"Total cycles:\s+(\d+)", output)
    if not match:
        raise RuntimeError(f"Failed to parse total cycles from output:\n{output}")
    cycles = int(match.group(1))
    print(f"{label} total cycles: {cycles}", flush=True)
    return cycles


def format_table(rows: list[dict[str, int | str]]) -> str:
    headers = ["size"] + list(VARIANTS.keys())
    header_row = "| " + " | ".join(headers) + " |"
    separator_row = "| " + " | ".join("---" for _ in headers) + " |"
    data_rows = []
    for row in rows:
        data_rows.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join([header_row, separator_row, *data_rows])


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark both guest implementations.")
    parser.add_argument(
        "cases",
        nargs="*",
        help="JSON field counts or named datasets (defaults to 2..256 powers of two).",
    )
    args = parser.parse_args()

    tokens = args.cases or [str(size) for size in DEFAULT_SIZES]

    def resolve_case(token: str) -> tuple[str, list[tuple[str, str]], list[str]]:
        name = token.upper()
        if name in NAMED_DATASETS:
            dataset = NAMED_DATASETS[name]
            return name, dataset["payload"], dataset["keys"]
        try:
            size = int(token, 10)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid case '{token}': must be positive integer or one of {list(NAMED_DATASETS)}"
            ) from exc
        if size <= 0:
            raise argparse.ArgumentTypeError("sizes must be positive integers")
        payload_entries, keys = generate_entries_for_size(size)
        return str(size), payload_entries, keys

    original_guest = GUEST_MAIN.read_text(encoding="utf-8")
    original_key_table = KEY_TABLE_PATH.read_text(encoding="utf-8")
    try:
        cases = [resolve_case(token) for token in tokens]
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    all_rows = []
    try:
        for label, payload_entries, keys in cases:
            print(f"\n=== Benchmarking {label} ===")
            write_dataset(payload_entries, keys)
            row = {"size": label}
            for label, source in VARIANTS.items():
                if not source.exists():
                    raise FileNotFoundError(f"Variant source not found: {source}")
                row[label] = run_variant(label, source)
            all_rows.append(row)
    finally:
        GUEST_MAIN.write_text(original_guest, encoding="utf-8")
        KEY_TABLE_PATH.write_text(original_key_table, encoding="utf-8")

    table = format_table(all_rows)
    TABLE_PATH.write_text(table + "\n", encoding="utf-8")
    print("\n=== Summary ===")
    print(table)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stdout or "")
        sys.stderr.write(exc.stderr or "")
        raise
