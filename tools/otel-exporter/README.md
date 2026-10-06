# OpenTelemetry metrics exporter

This exporter polls OpenSIPS statistics through the Management Interface and sends them to an OpenTelemetry Collector using OTLP/HTTP JSON.

It runs out-of-process on purpose: a slow or unavailable Collector cannot block SIP workers, and OTLP dependencies do not become OpenSIPS runtime dependencies.

## Run

```bash
export OPENSIPS_MI_URL=http://127.0.0.1:8888/mi
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_SERVICE_NAME=opensips-edge-1
export OTEL_RESOURCE_ATTRIBUTES='deployment.environment=prod,service.namespace=voice'
python3 tools/otel-exporter/exporter.py
```

The default interval is 5 seconds. Set `OTEL_INTERVAL=1` for one-second operational metrics.

Use `--once` for cron/CI or to validate connectivity:

```bash
python3 tools/otel-exporter/exporter.py --once --debug
```

## Selecting statistics

By default the exporter requests `all` from OpenSIPS `get_statistics`.

Limit the payload with the same selectors supported by OpenSIPS MI:

```bash
export OPENSIPS_STATS='core:,tm:,dialog:,media_qoe:,media_security:'
```

Each OpenSIPS stat name is converted into a valid OTEL metric name while the original name is kept as the `opensips.stat` data-point attribute. Statistics are exported as gauges by default because the MI response does not expose the OpenSIPS statistic flags. Use `OTEL_COUNTER_STATS` to explicitly map known monotonic counters; matching metrics are emitted as cumulative monotonic OTLP sums instead of being guessed from their names. For example:

```text
media_qoe:degraded_reports
```

becomes:

```text
opensips_media_qoe_degraded_reports
```

## OTLP settings

- `OTEL_EXPORTER_OTLP_ENDPOINT` — collector base URL or a full `/v1/metrics` URL
- `OTEL_EXPORTER_OTLP_HEADERS` — comma-separated `key=value` HTTP headers for collector authentication
- `OTEL_SERVICE_NAME` — `service.name`, default `opensips`
- `OTEL_RESOURCE_ATTRIBUTES` — comma-separated resource `key=value` pairs
- `OTEL_INTERVAL` — poll/export interval in seconds, minimum 1
- `OTEL_TIMEOUT` — MI and Collector HTTP timeout, minimum 0.5 seconds
- `OTEL_COUNTER_STATS` — optional comma-separated glob patterns for OpenSIPS
  statistics which are cumulative monotonic counters, for example
  `core:*_requests,tm:*_replies,media_qoe:reports`

## Architecture

For production deployments a useful split is:

- OpenSIPS `prometheus` module for direct pull-based metrics;
- this exporter for OTLP pipelines and vendor-neutral Collector processing;
- `tools/control-plane` for live operational status/UI;
- `media_qoe` and `media_security` for new media-specific counters/events.

This keeps Prometheus and OpenTelemetry available at the same time without coupling either backend to SIP request processing.
