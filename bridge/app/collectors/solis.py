import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS, MODBUS_READ_INPUT_REGISTERS

log = logging.getLogger("bridge.collector.solis")


class SolisCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "grid_frequency", "grid_voltage",
        "pv_voltage", "inverter_temp",
        "pv_energy_today", "grid_energy_import_today", "grid_energy_export_today",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)

    def _registers(self):
        return [
            {"name": "pv1_voltage", "addr": 0x00, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv1_current", "addr": 0x01, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv2_voltage", "addr": 0x02, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv2_current", "addr": 0x03, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv1_power", "addr": 0x04, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
            {"name": "pv2_power", "addr": 0x05, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
            {"name": "grid_voltage_r", "addr": 0x08, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_voltage_s", "addr": 0x09, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_voltage_t", "addr": 0x0A, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "grid_current_r", "addr": 0x0B, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "signed": True, "count": 1},
            {"name": "grid_current_s", "addr": 0x0C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "signed": True, "count": 1},
            {"name": "grid_current_t", "addr": 0x0D, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "signed": True, "count": 1},
            {"name": "grid_frequency", "addr": 0x0E, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
            {"name": "grid_power_total", "addr": 0x10, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
            {"name": "inverter_temp", "addr": 0x1F, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
            {"name": "pv_energy_today", "addr": 0x29, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
            {"name": "grid_energy_import_today", "addr": 0x2B, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
            {"name": "grid_energy_export_today", "addr": 0x2D, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
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
            "grid_frequency": round(raw.get("grid_frequency", 0), 2),
            "grid_voltage": round(raw.get("grid_voltage_r", 0), 1),
            "pv_voltage": round(max(raw.get("pv1_voltage", 0), raw.get("pv2_voltage", 0)), 1),
            "inverter_temp": round(raw.get("inverter_temp", 0), 1),
            "pv_energy_today": round(raw.get("pv_energy_today", 0), 1),
            "grid_energy_import_today": round(raw.get("grid_energy_import_today", 0), 1),
            "grid_energy_export_today": round(raw.get("grid_energy_export_today", 0), 1),
        }
