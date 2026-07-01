import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS

log = logging.getLogger("bridge.collector.fronius")

FRONIUS_REGISTERS = [
    {"name": "pv_power", "addr": 0x0508, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "pv_energy_today", "addr": 0x050A, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_power_total", "addr": 0x050C, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "signed": True, "count": 2},
    {"name": "grid_voltage_r", "addr": 0x0512, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_voltage_s", "addr": 0x0513, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_voltage_t", "addr": 0x0514, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_frequency", "addr": 0x0518, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "inverter_temp", "addr": 0x0522, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "pv_voltage", "addr": 0x0544, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x05B6, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_energy_export_today", "addr": 0x05B8, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
]

FRONIUS_HYBRID_REGISTERS = [
    {"name": "pv_power", "addr": 0x0508, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "pv_energy_today", "addr": 0x050A, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_power_total", "addr": 0x050C, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "signed": True, "count": 2},
    {"name": "load_power_total", "addr": 0x050E, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_voltage_r", "addr": 0x0512, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_frequency", "addr": 0x0518, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "inverter_temp", "addr": 0x0522, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "pv_voltage", "addr": 0x0544, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "battery_soc", "addr": 0x0554, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "battery_power", "addr": 0x0556, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "signed": True, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x05B6, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_energy_export_today", "addr": 0x05B8, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
]


class FroniusCollector(BaseCollector):
    METRICS = {
        "pv_power", "pv_voltage", "pv_energy_today",
        "grid_power", "grid_voltage", "grid_frequency", "inverter_temp",
        "grid_energy_import_today", "grid_energy_export_today",
        "load_power", "battery_power", "battery_soc",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        model = config.inverter_model or "symo"
        self._regs = FRONIUS_HYBRID_REGISTERS if model in ("gen24", "hybrid") else FRONIUS_REGISTERS
        self._is_hybrid = model in ("gen24", "hybrid")

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        raw = self._client.read_batch(self._regs)
        if not raw:
            return None

        result = {
            "timestamp": ts,
            "pv_power": round(raw.get("pv_power", 0), 1),
            "pv_voltage": round(raw.get("pv_voltage", 0), 1),
            "pv_energy_today": round(raw.get("pv_energy_today", 0), 1),
            "grid_power": round(raw.get("grid_power_total", 0), 1),
            "grid_voltage": round(raw.get("grid_voltage_r", 0), 1),
            "grid_frequency": round(raw.get("grid_frequency", 0), 2),
            "inverter_temp": round(raw.get("inverter_temp", 0), 1),
            "grid_energy_import_today": round(raw.get("grid_energy_import_today", 0), 1),
            "grid_energy_export_today": round(raw.get("grid_energy_export_today", 0), 1),
        }

        if self._is_hybrid:
            result["load_power"] = round(raw.get("load_power_total", 0), 1)
            result["battery_power"] = round(raw.get("battery_power", 0), 1)
            result["battery_soc"] = round(raw.get("battery_soc", 0), 1)

        return result
