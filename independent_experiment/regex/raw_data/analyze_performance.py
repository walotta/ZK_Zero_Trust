#!/usr/bin/env python3
"""
Performance comparison between the Reef baseline and the zkVM implementation.

The script ingests JSON dumps for each dataset/framework pair, computes error
rates plus average proof/verify times (successful cases only), prints summaries,
and produces four PNG visualizations:

  1. proof_time_comparison.png      – dataset + combined bar chart (averages)
  2. verify_time_comparison.png     – dataset + combined bar chart (averages)
  3. <dataset>_proof_time_line.png  – per-case proof seconds (line chart)
  4. <dataset>_verify_time_line.png – per-case verify seconds (line chart)

Line charts place case IDs on the x-axis so cross-case differences between Reef
and zkVM are easy to inspect. Rendering uses Pillow so no external charting
packages are required.

Usage examples (run from the directory containing the JSON files):
    python analyze_performance.py opus4
    python analyze_performance.py opus4 qwen3
    python analyze_performance.py opus4 --output-dir analysis
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


DATASET_CHOICES = ("opus4", "qwen3")
FRAMEWORK_LABELS = ("Reef (baseline)", "zkVM")
FRAMEWORK_FILE_PREFIXES = ("reef", "zkvm")
FRAMEWORK_COLORS = {"Reef (baseline)": "#1f77b4", "zkVM": "#ff7f0e"}


def _load_font(size: int) -> ImageFont.ImageFont:
    font_candidates = (
        "DejaVuSans.ttf",
        "Arial.ttf",
        "LiberationSans-Regular.ttf",
        "FreeSans.ttf",
    )
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except IOError:
            continue
    return ImageFont.load_default()


FONT_SMALL = _load_font(12)
FONT_REG = _load_font(14)
FONT_MED = _load_font(16)
FONT_LARGE = _load_font(20)


def draw_text_center(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, font: ImageFont.ImageFont, fill: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((x - width / 2, y - height / 2), text, fill=fill, font=font)


def draw_text_right(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, font: ImageFont.ImageFont, fill: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((x - width, y - height / 2), text, fill=fill, font=font)


@dataclass
class FrameworkSummary:
    name: str
    total_cases: int
    error_cases: int
    proof_avg: Optional[float]
    verify_avg: Optional[float]

    @property
    def error_rate(self) -> float:
        return self.error_cases / self.total_cases if self.total_cases else math.nan


@dataclass
class DatasetSummary:
    dataset: str
    summaries: Dict[str, FrameworkSummary]


@dataclass
class CaseSeriesEntry:
    case_id: int
    description: str
    reef_proof: Optional[float]
    reef_verify: Optional[float]
    zkvm_proof: Optional[float]
    zkvm_verify: Optional[float]


@dataclass
class DatasetDetail:
    summary: DatasetSummary
    cases: List[CaseSeriesEntry]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Reef and zkVM performance for the specified datasets."
    )
    parser.add_argument(
        "datasets",
        nargs="+",
        choices=DATASET_CHOICES,
        help="Datasets to include in the comparison (processed together).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory to write PNG charts. Defaults to the current working directory.",
    )
    return parser.parse_args()


def load_records(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def entry_has_error(entry: dict) -> bool:
    if "error" in entry:
        err_val = entry["error"]
        if isinstance(err_val, dict):
            if err_val:
                return True
        elif err_val not in (None, "", False):
            return True
    if "regex_matched" in entry:
        expected = not entry.get("negated", False)
        actual = entry.get("regex_matched")
        if actual is None or actual != expected:
            return True
    return False


def average_time(entries: Iterable[dict], key: str) -> Optional[float]:
    values = [entry[key] for entry in entries if isinstance(entry.get(key), (int, float))]
    if not values:
        return None
    return sum(values) / len(values)


def summarize_records(name: str, records: Sequence[dict]) -> FrameworkSummary:
    error_count = sum(1 for entry in records if entry_has_error(entry))
    successes = [entry for entry in records if not entry_has_error(entry)]
    proof_avg = average_time(successes, "proof_seconds")
    verify_avg = average_time(successes, "verify_seconds")
    return FrameworkSummary(
        name=name,
        total_cases=len(records),
        error_cases=error_count,
        proof_avg=proof_avg,
        verify_avg=verify_avg,
    )


def collect_dataset_details(
    base_dir: Path, datasets: Sequence[str]
) -> Tuple[List[DatasetDetail], Dict[str, List[dict]]]:
    combined_records = {framework: [] for framework in FRAMEWORK_LABELS}
    dataset_details: List[DatasetDetail] = []
    for dataset in datasets:
        dataset_summaries: Dict[str, FrameworkSummary] = {}
        loaded_records: Dict[str, List[dict]] = {}
        for label, prefix in zip(FRAMEWORK_LABELS, FRAMEWORK_FILE_PREFIXES):
            path = base_dir / f"{prefix}_{dataset}_performance.json"
            if not path.exists():
                raise FileNotFoundError(f"Missing {path}")
            records = load_records(path)
            combined_records[label].extend(records)
            dataset_summaries[label] = summarize_records(label, records)
            loaded_records[label] = records

        cases = build_case_series(loaded_records[FRAMEWORK_LABELS[0]], loaded_records[FRAMEWORK_LABELS[1]])
        dataset_details.append(DatasetDetail(summary=DatasetSummary(dataset, dataset_summaries), cases=cases))
    return dataset_details, combined_records


def build_case_series(reef_records: Sequence[dict], zkvm_records: Sequence[dict]) -> List[CaseSeriesEntry]:
    if len(reef_records) != len(zkvm_records):
        raise ValueError("The Reef and zkVM record lists must have the same length to align cases.")
    cases: List[CaseSeriesEntry] = []
    for idx, (reef_entry, zkvm_entry) in enumerate(zip(reef_records, zkvm_records), start=1):
        case_id = idx
        description = reef_entry.get("pattern") or reef_entry.get("pattern_original") or f"Case {case_id}"
        if reef_entry.get("pattern") != zkvm_entry.get("pattern"):
            description = f"{description} (pattern mismatch)"
        cases.append(
            CaseSeriesEntry(
                case_id=case_id,
                description=description,
                reef_proof=reef_entry.get("proof_seconds") if not entry_has_error(reef_entry) else None,
                reef_verify=reef_entry.get("verify_seconds") if not entry_has_error(reef_entry) else None,
                zkvm_proof=zkvm_entry.get("proof_seconds") if not entry_has_error(zkvm_entry) else None,
                zkvm_verify=zkvm_entry.get("verify_seconds") if not entry_has_error(zkvm_entry) else None,
            )
        )
    return cases


def render_bar_chart(
    output_path: Path,
    groups: Sequence[Tuple[str, Optional[float], Optional[float]]],
    title: str,
    y_label: str,
) -> None:
    width = 900
    height = 500
    margin_left = 110
    margin_right = 40
    margin_top = 90
    margin_bottom = 90

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    draw_text_center(draw, width / 2, margin_top - 45, title, FONT_LARGE, "#111")

    valid_values = [
        value
        for _, reef_val, zkvm_val in groups
        for value in (reef_val, zkvm_val)
        if value is not None and not math.isnan(value)
    ]
    max_value = max(valid_values) if valid_values else 1.0
    max_value *= 1.05
    if max_value <= 0:
        max_value = 1.0

    group_count = len(groups)
    if group_count == 0:
        return

    group_spacing = chart_width / group_count
    bar_group_width = group_spacing * 0.5
    bar_gap = bar_group_width * 0.12
    single_bar_width = (bar_group_width - bar_gap) / 2

    def value_to_y(val: float) -> float:
        return height - margin_bottom - (val / max_value) * chart_height

    # Axes
    x_axis_y = height - margin_bottom
    draw.line([(margin_left, x_axis_y), (width - margin_right, x_axis_y)], fill="#444444", width=2)
    draw.line([(margin_left, margin_top), (margin_left, x_axis_y)], fill="#444444", width=2)

    tick_count = 5
    for tick in range(tick_count + 1):
        val = (max_value / tick_count) * tick
        y = value_to_y(val)
        draw.line([(margin_left, y), (width - margin_right, y)], fill="#e0e0e0", width=1)
        draw_text_right(draw, margin_left - 12, y, f"{val:.2f}", FONT_SMALL, "#444444")

    for idx, (label, reef_val, zkvm_val) in enumerate(groups):
        group_center = margin_left + group_spacing * (idx + 0.5)
        x_reef = group_center - (bar_gap / 2 + single_bar_width)
        x_zkvm = group_center + bar_gap / 2
        for framework_label, x_pos, val in (
            (FRAMEWORK_LABELS[0], x_reef, reef_val),
            (FRAMEWORK_LABELS[1], x_zkvm, zkvm_val),
        ):
            color = FRAMEWORK_COLORS[framework_label]
            if val is None or math.isnan(val):
                draw.rectangle(
                    [(x_pos, value_to_y(0) - 1), (x_pos + single_bar_width, value_to_y(0) + 1)],
                    fill="#bbbbbb",
                )
                draw_text_center(
                    draw,
                    x_pos + single_bar_width / 2,
                    value_to_y(0) - 14,
                    "N/A",
                    FONT_SMALL,
                    "#666666",
                )
            else:
                top = value_to_y(val)
                bottom = x_axis_y
                draw.rectangle([(x_pos, top), (x_pos + single_bar_width, bottom)], fill=color)
                draw.rectangle([(x_pos, top), (x_pos + single_bar_width, bottom)], outline="#333333", width=1)
                draw_text_center(
                    draw,
                    x_pos + single_bar_width / 2,
                    top - 12,
                    f"{val:.2f}s",
                    FONT_SMALL,
                    "#333333",
                )
        draw_text_center(
            draw,
            group_center,
            x_axis_y + 28,
            label,
            FONT_REG,
            "#222222",
        )

    legend_y = margin_top - 30
    legend_x = margin_left
    for framework in FRAMEWORK_LABELS:
        color = FRAMEWORK_COLORS[framework]
        draw.rectangle([(legend_x, legend_y), (legend_x + 18, legend_y + 18)], fill=color)
        draw.rectangle([(legend_x, legend_y), (legend_x + 18, legend_y + 18)], outline="#333333", width=1)
        draw.text(
            (legend_x + 26, legend_y + 4),
            framework,
            fill="#222222",
            font=FONT_REG,
        )
        legend_x += 200

    draw_text_center(
        draw,
        margin_left - 60,
        margin_top + chart_height / 2,
        y_label,
        FONT_REG,
        "#222222",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")


def render_line_chart(
    output_path: Path,
    dataset_label: str,
    cases: Sequence[CaseSeriesEntry],
    accessor_map: Dict[str, Callable[[CaseSeriesEntry], Optional[float]]],
    title: str,
    y_label: str,
) -> None:
    width = 940
    height = 520
    margin_left = 90
    margin_right = 40
    margin_top = 90
    margin_bottom = 90

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    case_count = len(cases)
    if case_count == 0:
        return

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    draw_text_center(draw, width / 2, margin_top - 45, title, FONT_LARGE, "#111111")

    all_values: List[float] = []
    for accessor in accessor_map.values():
        for case in cases:
            val = accessor(case)
            if val is not None and not math.isnan(val):
                all_values.append(val)
    max_value = max(all_values) if all_values else 1.0
    max_value *= 1.05
    if max_value <= 0:
        max_value = 1.0

    def case_to_x(case_index: int) -> float:
        if case_count == 1:
            return margin_left + chart_width / 2
        return margin_left + ((case_index - 1) / (case_count - 1)) * chart_width

    def value_to_y(val: float) -> float:
        return height - margin_bottom - (val / max_value) * chart_height

    x_axis_y = height - margin_bottom
    draw.line([(margin_left, x_axis_y), (width - margin_right, x_axis_y)], fill="#444444", width=2)
    draw.line([(margin_left, margin_top), (margin_left, x_axis_y)], fill="#444444", width=2)

    y_ticks = 6
    for tick in range(y_ticks + 1):
        val = (max_value / y_ticks) * tick
        y = value_to_y(val)
        draw.line([(margin_left, y), (width - margin_right, y)], fill="#e0e0e0", width=1)
        draw_text_right(draw, margin_left - 12, y, f"{val:.2f}", FONT_SMALL, "#444444")

    if case_count == 1:
        tick_indices = [1]
    else:
        tick_count = min(10, case_count - 1)
        tick_indices = sorted(
            {1 + round((case_count - 1) * (tick / tick_count)) for tick in range(tick_count + 1)}
        )
    for index in tick_indices:
        x = case_to_x(index)
        draw.line([(x, x_axis_y), (x, x_axis_y + 6)], fill="#444444", width=1)
        draw_text_center(draw, x, x_axis_y + 20, str(index), FONT_SMALL, "#444444")

    for label in FRAMEWORK_LABELS:
        accessor = accessor_map[label]
        color = FRAMEWORK_COLORS[label]
        points_to_draw: List[Tuple[float, float]] = []
        for case in cases:
            val = accessor(case)
            if val is None or math.isnan(val):
                if len(points_to_draw) >= 2:
                    draw.line(points_to_draw, fill=color, width=3)
                for px, py in points_to_draw:
                    draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color, outline="#ffffff", width=1)
                points_to_draw = []
                continue
            x = case_to_x(case.case_id)
            y = value_to_y(val)
            points_to_draw.append((x, y))
        if len(points_to_draw) >= 2:
            draw.line(points_to_draw, fill=color, width=3)
        if points_to_draw:
            for px, py in points_to_draw:
                draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color, outline="#ffffff", width=1)

    legend_y = margin_top - 30
    legend_x = margin_left
    for label in FRAMEWORK_LABELS:
        color = FRAMEWORK_COLORS[label]
        draw.line([(legend_x, legend_y), (legend_x + 26, legend_y)], fill=color, width=4)
        draw.text((legend_x + 34, legend_y - 8), label, fill="#222222", font=FONT_REG)
        legend_x += 210

    draw_text_center(
        draw,
        margin_left - 60,
        margin_top + chart_height / 2,
        y_label,
        FONT_REG,
        "#222222",
    )
    draw_text_center(
        draw,
        margin_left + chart_width / 2,
        height - margin_bottom + 45,
        "Case ID",
        FONT_REG,
        "#333333",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")


def print_dataset_report(dataset_summary: DatasetSummary) -> None:
    dataset = dataset_summary.dataset
    print(f"Dataset: {dataset}")
    for label in FRAMEWORK_LABELS:
        summary = dataset_summary.summaries[label]
        err_pct = summary.error_rate * 100 if not math.isnan(summary.error_rate) else float("nan")
        proof = "N/A" if summary.proof_avg is None else f"{summary.proof_avg:.3f}s"
        verify = "N/A" if summary.verify_avg is None else f"{summary.verify_avg:.3f}s"
        print(
            f"  {summary.name}: {summary.error_cases}/{summary.total_cases} errors "
            f"({err_pct:.2f}%), avg proof {proof}, avg verify {verify}"
        )
    print()


def build_groups(
    dataset_details: Sequence[DatasetDetail], metric: str, combined_summary: Dict[str, FrameworkSummary]
) -> List[Tuple[str, Optional[float], Optional[float]]]:
    groups: List[Tuple[str, Optional[float], Optional[float]]] = []
    for detail in dataset_details:
        label = detail.summary.dataset.upper()
        reef_val = getattr(detail.summary.summaries[FRAMEWORK_LABELS[0]], metric)
        zkvm_val = getattr(detail.summary.summaries[FRAMEWORK_LABELS[1]], metric)
        groups.append((label, reef_val, zkvm_val))
    groups.append(
        (
            "Combined",
            getattr(combined_summary[FRAMEWORK_LABELS[0]], metric),
            getattr(combined_summary[FRAMEWORK_LABELS[1]], metric),
        )
    )
    return groups


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    dataset_details, combined_records = collect_dataset_details(base_dir, args.datasets)

    for detail in dataset_details:
        print_dataset_report(detail.summary)

    combined_summary = {
        framework: summarize_records(framework, combined_records[framework])
        for framework in FRAMEWORK_LABELS
    }
    print("Combined view")
    for framework in FRAMEWORK_LABELS:
        summary = combined_summary[framework]
        err_pct = summary.error_rate * 100 if not math.isnan(summary.error_rate) else float("nan")
        proof = "N/A" if summary.proof_avg is None else f"{summary.proof_avg:.3f}s"
        verify = "N/A" if summary.verify_avg is None else f"{summary.verify_avg:.3f}s"
        print(
            f"  {summary.name}: {summary.error_cases}/{summary.total_cases} errors "
            f"({err_pct:.2f}%), avg proof {proof}, avg verify {verify}"
        )
    print()

    proof_groups = build_groups(dataset_details, "proof_avg", combined_summary)
    verify_groups = build_groups(dataset_details, "verify_avg", combined_summary)

    bar_proof_path = args.output_dir / "proof_time_comparison.png"
    bar_verify_path = args.output_dir / "verify_time_comparison.png"

    render_bar_chart(
        bar_proof_path,
        proof_groups,
        title="Proof Time Comparison (Successful Cases)",
        y_label="Average seconds",
    )
    render_bar_chart(
        bar_verify_path,
        verify_groups,
        title="Verify Time Comparison (Successful Cases)",
        y_label="Average seconds",
    )

    for detail in dataset_details:
        dataset = detail.summary.dataset
        accessor_proof = {
            FRAMEWORK_LABELS[0]: lambda case, attr="reef_proof": getattr(case, attr),
            FRAMEWORK_LABELS[1]: lambda case, attr="zkvm_proof": getattr(case, attr),
        }
        accessor_verify = {
            FRAMEWORK_LABELS[0]: lambda case, attr="reef_verify": getattr(case, attr),
            FRAMEWORK_LABELS[1]: lambda case, attr="zkvm_verify": getattr(case, attr),
        }
        proof_line_path = args.output_dir / f"{dataset}_proof_time_line.png"
        verify_line_path = args.output_dir / f"{dataset}_verify_time_line.png"

        render_line_chart(
            proof_line_path,
            dataset_label=dataset.upper(),
            cases=detail.cases,
            accessor_map=accessor_proof,
            title=f"{dataset.upper()} Proof Time per Case",
            y_label="Seconds",
        )
        render_line_chart(
            verify_line_path,
            dataset_label=dataset.upper(),
            cases=detail.cases,
            accessor_map=accessor_verify,
            title=f"{dataset.upper()} Verify Time per Case",
            y_label="Seconds",
        )

    print(f"Saved bar charts to {bar_proof_path} and {bar_verify_path}.")
    for detail in dataset_details:
        dataset = detail.summary.dataset
        proof_path = args.output_dir / f"{dataset}_proof_time_line.png"
        verify_path = args.output_dir / f"{dataset}_verify_time_line.png"
        print(f"Saved line charts to {proof_path} and {verify_path}")


if __name__ == "__main__":
    main()
