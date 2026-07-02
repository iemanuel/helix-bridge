# Helix Bridge

Solar inverter monitoring bridge that reads inverter data and publishes to Home Assistant via MQTT.

## Configuration

### Mode

| Option | Description |
|--------|-------------|
| `mode` | `simulation` — test with a simulated inverter. `inverter` — connect to a real inverter. |

### Inverter Type

| Option | Description |
|--------|-------------|
| `type` | Inverter brand/protocol. In `simulation` mode, this selects which inverter to simulate. In `inverter` mode, this selects the real hardware. See supported list below. |

### Connection (mode: `inverter`)

| Option | Description |
|--------|-------------|
| `device` | Serial device path for RS485/USB connections (e.g. `/dev/ttyUSB0`). |
| `modbus_host` | Hostname or IP for TCP-connected inverters (Goodwe, SMA, Fronius, SunSpec). |
| `modbus_port` | Modbus TCP port (default: 502). |
| `modbus_address` | Modbus slave ID (default: 1). |
| `baud_rate` | Serial baud rate (default: 19200). |
| `timeout` | Modbus request timeout in seconds (default: 5). |

### Supported Inverter Types

- `simulation` — Built-in realistic simulator for testing
- `sunsynk` / `deye` / `sol_ark` — Deye/Sunsynk/Sol-Ark hybrid inverters
- `goodwe` — Goodwe ET, EH, BT, BH, GW series
- `huawei` — Huawei SUN2000 series
- `solis` — Solis S6, S5, 4G, 3P, RHI
- `growatt` — Growatt MIN, TLX, SPH, SPA
- `sofar` — Sofar KTL, KTL-X, HVT, ME
- `luxpower` — Luxpower SNA, LXP, Hybrid
- `sma` — SMA Sunny Boy, Tripower, Sunny Island
- `fronius` — Fronius Symo, Primo, Gen24
- `voltronic` / `axpert` / `mppsolar` — Voltronic/Axpert/MPP Solar PIP series
- `victron_vedirect` — Victron SmartSolar, MultiPlus, Quattro
- `generic_modbus` — User-configured Modbus register map
- `sunspec` — Any SunSpec-compliant inverter (auto-detect)

### MQTT

| Option | Description |
|--------|-------------|
| `host` | MQTT broker hostname. Default `core-mosquitto` for the HA built-in broker. |
| `port` | MQTT broker port (default: 1883). |
| `username` | MQTT username (optional). |
| `password` | MQTT password (optional). |
| `topic_prefix` | MQTT topic prefix (default: `helix_bridge`). |
| `ha_discovery` | Enable Home Assistant MQTT auto-discovery (default: true). |

### Other

| Option | Description |
|--------|-------------|
| `poll_interval` | Seconds between inverter polls (default: 5, min: 1, max: 3600). |
| `log_level` | Logging verbosity: `debug`, `info`, `warning`, `error`. |

## Sensors

When MQTT auto-discovery is enabled, all sensors appear automatically in Home Assistant:

- `sensor.helix_bridge_pv_power` — Total PV power (W)
- `sensor.helix_bridge_grid_power` — Grid power (W, positive=import, negative=export)
- `sensor.helix_bridge_battery_power` — Battery power (W)
- `sensor.helix_bridge_load_power` — Load/consumption power (W)
- `sensor.helix_bridge_battery_soc` — Battery state of charge (%)
- Plus voltage, current, frequency, energy totals, temperatures for each PV string

## Dashboard

A pre-built Lovelace dashboard with all supported entities across 4 views (Power, PV Strings, Grid, Energy). Delete entity cards your inverter doesn't have.

To import:
1. Go to **Settings → Dashboards → Raw Configuration Editor**
2. Paste the YAML below
3. Save and reload

```yaml
title: "Helix Bridge"
icon: mdi:solar-power
views:
  - title: Power
    cards:
      - type: grid
        columns: 4
        cards:
          - type: sensor
            entity: sensor.helix_bridge_pv_power
            name: PV Power
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_grid_power
            name: Grid Power
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_battery_power
            name: Battery Power
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_load_power
            name: Load Power
            graph: line
      - type: horizontal-stack
        cards:
          - type: gauge
            entity: sensor.helix_bridge_battery_soc
            name: Battery SOC
            severity:
              green: 50
              yellow: 25
              red: 0
          - type: sensor
            entity: sensor.helix_bridge_battery_voltage
            name: Battery Voltage
          - type: sensor
            entity: sensor.helix_bridge_battery_current
            name: Battery Current
          - type: sensor
            entity: sensor.helix_bridge_battery_temperature
            name: Battery Temp
      - type: entities
        title: Essential / Non-essential
        entities:
          - entity: sensor.helix_bridge_load_power_essential
            name: Essential Load
          - entity: sensor.helix_bridge_load_power_non_essential
            name: Non-Essential Load
          - entity: sensor.helix_bridge_generator_power
            name: Generator Power
          - entity: sensor.helix_bridge_ac_couple_pv_power
            name: AC Couple PV
          - entity: sensor.helix_bridge_auxiliary_pv_power
            name: Auxiliary PV

  - title: PV Strings
    cards:
      - type: entities
        title: Per-MPPT
        entities:
          - entity: sensor.helix_bridge_pv_power_1
            name: PV1 Power
          - entity: sensor.helix_bridge_pv_power_2
            name: PV2 Power
          - entity: sensor.helix_bridge_pv_power_3
            name: PV3 Power
          - entity: sensor.helix_bridge_pv_power_predicted
            name: PV Predicted
      - type: entities
        title: Voltage & Current
        entities:
          - entity: sensor.helix_bridge_pv_voltage
            name: PV Voltage
          - entity: sensor.helix_bridge_pv_voltage_1
            name: PV1 Voltage
          - entity: sensor.helix_bridge_pv_voltage_2
            name: PV2 Voltage
          - entity: sensor.helix_bridge_pv_voltage_3
            name: PV3 Voltage
          - entity: sensor.helix_bridge_pv_current
            name: PV Current
          - entity: sensor.helix_bridge_pv_current_1
            name: PV1 Current
          - entity: sensor.helix_bridge_pv_current_2
            name: PV2 Current
          - entity: sensor.helix_bridge_pv_current_3
            name: PV3 Current

  - title: Grid
    cards:
      - type: grid
        columns: 2
        cards:
          - type: sensor
            entity: sensor.helix_bridge_grid_voltage
            name: Grid Voltage
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_grid_frequency
            name: Grid Frequency
            graph: line
      - type: entities
        entities:
          - entity: sensor.helix_bridge_ac_output_voltage
            name: AC Output Voltage
          - entity: sensor.helix_bridge_inverter_temp
            name: Inverter Temperature

  - title: Energy
    cards:
      - type: grid
        columns: 2
        cards:
          - type: sensor
            entity: sensor.helix_bridge_pv_energy_today
            name: PV Energy Today
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_load_energy_today
            name: Load Energy Today
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_grid_energy_import_today
            name: Grid Import Today
            graph: line
          - type: sensor
            entity: sensor.helix_bridge_grid_energy_export_today
            name: Grid Export Today
            graph: line
```

## REST API

The bridge exposes a REST API on port 8080:

- `GET /api/v1/metrics` — Current inverter metrics in JSON
- `GET /api/v1/status` — Bridge status and configuration

## Troubleshooting

- **No sensors appear**: Verify MQTT connection and ensure `ha_discovery: true`.
- **Serial device not found**: Add the device path under "Devices" in add-on permissions.
- **Connection timeout**: Increase `timeout` and verify network/hardware connections.
- **Wrong values**: Confirm `modbus_address` and inverter type match your hardware.
