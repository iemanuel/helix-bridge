# Changelog

## 1.0.0 (2026-07-02)

Initial stable release. Helix Bridge is a solar inverter monitoring bridge that reads data from 13+ inverter protocol families and publishes to Home Assistant via MQTT.

### Features

- **Multi-brand inverter support**: Sunsynk/Deye/Sol-Ark, Goodwe, Huawei, Solis, Growatt, Sofar, Luxpower, SMA, Fronius, Voltronic/Axpert/MPP Solar, Victron Energy, and generic SunSpec/Modbus
- **Simulation mode**: Realistic inverter simulator with selectable profiles (sunsynk, goodwe, huawei) for testing without hardware
- **MQTT auto-discovery**: All sensors auto-register in Home Assistant via MQTT discovery with device classes, units, and state classes
- **Pre-built HA dashboard**: Complete Lovelace dashboard covering all 33 metrics across Power, PV Strings, Grid, and Energy views
- **REST API**: HTTP endpoint at `/api/v1/metrics` for live inverter data
- **Home Assistant Add-on**: Runs as an HA container with mode selector, configurable inverter type, MQTT settings, and poll interval
- **Docker Compose**: One-command setup with Mosquitto MQTT broker
- **13 collector drivers**: Each implementing a common metric interface (PV power/voltage/current, grid power, battery SOC/power, load, energy totals, temperatures)
