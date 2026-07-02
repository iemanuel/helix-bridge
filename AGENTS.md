# Helix Bridge — AGENTS.md

## Deployment

- **HA add-on only.** All code in `bridge/`. Runs inside HAOS via `bridge/run.sh` and `bridge/Dockerfile`.
- Config is **auto-generated** at startup by `run.sh` from HA add-on options (`/data/options.json`). The `type` field in add-on options becomes `inverter_model` when `mode: simulation`.
- `bridge/config.yaml` (`version`, `slug`, `changelog`) is the add-on manifest. Bump version there.

## Code layout

- Entrypoint: `bridge/app/main.py` — creates collector + MQTT discovery + REST API + poll loop
- Collectors in `bridge/app/collectors/*.py` — each has a `METRICS` set (str) and `poll() → dict`
- Simulation profiles in `simulation.py`'s `SIM_PROFILES` dict (17 types). When adding a new inverter type, add a profile here if simulation mode should support it.
- Metric definitions in `collectors/base.py`'s `metric_definitions` list (33 metrics). Add new entity types here.
- MQTT discovery in `ha_integration/mqtt_discovery.py`. Entity IDs = `{prefix}_{metric_name}` via `object_id`. Display names from `_friendly_name()` (not `description` field).
- Inverter type → collector mapping in `main.py` `COLLECTOR_MAP`.

## Tests

```sh
pip install -r requirements.txt
python -m pytest tests/  # runs all 77 tests
```

- `tests/conftest.py` adds `bridge/app` to `sys.path` — so collectors import as `from collectors.base import ...`
- `MockConfig` in conftest provides minimal config stubs
- Tests use `unittest.mock` — no integration or hardware tests

## Quirks

- `deye`, `sol_ark` map to `SunsynkCollector`; `axpert`, `mppsolar` map to `VoltronicCollector` — they share the same protocol
- When `mode: simulation`, `inverter_model` is set from the add-on `type` field (e.g., `deye` picks the `deye` simulation profile)
- MQTT discovery publishes with `retain=True`. Stale retained messages in the broker can cause stale HA entities — delete them from HA's MQTT integration UI, then restart the add-on
- Add-on needs `hassio_role: manager` for Supervisor API access; if API returns "forbidden", it falls back to MQTT defaults (connects to `core-mosquitto` without auth)
- All state is published to a single JSON topic (`{prefix}/state`) plus per-metric topics (`{prefix}/{name}`). HA discovery uses the JSON topic with `value_template`.
