#!/usr/bin/env python3
"""
Extract selected performance metrics from an end-to-end log file and emit CSV.

Successful entries must contain a matching "Permit decision" line (e.g. Permit/Permit).
Failed entries (missing permit line or decision mismatch) are skipped.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

HEADER_PATTERN = r'^#\s*-+\s*(?P<name>.+?)\s*-+\s*$'


def parse_sections(lines: Iterable[str]):
    """Yield (test_name, section_lines) pairs split by header markers."""
    header_re = re.compile(HEADER_PATTERN)
    current_name = None
    current_lines: list[str] = []

    for raw_line in lines:
        stripped = raw_line.strip('\n')
        match = header_re.match(stripped)
        if match:
            if current_name:
                yield current_name, current_lines
            current_name = match.group('name').strip()
            current_lines = []
            continue

        if current_name is not None:
            current_lines.append(stripped)

    if current_name:
        yield current_name, current_lines


def parse_metrics(section_lines: Iterable[str]):
    """Parse metrics from a section, return dict or None if incomplete/failed."""
    total_cycles_e5 = user_cycles_e5 = proof_size_kb = None
    gen_time = verify_time = None
    decision_actual = decision_expected = None

    for line in section_lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('Total cycles:'):
            total_cycles_raw = int(line.split(':', 1)[1].strip())
            total_cycles_e5 = total_cycles_raw / 1e5
        elif line.startswith('User cycles:'):
            user_cycles_raw = int(line.split(':', 1)[1].strip())
            user_cycles_e5 = user_cycles_raw / 1e5
        elif line.startswith('Proof size:'):
            value = line.split(':', 1)[1].strip()
            if value.endswith('bytes'):
                value = value[:-5].strip()
            proof_size_bytes = int(value)
            proof_size_kb = proof_size_bytes / 1024
        elif line.startswith('Gen time elapsed:'):
            value = line.split(':', 1)[1].strip()
            if value.endswith('s'):
                value = value[:-1]
            gen_time = float(value)
        elif line.startswith('Verify time elapsed:'):
            value = line.split(':', 1)[1].strip()
            if value.endswith('ms'):
                value = value[:-2]
            verify_time = float(value)
        elif line.startswith('Permit decision:'):
            value = line.split(':', 1)[1].strip()
            parts = [part.strip() for part in value.split('/', 1)]
            if len(parts) == 2:
                decision_actual, decision_expected = parts

    if not decision_actual or not decision_expected:
        return None

    if decision_actual.lower() != decision_expected.lower():
        return None

    if None in (total_cycles_e5, user_cycles_e5, proof_size_kb, gen_time, verify_time):
        return None

    return {
        'total_cycles_e5': total_cycles_e5,
        'user_cycles_e5': user_cycles_e5,
        'proof_size_kb': proof_size_kb,
        'gen_time_seconds': gen_time,
        'verify_time_ms': verify_time,
    }


CSV_FIELDS = [
    'test_name',
    'total_cycles_e5',
    'user_cycles_e5',
    'proof_size_kb',
    'gen_time_seconds',
    'verify_time_ms',
]

NUMERIC_FIELDS = [field for field in CSV_FIELDS if field != 'test_name']


def extract_rows(log_path: Path):
    """Extract successful rows from the provided log path."""
    rows = []
    skipped = 0
    with log_path.open('r', encoding='utf-8') as handle:
        for test_name, section_lines in parse_sections(handle):
            metrics = parse_metrics(section_lines)
            if metrics is None:
                skipped += 1
                continue
            metrics['test_name'] = test_name
            rows.append(metrics)

    return rows, skipped


def parse_args():
    parser = argparse.ArgumentParser(description='Extract metrics from end-to-end logs.')
    parser.add_argument(
        'log_file',
        nargs='?',
        default=Path(__file__).with_name('end2end.log'),
        type=Path,
        help='Path to the log file (default: data/end2end/end2end.log)',
    )
    parser.add_argument(
        '-o',
        '--output',
        type=Path,
        help='Optional output CSV path (defaults to stdout)',
    )
    return parser.parse_args()


def write_csv(rows, destination):
    writer = csv.DictWriter(destination, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)


def write_numeric_files(rows, directory: Path):
    """Write a per-field file with one value per line."""
    directory.mkdir(parents=True, exist_ok=True)
    for field in NUMERIC_FIELDS:
        filepath = directory / field
        with filepath.open('w', encoding='utf-8') as handle:
            for row in rows:
                handle.write(f"{row[field]}\n")


def _kmeans_1d(points: List[Tuple[str, float]], iterations: int = 25):
    """Cluster points into two groups via 1D k-means."""
    if not points:
        return [(0.0, []), (0.0, [])]

    values = [value for _, value in points]
    min_val, max_val = min(values), max(values)
    if min_val == max_val:
        return [(min_val, points), (max_val, [])]

    centers = [min_val, max_val]
    assignments: dict[int, list[Tuple[str, float]]] = {0: [], 1: []}

    for _ in range(iterations):
        new_assign = {0: [], 1: []}
        for name, value in points:
            idx = 0 if abs(value - centers[0]) <= abs(value - centers[1]) else 1
            new_assign[idx].append((name, value))

        new_centers = []
        for i in (0, 1):
            if new_assign[i]:
                avg = sum(val for _, val in new_assign[i]) / len(new_assign[i])
                new_centers.append(avg)
            else:
                new_centers.append(centers[i])

        if assignments == new_assign:
            centers = new_centers
            break

        assignments = new_assign
        centers = new_centers

    return sorted(
        ((centers[i], assignments.get(i, [])) for i in (0, 1)),
        key=lambda item: item[0],
    )


def write_cluster_file(rows, field: str, directory: Path):
    """Write case-name lists for each cluster of a given metric (sorted ascending)."""
    directory.mkdir(parents=True, exist_ok=True)
    points = [(row['test_name'], row[field]) for row in rows]
    row_lookup = {row['test_name']: row for row in rows}
    clusters = _kmeans_1d(points)
    filepath = directory / f"{field}_groups"

    with filepath.open('w', encoding='utf-8') as handle:
        for idx, (center, cases) in enumerate(clusters, 1):
            handle.write(f"Group {idx} (mean={center:.6f}):\n")
            if cases:
                cases_sorted = sorted(cases, key=lambda item: item[0])
                for name, _ in cases_sorted:
                    metrics = row_lookup.get(name)
                    if not metrics:
                        continue
                    user_cycles = int(round(metrics['user_cycles_e5'] * 1e5))
                    total_cycles = int(round(metrics['total_cycles_e5'] * 1e5))
                    handle.write(f"{name},{user_cycles},{total_cycles}\n")
            handle.write("\n")


def main():
    args = parse_args()
    log_path = args.log_file
    if not log_path.is_file():
        sys.exit(f'Log file not found: {log_path}')

    rows, skipped = extract_rows(log_path)
    if not rows:
        sys.exit('No successful entries found.')

    numeric_dir = args.output.parent if args.output else log_path.parent

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w', newline='', encoding='utf-8') as fh:
            write_csv(rows, fh)
    else:
        write_csv(rows, sys.stdout)

    write_numeric_files(rows, numeric_dir)
    write_cluster_file(rows, 'gen_time_seconds', numeric_dir)
    write_cluster_file(rows, 'proof_size_kb', numeric_dir)

    print(f'Processed {len(rows)} entries, skipped {skipped} sections.', file=sys.stderr)


if __name__ == '__main__':
    main()
