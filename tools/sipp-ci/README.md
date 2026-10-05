# SIPp CI reporting

This directory turns a normal SIPp statistics CSV into artifacts which CI systems understand natively.

## Outputs

`sipp_report.py` can emit:

- JSON summary for machines and dashboards
- JUnit XML for test-report UIs
- Markdown summary suitable for `GITHUB_STEP_SUMMARY`
- a non-zero exit code when configured thresholds are violated

## Assertions

Supported thresholds:

- minimum successful calls
- maximum failed calls
- minimum success rate
- maximum response time
- minimum call rate

Example:

```bash
python3 tools/sipp-ci/sipp_report.py stats.csv \
  --json artifacts/summary.json \
  --junit artifacts/junit.xml \
  --markdown artifacts/summary.md \
  --min-success-rate 99.5 \
  --max-failed-calls 0 \
  --max-response-time-ms 150
```

## Running SIPp through the wrapper

`run_sipp_ci.sh` adds `-trace_stat` and `-stf`, executes the reporter afterwards and preserves artifacts even when thresholds fail.

Thresholds are configured through environment variables:

```bash
export SIPP_MIN_SUCCESSFUL_CALLS=1000
export SIPP_MAX_FAILED_CALLS=0
export SIPP_MIN_SUCCESS_RATE=99.9
export SIPP_MAX_RESPONSE_TIME_MS=120
export SIPP_MIN_CALL_RATE=100

bash tools/sipp-ci/run_sipp_ci.sh -sf test/uac.xml 127.0.0.1:5060 -m 1000 -r 100
```

Artifacts are written to `sipp-ci-artifacts/` by default. Override this with `SIPP_CI_OUT_DIR`.

The reporter accepts common SIPp header variants and uses the final statistics row. Missing metrics fail any assertion which depends on them instead of silently passing.
