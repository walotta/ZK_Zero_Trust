#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

from compile_regex import create_dfa_bytes

# Regex evaluation cases are sourced from an external JSON file at runtime.
ROOT = Path(__file__).resolve().parent
REGEX_BIN_PATH = ROOT / "methods" / "guest" / "src" / "regex.bin"
REGEX_STR_PATH = ROOT / "methods" / "guest" / "src" / "regex.txt"
DEFAULT_JSON_OUTPUT_PATH = ROOT / "regex_metrics.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile regex patterns into the guest binary, run them inside the host, "
            "and collect execution metrics."
        )
    )
    parser.add_argument(
        "--cases",
        required=True,
        help="Path to a JSON file containing [{\"pattern\": ..., \"str\": ...}, ...]",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Destination JSON file for collected metrics. Defaults to regex_metrics.json next "
            "to this script."
        ),
    )
    return parser.parse_args()


def resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def load_cases(cases_path: Path) -> list[dict[str, str]]:
    try:
        raw = json.loads(cases_path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"Cases file not found: {cases_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON in {cases_path}: {exc}") from exc

    if not isinstance(raw, list):
        raise ValueError("Cases JSON must be a list of objects")

    cases: list[dict[str, str]] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Case #{idx} is not an object: {entry!r}")
        try:
            pattern = entry["pattern"]
            eval_str = entry["str"]
        except KeyError as exc:
            raise ValueError(f"Case #{idx} missing required key: {exc.args[0]}") from exc

        cases.append({"pattern": str(pattern), "str": str(eval_str)})

    return cases


def _extract_with_prefix(
    output: str,
    prefixes: Iterable[str],
    parser: Callable[[str], Optional[float]],
) -> Optional[float]:
    for line in output.splitlines():
        stripped = line.strip()
        for prefix in prefixes:
            if stripped.startswith(prefix):
                remainder = stripped[len(prefix) :].strip()
                parsed = parser(remainder)
                if parsed is not None:
                    return parsed
    return None


def _parse_duration(token: str) -> Optional[float]:
    match = re.match(r"(?P<value>[\d.]+)\s*(?P<unit>ns|µs|us|ms|s)?", token)
    if not match:
        return None
    value = float(match.group("value"))
    unit = match.group("unit") or "s"
    if unit == "s":
        return value
    if unit == "ms":
        return value / 1_000
    if unit in {"us", "µs"}:
        return value / 1_000_000
    if unit == "ns":
        return value / 1_000_000_000
    return None


def _parse_int(token: str) -> Optional[int]:
    cleaned = token.replace(",", "").replace("_", "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _append_error(entry: dict[str, object], message: str) -> None:
    existing = entry.get("error")
    if existing:
        entry["error"] = f"{existing}; {message}"
    else:
        entry["error"] = message


def load_existing_metrics(path: Path) -> tuple[list[dict[str, object]], dict[tuple[str, str], int]]:
    if not path.exists():
        return [], {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"Warning: failed to parse existing metrics at {path}: {exc}", file=sys.stderr)
        return [], {}

    if not isinstance(raw, list):
        print(f"Warning: existing metrics at {path} are not a list – ignoring file", file=sys.stderr)
        return [], {}

    entries: list[dict[str, object]] = []
    index_map: dict[tuple[str, str], int] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        pattern = str(entry.get("pattern"))
        eval_str = str(entry.get("str"))
        index_map[(pattern, eval_str)] = len(entries)
        entries.append(entry)

    return entries, index_map


def write_metrics(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2))


def extract_metrics(output: str, wall_seconds: float) -> dict[str, Optional[float | int]]:
    proof_seconds = _extract_with_prefix(
        output,
        prefixes=("Gen time elapsed:", "Proof time elapsed:", "Prove time elapsed:"),
        parser=_parse_duration,
    )

    verify_seconds = _extract_with_prefix(
        output,
        prefixes=(
            "Verify time elapsed:",
            "Verification time elapsed:",
            "Verify elapsed:",
        ),
        parser=_parse_duration,
    )

    total_cycles = _extract_with_prefix(
        output,
        prefixes=("Total cycles:",),
        parser=_parse_int,
    )

    user_cycles = _extract_with_prefix(
        output,
        prefixes=("User cycles:",),
        parser=_parse_int,
    )

    return {
        "proof_seconds": proof_seconds,
        "verify_seconds": verify_seconds,
        "total_cycles": total_cycles,
        "user_cycles": user_cycles,
    }


def compile_pattern(pattern: str) -> bytes:
    return create_dfa_bytes(pattern)


def write_regex_bytes(buf: bytes, pattern: str) -> None:
    # tmp_path = ROOT / "regex.bin.tmp"
    # with tmp_path.open("wb") as f:
    #     f.write(buf)
    # os.system(f"rm -f '{REGEX_BIN_PATH}'")
    # os.system(f"mv '{tmp_path}' '{REGEX_BIN_PATH}'")
    tmp_path = ROOT / "regex.txt.tmp"
    with tmp_path.open("w") as f:
        f.write(pattern)
    os.system(f"rm -f '{REGEX_STR_PATH}'")
    os.system(f"mv '{tmp_path}' '{REGEX_STR_PATH}'")



def run_host(eval_str: str) -> subprocess.CompletedProcess[str]:
    cmd = ["cargo", "run", "--release", "--", eval_str]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def main() -> int:
    args = parse_args()
    cases_path = resolve_path(args.cases)
    output_path = (
        resolve_path(args.output)
        if args.output is not None
        else DEFAULT_JSON_OUTPUT_PATH
    )

    try:
        cases = load_cases(cases_path)
    except ValueError as exc:
        print(f"Error loading cases: {exc}", file=sys.stderr)
        error_entry = {
            "pattern": None,
            "str": None,
            "proof_seconds": None,
            "verify_seconds": None,
            "total_cycles": None,
            "user_cycles": None,
            "error": f"load cases failed: {exc}",
            "python_match": None,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps([error_entry], indent=2))
        print(f"Metrics written to {output_path}")
        return 1

    metrics_output, existing_map = load_existing_metrics(output_path)
    updated = False
    total_cases = len(cases)
    for idx, case in enumerate(cases, start=1):
        pattern = case["pattern"]
        eval_str = case["str"]
        case_label = f"[{idx}/{total_cases}]"
        key = (pattern, eval_str)

        if key in existing_map:
            print(f"{case_label} pattern={pattern!r} eval={eval_str!r} (skipped; already recorded)", flush=True)
            continue

        print(f"{case_label} pattern={pattern!r} eval={eval_str!r}", flush=True)

        entry = {
            "pattern": pattern,
            "str": eval_str,
            "proof_seconds": None,
            "verify_seconds": None,
            "total_cycles": None,
            "user_cycles": None,
            "error": None,
            "python_match": None,
        }

        def persist_entry() -> None:
            nonlocal updated
            metrics_output.append(entry)
            existing_map[key] = len(metrics_output) - 1
            write_metrics(output_path, metrics_output)
            print(f"  {case_label} metrics saved to {output_path}")
            updated = True

        try:
            entry["python_match"] = bool(re.search(pattern, eval_str))
        except re.error as exc:
            message = f"python re failed: {exc}"
            print(f"  {case_label} {message}", file=sys.stderr)
            _append_error(entry, message)
            persist_entry()
            continue

        try:
            # if idx == 97:
            #     raise TimeoutError("timeout when compile pattern")
            # compiled_bytes = compile_pattern(pattern)
            write_regex_bytes(None, pattern)
        except Exception as exc:
            message = f"compile/write failed: {exc}"
            print(f"  {case_label} {message}", file=sys.stderr)
            _append_error(entry, message)
            persist_entry()
            continue

        run_start = time.perf_counter()
        try:
            result = run_host(eval_str)
        except Exception as exc:
            message = f"host execution exception: {exc}"
            print(f"  {case_label} {message}", file=sys.stderr)
            _append_error(entry, message)
            persist_entry()
            continue

        wall_seconds = time.perf_counter() - run_start

        if result.returncode != 0:
            stderr_out = result.stderr.strip()
            message = f"host exit {result.returncode}: {stderr_out or '(no stderr)'}"
            print(f"  {case_label} host execution failed", file=sys.stderr)
            if stderr_out:
                print(stderr_out, file=sys.stderr)
            _append_error(entry, message)
            persist_entry()
            continue

        stdout_text = result.stdout.strip()
        if stdout_text:
            print(stdout_text)
        print()

        try:
            entry.update(extract_metrics(result.stdout, wall_seconds))
        except Exception as exc:
            message = f"metric parse failed: {exc}"
            print(f"  {case_label} {message}", file=sys.stderr)
            _append_error(entry, message)

        persist_entry()

    if updated:
        print(f"Metrics written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
