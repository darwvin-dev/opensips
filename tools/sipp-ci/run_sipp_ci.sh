#!/usr/bin/env bash
set -uo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <sipp arguments...>" >&2
  exit 2
fi

OUT_DIR="${SIPP_CI_OUT_DIR:-sipp-ci-artifacts}"
STATS_FILE="${SIPP_CI_STATS_FILE:-$OUT_DIR/sipp-stats.csv}"
mkdir -p "$OUT_DIR"

sipp "$@" -trace_stat -stf "$STATS_FILE"
sipp_rc=$?

report_args=(
  "$STATS_FILE"
  --json "$OUT_DIR/summary.json"
  --junit "$OUT_DIR/junit.xml"
  --markdown "$OUT_DIR/summary.md"
)

[[ -n "${SIPP_MIN_SUCCESSFUL_CALLS:-}" ]] && report_args+=(--min-successful-calls "$SIPP_MIN_SUCCESSFUL_CALLS")
[[ -n "${SIPP_MAX_FAILED_CALLS:-}" ]] && report_args+=(--max-failed-calls "$SIPP_MAX_FAILED_CALLS")
[[ -n "${SIPP_MIN_SUCCESS_RATE:-}" ]] && report_args+=(--min-success-rate "$SIPP_MIN_SUCCESS_RATE")
[[ -n "${SIPP_MAX_RESPONSE_TIME_MS:-}" ]] && report_args+=(--max-response-time-ms "$SIPP_MAX_RESPONSE_TIME_MS")
[[ -n "${SIPP_MIN_CALL_RATE:-}" ]] && report_args+=(--min-call-rate "$SIPP_MIN_CALL_RATE")

if [[ -s "$STATS_FILE" ]]; then
  python3 "$(dirname "$0")/sipp_report.py" "${report_args[@]}"
  report_rc=$?
else
  echo "SIPp did not produce statistics at $STATS_FILE" >&2
  report_rc=2
fi

if [[ $sipp_rc -ne 0 ]]; then
  exit "$sipp_rc"
fi
exit "$report_rc"
