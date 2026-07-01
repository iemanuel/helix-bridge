# Helix Bridge

> **Disclaimer:** This project is not production ready. It was built from the idea of bringing together various inverter implementations into a single bridge. Use at your own risk.

A solar inverter monitoring bridge that reads inverter data and publishes it to Home Assistant via MQTT.

## Architecture

```
┌──────────────┐     ┌────────────┐     ┌─────────────────┐
│  Inverter    │────►│  Bridge    │────►│  Home Assistant │
│  (serial/    │USB  │  (Python)  │MQTT │  (MQTT auto-    │
│   modbus)    │     │  :8080     │     │   discovery)    │
└──────────────┘     └────────────┘     └─────────────────┘
```


## Quick Start

```bash
docker compose up -d
```

Then:
- **Bridge API**: http://localhost:8080/api/v1/metrics
- **Home Assistant auto-discovers** all sensors via MQTT

## Supported Inverters

| Brand | Type Key | Models | Protocol | Connection |
|-------|----------|--------|----------|------------|
| Deye / Sunsynk / Sol-Ark | `sunsynk` | Hybrid 3ph/1ph, Sunsynk 8-16kW, Sol-Ark 12-15k | Modbus RTU | Serial (RS485) |
| Solis | `solis` | S6, S5, 4G, 3P, RHI | Modbus RTU | Serial |
| Growatt | `growatt` | MIN, TLX, SPH, SPA | Modbus RTU | Serial |
| Sofar | `sofar` | KTL, KTL-X, HVT, ME | Modbus RTU | Serial |
| Luxpower | `luxpower` | SNA, LXP, Hybrid | Modbus RTU | Serial |
| Huawei | `huawei` | SUN2000 series | Modbus RTU | Serial (RS485) |
| Goodwe | `goodwe` | ET, EH, BT, BH, GW series | Modbus TCP | Network |
| SMA | `sma` | Sunny Boy, Tripower, Sunny Island | SunSpec Modbus | TCP (SunSpec) |
| Fronius | `fronius` | Symo, Primo, Gen24 | Modbus TCP | Network |
| Victron Energy | `victron_vedirect` | SmartSolar, MultiPlus, Quattro | VE.Direct | Serial (USB) |
| Voltronic / Axpert / MPP Solar | `voltronic` | PIP, Axpert MKS/VM, InfiniSolar | QPIGS Serial | Serial (USB) |
| Generic SunSpec | `sunspec` | Any SunSpec-compliant inverter | SunSpec Modbus | TCP (auto-detect) |
| Generic Modbus | `generic_modbus` | User-configured register map | Modbus RTU/TCP | Serial or TCP |
| **TOTAL** | **13 protocol families** | **100+ models covered** | | |

### Configuration

Edit `bridge/config/config.yaml`:

```yaml
inverter:
  type: sunsynk              # Choose from the table above
  device: /dev/ttyUSB0       # Serial device (for RTU/serial protocols)
  model: ""                  # Sub-model for growatt/sofar/fronius
  baud_rate: 19200           # Serial baud rate
  modbus_host: ""            # TCP hostname (for TCP protocols)
  modbus_port: 502           # Modbus TCP port
  modbus_address: 1          # Modbus slave ID
  modbus_timeout: 5
```

### Home Assistant Integration

Sensors auto-discover via MQTT when `mqtt.ha_discovery: true`. All sensors appear automatically in Home Assistant:

- `sensor.helix_bridge_pv_power`
- `sensor.helix_bridge_grid_power`
- `sensor.helix_bridge_battery_power`
- `sensor.helix_bridge_load_power`
- `sensor.helix_bridge_battery_soc`
- Plus voltage, frequency, energy totals, temperature

### Dashboards

A pre-built Lovelace dashboard with all supported entities is in `ha-dashboards/helix_bridge.yaml`. Delete the entity cards your inverter doesn't have. To import:

1. In Home Assistant, go to **Settings → Dashboards → Raw Configuration Editor**
2. Paste the contents of `ha-dashboards/helix_bridge.yaml`
3. Save and reload

## Attributions

Helix Bridge builds on these open-source libraries:

| Library | License | Used for |
|---------|---------|----------|
| [aiohttp](https://github.com/aio-libs/aiohttp) 3.9.5 | Apache 2.0 | REST API server |
| [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) 2.1.0 | EPL 2.0 / EDL 1.0 | MQTT publishing & discovery |
| [pyserial](https://github.com/pyserial/pyserial) 3.5 | BSD 3-Clause | Serial (USB/RS485) communication |
| [pysolarmanv5](https://github.com/jmccrohan/pysolarmanv5) 3.0.6 | MIT | Solarman V5 dongle protocol |
| [PyYAML](https://github.com/yaml/pyyaml) 6.0.2 | MIT | Configuration file parsing |

See each project's repository for full license terms.
