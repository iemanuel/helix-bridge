# Changelog

## 1.0.0 (2026-07-02)

Initial release. Helix Bridge is a solar inverter monitoring bridge running as a Home Assistant add-on.

- **17 simulation profiles** covering all supported inverter types (goodwe, huawei, sunsynk, deye, sol_ark, solis, growatt, sofar, luxpower, sma, fronius, voltronic, axpert, mppsolar, victron_vedirect, sunspec, generic_modbus)
- **13 collector drivers** for reading data from Sunsynk/Deye/Sol-Ark, Goodwe, Huawei, Solis, Growatt, Sofar, Luxpower, SMA, Fronius, Voltronic/Axpert/MPP Solar, Victron Energy, and generic SunSpec/Modbus inverters
- **MQTT auto-discovery** with all sensors auto-registering in Home Assistant via MQTT discovery (device classes, units, state classes)
- **Pre-built HA dashboard** in `ha-dashboards/helix_bridge.yaml`
- **REST API** at `/api/v1/metrics`
