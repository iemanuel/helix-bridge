import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS, MODBUS_READ_INPUT_REGISTERS

log = logging.getLogger("bridge.collector.sofar")


SOFAR_KTL_REGISTERS = [
    {"name": "pv1_power", "addr": 0x00, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv2_power", "addr": 0x01, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv1_voltage", "addr": 0x02, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "pv2_voltage", "addr": 0x03, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "grid_voltage_r", "addr": 0x06, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "grid_frequency", "addr": 0x09, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "grid_power_total", "addr": 0x0C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "inverter_temp", "addr": 0x11, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "pv_energy_today", "addr": 0x24, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x26, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
]

SOFAR_HYBRID_REGISTERS = [
    {"name": "pv1_power", "addr": 0x00, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv2_power", "addr": 0x01, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv1_voltage", "addr": 0x02, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "pv2_voltage", "addr": 0x03, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "grid_voltage_r", "addr": 0x06, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "grid_frequency", "addr": 0x09, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "grid_power_total", "addr": 0x0C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "load_power_total", "addr": 0x0D, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "battery_voltage", "addr": 0x0F, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "battery_soc", "addr": 0x10, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "battery_current", "addr": 0x11, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "signed": True, "count": 1},
    {"name": "battery_power", "addr": 0x12, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "inverter_temp", "addr": 0x16, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "pv_energy_today", "addr": 0x30, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x32, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "load_energy_today", "addr": 0x34, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.1, "count": 2},
]

SOFAR_MODELS = {
    "ktl": SOFAR_KTL_REGISTERS,
    "ktl-x": SOFAR_KTL_REGISTERS,
    "hvt": SOFAR_HYBRID_REGISTERS,
    "hybrid": SOFAR_HYBRID_REGISTERS,
    "me": SOFAR_HYBRID_REGISTERS,
}


class SofarCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "grid_frequency", "grid_voltage",
        "pv_voltage", "inverter_temp",
        "pv_energy_today", "grid_energy_import_today",
        "load_power", "battery_power", "battery_soc", "battery_voltage", "load_energy_today",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        model = config.inverter_model or "ktl"
        self._regs = SOFAR_MODELS.get(model, SOFAR_KTL_REGISTERS)
        self._is_hybrid = model in ("hvt", "hybrid", "me")

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        raw = self._client.read_batch(self._regs)
        if not raw:
            return None

        pv1 = raw.get("pv1_power", 0)
        pv2 = raw.get("pv2_power", 0)

        result = {
            "timestamp": ts,
            "pv_power": round(pv1 + pv2, 1),
            "grid_power": round(raw.get("grid_power_total", 0), 1),
            "grid_frequency": round(raw.get("grid_frequency", 0), 2),
            "grid_voltage": round(raw.get("grid_voltage_r", 0), 1),
            "pv_voltage": round(max(raw.get("pv1_voltage", 0), raw.get("pv2_voltage", 0)), 1),
            "inverter_temp": round(raw.get("inverter_temp", 0), 1),
            "pv_energy_today": round(raw.get("pv_energy_today", 0), 1),
            "grid_energy_import_today": round(raw.get("grid_energy_import_today", 0), 1),
        }

        if self._is_hybrid:
            result["load_power"] = round(raw.get("load_power_total", 0), 1)
            result["battery_power"] = round(raw.get("battery_power", 0), 1)
            result["battery_soc"] = round(raw.get("battery_soc", 0), 1)
            result["battery_voltage"] = round(raw.get("battery_voltage", 0), 2)
            result["load_energy_today"] = round(raw.get("load_energy_today", 0), 1)

        return result
