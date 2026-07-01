import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_INPUT_REGISTERS

log = logging.getLogger("bridge.collector.growatt")

GROWATT_REGISTERS_MIN = [
    {"name": "pv1_power", "addr": 0x0B, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv2_power", "addr": 0x0C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "grid_frequency", "addr": 0x16, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "grid_power_total", "addr": 0x18, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "pv_energy_today", "addr": 0x26, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x2C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
]

GROWATT_REGISTERS_TLX = [
    {"name": "pv1_power", "addr": 0x0D, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv2_power", "addr": 0x0E, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv3_power", "addr": 0x0F, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv4_power", "addr": 0x10, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "grid_frequency", "addr": 0x17, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "grid_power_total", "addr": 0x19, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "pv_energy_today", "addr": 0x2B, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x31, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
]

GROWATT_REGISTERS_SPH = [
    {"name": "pv1_power", "addr": 0x0B, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "pv2_power", "addr": 0x0C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "grid_frequency", "addr": 0x16, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01, "count": 1},
    {"name": "grid_power_total", "addr": 0x18, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "load_power_total", "addr": 0x1A, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "battery_soc", "addr": 0x1C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "count": 1},
    {"name": "battery_power", "addr": 0x1D, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1, "signed": True, "count": 1},
    {"name": "battery_voltage", "addr": 0x1E, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "inverter_temp", "addr": 0x20, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 1},
    {"name": "pv_energy_today", "addr": 0x26, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
    {"name": "grid_energy_import_today", "addr": 0x2C, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1, "count": 2},
]

GROWATT_MODELS = {
    "min": GROWATT_REGISTERS_MIN,
    "tlx": GROWATT_REGISTERS_TLX,
    "sph": GROWATT_REGISTERS_SPH,
    "spa": GROWATT_REGISTERS_SPH,
}


class GrowattCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "grid_frequency",
        "pv_energy_today", "grid_energy_import_today",
        "load_power", "battery_power", "battery_soc", "battery_voltage", "inverter_temp",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        model = config.inverter_model or "min"
        self._regs = GROWATT_MODELS.get(model, GROWATT_REGISTERS_MIN)
        self._model = model

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        raw = self._client.read_batch(self._regs)
        if not raw:
            return None

        pv1 = raw.get("pv1_power", 0)
        pv2 = raw.get("pv2_power", 0)
        pv3 = raw.get("pv3_power", 0)
        pv4 = raw.get("pv4_power", 0)

        result = {
            "timestamp": ts,
            "pv_power": round(pv1 + pv2 + pv3 + pv4, 1),
            "grid_power": round(raw.get("grid_power_total", 0), 1),
            "grid_frequency": round(raw.get("grid_frequency", 0), 2),
            "pv_energy_today": round(raw.get("pv_energy_today", 0), 1),
            "grid_energy_import_today": round(raw.get("grid_energy_import_today", 0), 1),
        }

        if self._model in ("sph", "spa"):
            result["load_power"] = round(raw.get("load_power_total", 0), 1)
            result["battery_power"] = round(raw.get("battery_power", 0), 1)
            result["battery_soc"] = round(raw.get("battery_soc", 0), 1)
            result["battery_voltage"] = round(raw.get("battery_voltage", 0), 2)
            result["inverter_temp"] = round(raw.get("inverter_temp", 0), 1)

        return result
