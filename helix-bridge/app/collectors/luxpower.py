import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS, MODBUS_READ_INPUT_REGISTERS

log = logging.getLogger("bridge.collector.luxpower")


class LuxpowerCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "battery_power", "load_power",
        "battery_soc", "battery_voltage",
        "grid_voltage", "grid_frequency", "pv_voltage", "inverter_temp",
        "pv_energy_today", "load_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)

    def _registers(self):
        return [
            {"name": "pv1_power", "addr": 0x30, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "count": 1},
            {"name": "pv2_power", "addr": 0x31, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "count": 1},
            {"name": "pv1_voltage", "addr": 0x32, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv2_voltage", "addr": 0x33, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_voltage_r", "addr": 0x34, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_voltage_s", "addr": 0x35, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_voltage_t", "addr": 0x36, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_frequency", "addr": 0x38, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.01, "count": 1},
            {"name": "grid_power_total", "addr": 0x3E, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 1},
            {"name": "load_power_total", "addr": 0x3F, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "count": 1},
            {"name": "battery_voltage", "addr": 0x40, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.01, "count": 1},
            {"name": "battery_soc", "addr": 0x41, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "count": 1},
            {"name": "battery_power", "addr": 0x42, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 1},
            {"name": "battery_current", "addr": 0x43, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "signed": True, "count": 1},
            {"name": "inverter_temp", "addr": 0x44, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv_energy_today", "addr": 0x50, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
            {"name": "grid_energy_import_today", "addr": 0x52, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
            {"name": "grid_energy_export_today", "addr": 0x54, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
            {"name": "load_energy_today", "addr": 0x56, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
        ]

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        raw = self._client.read_batch(self._registers())
        if not raw:
            return None

        pv1 = raw.get("pv1_power", 0)
        pv2 = raw.get("pv2_power", 0)

        return {
            "timestamp": ts,
            "pv_power": round(pv1 + pv2, 1),
            "grid_power": round(raw.get("grid_power_total", 0), 1),
            "battery_power": round(raw.get("battery_power", 0), 1),
            "load_power": round(raw.get("load_power_total", 0), 1),
            "battery_soc": round(raw.get("battery_soc", 0), 1),
            "battery_voltage": round(raw.get("battery_voltage", 0), 2),
            "grid_voltage": round(raw.get("grid_voltage_r", 0), 1),
            "grid_frequency": round(raw.get("grid_frequency", 0), 2),
            "pv_voltage": round(max(raw.get("pv1_voltage", 0), raw.get("pv2_voltage", 0)), 1),
            "inverter_temp": round(raw.get("inverter_temp", 0), 1),
            "pv_energy_today": round(raw.get("pv_energy_today", 0), 1),
            "load_energy_today": round(raw.get("load_energy_today", 0), 1),
            "grid_energy_import_today": round(raw.get("grid_energy_import_today", 0), 1),
            "grid_energy_export_today": round(raw.get("grid_energy_export_today", 0), 1),
        }
