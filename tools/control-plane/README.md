# OpenSIPS control plane

A dependency-free operational UI and REST gateway for the OpenSIPS Management Interface (MI).

## Features

- browser UI with live Server-Sent Events (SSE)
- generic JSON MI command endpoint
- read-only commands available without a control token
- mutating commands denied by default and protected with a bearer token when enabled
- Prometheus metrics for the control-plane process
- configurable live snapshot methods
- localhost-only default listener

## Start

First expose OpenSIPS MI over HTTP using the normal OpenSIPS `httpd`/`mi_http` configuration, then point the control plane to that URL:

```bash
export OPENSIPS_MI_URL=http://127.0.0.1:8888/mi
export CONTROL_TOKEN='replace-with-a-long-random-value'
python3 tools/control-plane/server.py
```

Open `http://127.0.0.1:8088/`.

Environment variables:

- `OPENSIPS_MI_URL` — JSON-RPC MI endpoint; default `http://127.0.0.1:8888/mi`
- `CONTROL_LISTEN` — listener address; default `127.0.0.1`
- `CONTROL_PORT` — listener port; default `8088`
- `CONTROL_TOKEN` — bearer token required for mutating methods; if unset, mutations are disabled
- `OPENSIPS_SNAPSHOT_METHODS` — comma-separated read methods for the live dashboard
- `CONTROL_SSE_INTERVAL` — live refresh interval in seconds; minimum `0.5`

## API

### `GET /api/health`

Control-plane health and configured MI target.

### `GET /api/snapshot`

Calls each configured snapshot MI method and returns the results as one JSON object. Individual MI errors remain visible in the response instead of taking down the dashboard.

### `GET /api/events`

SSE stream of live snapshots.

### `GET /metrics`

Prometheus text exposition for the gateway itself:

- HTTP request count
- MI request count
- MI error count
- latest MI latency
- active SSE clients

OpenSIPS process/module metrics remain available through the existing OpenSIPS Prometheus module; this endpoint covers the new control-plane layer.

### `POST /api/mi`

Request:

```json
{
  "method": "get_statistics",
  "params": {}
}
```

Methods beginning with `get_`, `list_`, `show_`, `status`, `uptime`, `ps`, or `which` are treated as read-only. Other methods require:

```text
Authorization: Bearer <CONTROL_TOKEN>
```

This is a deliberate deny-by-default policy. If `CONTROL_TOKEN` is not configured, write-like methods cannot be invoked through the gateway.

## Deployment notes

The built-in HTTP server is intended as a small control surface, not an Internet-facing identity layer. Keep the default loopback binding or place it behind the same TLS, SSO/VPN and network policy used for other production operations endpoints.

The UI never stores the bearer token in local storage; it exists only in the current page input.
