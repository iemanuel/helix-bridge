import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS

log = logging.getLogger("bridge.collector.sma")

SMA_SUNSPEC_COMMON = [
    {"name": "sunspec_did", "addr": 0x0000, "func": MODBUS_READ_HOLDING_REGISTERS, "count": 1},
    {"name": "sunspec_length", "addr": 0x0002, "func": MODBUS_READ_HOLDING_REGISTERS, "count": 1},
]

SMA_INVERTER_BLOCK = [
    {"name": "pv_power", "addr": 0x0107, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 2},
    {"name": "pv_energy_today", "addr": 0x0109, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_frequency", "addr": 0x0113, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "grid_power_total", "addr": 0x0115, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 2},
    {"name": "grid_voltage_r", "addr": 0x0119, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "inverter_temp", "addr": 0x0121, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.01, "count": 2},
    {"name": "pv_voltage", "addr": 0x0127, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
]

SMA_METER_BLOCK = [
    {"name": "meter_power_total", "addr": 0x0207, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 2},
    {"name": "meter_energy_import", "addr": 0x0209, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "meter_energy_export", "addr": 0x020B, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
    {"name": "meter_voltage_r", "addr": 0x0219, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
]

SMA_BATTERY_BLOCK = [
    {"name": "battery_power", "addr": 0x0307, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "signed": True, "count": 2},
    {"name": "battery_soc", "addr": 0x0309, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 1, "count": 2},
    {"name": "battery_voltage", "addr": 0x030D, "func": MODBUS_READ_HOLDING_REGISTERS, "scale": 0.001, "count": 2},
]


class SMACollector(BaseCollector):
    METRICS = {
        "pv_power", "pv_voltage", "pv_energy_today",
        "grid_power", "grid_voltage", "grid_frequency", "inverter_temp",
        "grid_energy_import_today", "grid_energy_export_today",
        "battery_power", "battery_soc", "battery_voltage",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)

    def _sunspec_detect(self) -> tuple | None:
        try:
            raw = self._client.read_registers(0x0000, 4)
            if raw and len(raw) >= 4:
                did = raw[0]
                length = raw[2]
                if did == 0x0001:
                    return (0x0004, min(length, 80))
        except Exception:
            pass
        return None

    def _read_block(self, registers: list) -> dict:
        return self._client.read_batch(registers)

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)

        block_info = self._sunspec_detect()
        if not block_info:
            return None

        inv_data = self._read_block(SMA_INVERTER_BLOCK)
        meter_data = self._read_block(SMA_METER_BLOCK)
        bat_data = self._read_block(SMA_BATTERY_BLOCK)

        if not inv_data and not meter_data:
            return None

        result = {"timestamp": ts}

        pv_power = inv_data.get("pv_power", 0)
        result["pv_power"] = round(pv_power, 1)
        result["pv_voltage"] = round(inv_data.get("pv_voltage", 0), 1)
        result["pv_energy_today"] = round(inv_data.get("pv_energy_today", 0), 1)

        grid_p = meter_data.get("meter_power_total", inv_data.get("grid_power_total", 0))
        result["grid_power"] = round(grid_p, 1)

        grid_v = meter_data.get("meter_voltage_r", inv_data.get("grid_voltage_r", 0))
        result["grid_voltage"] = round(grid_v, 1)
        result["grid_frequency"] = round(inv_data.get("grid_frequency", 0), 2)
        result["inverter_temp"] = round(inv_data.get("inverter_temp", 0), 1)

        result["grid_energy_import_today"] = round(meter_data.get("meter_energy_import", 0), 1)
        result["grid_energy_export_today"] = round(meter_data.get("meter_energy_export", 0), 1)

        if bat_data.get("battery_soc") is not None:
            result["battery_power"] = round(bat_data.get("battery_power", 0), 1)
            result["battery_soc"] = round(bat_data.get("battery_soc", 0), 1)
            result["battery_voltage"] = round(bat_data.get("battery_voltage", 0), 2)

        return result
