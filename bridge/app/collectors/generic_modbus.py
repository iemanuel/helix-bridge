import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_INPUT_REGISTERS

log = logging.getLogger("bridge.collector.generic_modbus")


class GenericModbusCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "battery_power", "load_power", "battery_soc",
        "grid_voltage", "grid_frequency", "pv_voltage", "battery_voltage", "inverter_temp",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        self._registers = [
            {"name": "pv_power", "addr": 0, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1},
            {"name": "grid_power", "addr": 2, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1},
            {"name": "battery_power", "addr": 4, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1},
            {"name": "load_power", "addr": 6, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 1},
            {"name": "battery_soc", "addr": 8, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1},
            {"name": "grid_voltage", "addr": 10, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1},
            {"name": "grid_frequency", "addr": 12, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01},
            {"name": "pv_voltage", "addr": 14, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1},
            {"name": "battery_voltage", "addr": 16, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.01},
            {"name": "inverter_temp", "addr": 18, "func": MODBUS_READ_INPUT_REGISTERS, "scale": 0.1},
        ]

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        result = self._client.read_batch(self._registers)
        if not result:
            return None
        result["timestamp"] = ts
        return result
