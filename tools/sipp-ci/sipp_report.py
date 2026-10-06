#!/usr/bin/env python3
"""Turn SIPp statistics into CI-native reports and threshold assertions."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ALIASES = {
    "successful_calls": ("SuccessfulCall(C)", "SuccessfulCall", "SuccessfulCalls", "Successful calls"),
    "failed_calls": ("FailedCall(C)", "FailedCall", "FailedCalls", "Failed calls"),
    "response_time_ms": ("ResponseTime1(C)", "ResponseTime(C)", "ResponseTime1", "ResponseTime(ms)", "Response time"),
    "call_rate": ("CallRate(C)", "CallRate", "CallRate(P)", "Call rate"),
}


def _number(value: str) -> Optional[float]:
    value = (value or "").strip().replace("%", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _duration_ms(value: str) -> Optional[float]:
    raw = (value or "").strip()
    if not raw:
        return None
    parts = raw.split(":")
    if len(parts) in (3, 4):
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            micros = int(parts[3].ljust(6, "0")) if len(parts) == 4 else 0
        except ValueError:
            return None
        if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60:
            return None
        return (hours * 3600 + minutes * 60 + seconds) * 1000.0 + micros / 1000.0
    return _number(raw)


def _pick_response_time_ms(row: Dict[str, str], names: Iterable[str]) -> Optional[float]:
    lowered = {k.strip().lower(): v for k, v in row.items() if k}
    for name in names:
        raw = row.get(name)
        if raw is None:
            raw = lowered.get(name.lower())
        if raw is None:
            continue
        value = _duration_ms(raw)
        if value is not None:
            return value
    return None


def _pick(row: Dict[str, str], names: Iterable[str]) -> Optional[float]:
    for name in names:
        if name in row:
            value = _number(row[name])
            if value is not None:
                return value
    lowered = {k.strip().lower(): v for k, v in row.items() if k}
    for name in names:
        value = _number(lowered.get(name.lower(), ""))
        if value is not None:
            return value
    return None


def load_final_row(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ValueError("statistics file is empty")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    rows = [row for row in csv.DictReader(text.splitlines(), dialect=dialect) if any((v or "").strip() for v in row.values())]
    if not rows:
        raise ValueError("statistics file has no data rows")
    return rows[-1]


def summarize(row: Dict[str, str]) -> Dict[str, Optional[float]]:
    out = {
        name: (
            _pick_response_time_ms(row, aliases)
            if name == "response_time_ms"
            else _pick(row, aliases)
        )
        for name, aliases in ALIASES.items()
    }
    ok = out["successful_calls"]
    failed = out["failed_calls"]
    if ok is not None and failed is not None and ok + failed > 0:
        out["success_rate"] = ok * 100.0 / (ok + failed)
    else:
        out["success_rate"] = None
    return out


def evaluate(summary: Dict[str, Optional[float]], args: argparse.Namespace) -> List[Tuple[str, bool, str]]:
    checks: List[Tuple[str, bool, str]] = []

    def add(name: str, actual: Optional[float], expected: str, passed: bool) -> None:
        shown = "missing" if actual is None else f"{actual:.3f}".rstrip("0").rstrip(".")
        checks.append((name, passed, f"actual={shown}; expected {expected}"))

    if args.min_successful_calls is not None:
        value = summary["successful_calls"]
        add("minimum successful calls", value, f">= {args.min_successful_calls}", value is not None and value >= args.min_successful_calls)
    if args.max_failed_calls is not None:
        value = summary["failed_calls"]
        add("maximum failed calls", value, f"<= {args.max_failed_calls}", value is not None and value <= args.max_failed_calls)
    if args.min_success_rate is not None:
        value = summary["success_rate"]
        add("minimum success rate", value, f">= {args.min_success_rate}%", value is not None and value >= args.min_success_rate)
    if args.max_response_time_ms is not None:
        value = summary["response_time_ms"]
        add("maximum response time", value, f"<= {args.max_response_time_ms} ms", value is not None and value <= args.max_response_time_ms)
    if args.min_call_rate is not None:
        value = summary["call_rate"]
        add("minimum call rate", value, f">= {args.min_call_rate}", value is not None and value >= args.min_call_rate)

    return checks


def write_junit(path: Path, checks: List[Tuple[str, bool, str]], source: str) -> None:
    failed = sum(1 for _, passed, _ in checks if not passed)
    suite = ET.Element("testsuite", name="sipp-thresholds", tests=str(len(checks)), failures=str(failed))
    suite.set("source", source)
    for name, passed, message in checks:
        case = ET.SubElement(suite, "testcase", classname="sipp.threshold", name=name)
        if not passed:
            failure = ET.SubElement(case, "failure", message=message)
            failure.text = message
        else:
            ET.SubElement(case, "system-out").text = message
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def render_markdown(summary: Dict[str, Optional[float]], checks: List[Tuple[str, bool, str]]) -> str:
    lines = ["## SIPp CI report", "", "| Metric | Value |", "|---|---:|"]
    for key in ("successful_calls", "failed_calls", "success_rate", "call_rate", "response_time_ms"):
        value = summary.get(key)
        if value is None:
            shown = "n/a"
        elif key == "success_rate":
            shown = f"{value:.2f}%"
        else:
            shown = f"{value:.3f}".rstrip("0").rstrip(".")
        lines.append(f"| {key.replace('_', ' ')} | {shown} |")
    if checks:
        lines += ["", "### Thresholds", "", "| Check | Result | Details |", "|---|---|---|"]
        for name, passed, message in checks:
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {message} |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stats", type=Path, help="SIPp -trace_stat/-stf CSV file")
    p.add_argument("--json", dest="json_path", type=Path)
    p.add_argument("--junit", type=Path)
    p.add_argument("--markdown", type=Path)
    p.add_argument("--min-successful-calls", type=float)
    p.add_argument("--max-failed-calls", type=float)
    p.add_argument("--min-success-rate", type=float)
    p.add_argument("--max-response-time-ms", type=float)
    p.add_argument("--min-call-rate", type=float)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        row = load_final_row(args.stats)
        summary = summarize(row)
        checks = evaluate(summary, args)
    except (OSError, ValueError) as exc:
        print(f"sipp_report: {exc}", file=sys.stderr)
        return 2

    payload = {
        "source": str(args.stats),
        "summary": summary,
        "checks": [{"name": n, "passed": p, "message": m} for n, p, m in checks],
        "passed": all(p for _, p, _ in checks),
    }
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.junit:
        write_junit(args.junit, checks, str(args.stats))

    markdown = render_markdown(summary, checks)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(markdown)
    print(markdown, end="")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
