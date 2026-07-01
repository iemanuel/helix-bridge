import logging
import time

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS

log = logging.getLogger("bridge.collector.sunspec")

SUNSPEC_COMMON_MODEL_1 = [
    {"name": "sunspect_did", "addr": 0, "count": 1},
    {"name": "sunspect_length", "addr": 2, "count": 1},
    {"name": "sunspect_manufacturer", "addr": 4, "count": 16},
    {"name": "sunspect_model", "addr": 20, "count": 16},
    {"name": "sunspect_version", "addr": 36, "count": 8},
    {"name": "sunspect_serial", "addr": 44, "count": 16},
]

SUNSPEC_INVERTER_MODEL_101 = [
    {"name": "sunspec_did", "addr": 0, "count": 1},
    {"name": "sunspec_length", "addr": 2, "count": 1},
    {"name": "pv_power", "addr": 7, "count": 2, "scale": 1, "signed": True},
    {"name": "pv_voltage", "addr": 9, "count": 2, "scale": 0.001},
    {"name": "pv_current", "addr": 11, "count": 2, "scale": 0.001},
    {"name": "grid_power_total", "addr": 15, "count": 2, "scale": 1, "signed": True},
    {"name": "grid_frequency", "addr": 17, "count": 2, "scale": 0.001},
    {"name": "grid_voltage_r", "addr": 19, "count": 2, "scale": 0.001},
    {"name": "grid_current_r", "addr": 21, "count": 2, "scale": 0.001},
    {"name": "inverter_temp", "addr": 27, "count": 2, "scale": 0.01},
    {"name": "pv_energy_today", "addr": 31, "count": 2, "scale": 0.001},
    {"name": "pv_energy_total", "addr": 33, "count": 2, "scale": 0.001},
]

SUNSPEC_INVERTER_MODEL_103 = [
    {"name": "sunspec_did", "addr": 0, "count": 1},
    {"name": "sunspec_length", "addr": 2, "count": 1},
    {"name": "pv_power", "addr": 7, "count": 2, "scale": 1, "signed": True},
    {"name": "pv_voltage", "addr": 9, "count": 2, "scale": 0.001},
    {"name": "pv_current", "addr": 11, "count": 2, "scale": 0.001},
    {"name": "grid_power_total", "addr": 15, "count": 2, "scale": 1, "signed": True},
    {"name": "grid_frequency", "addr": 17, "count": 2, "scale": 0.001},
    {"name": "grid_voltage_r", "addr": 19, "count": 2, "scale": 0.001},
    {"name": "grid_current_r", "addr": 21, "count": 2, "scale": 0.001},
    {"name": "grid_voltage_s", "addr": 23, "count": 2, "scale": 0.001},
    {"name": "grid_current_s", "addr": 25, "count": 2, "scale": 0.001},
    {"name": "grid_voltage_t", "addr": 27, "count": 2, "scale": 0.001},
    {"name": "grid_current_t", "addr": 29, "count": 2, "scale": 0.001},
    {"name": "inverter_temp", "addr": 33, "count": 2, "scale": 0.01},
    {"name": "pv_energy_today", "addr": 37, "count": 2, "scale": 0.001},
    {"name": "pv_energy_total", "addr": 39, "count": 2, "scale": 0.001},
]

SUNSPEC_METER_MODEL_201 = [
    {"name": "sunspec_did", "addr": 0, "count": 1},
    {"name": "sunspec_length", "addr": 2, "count": 1},
    {"name": "meter_power_total", "addr": 7, "count": 2, "scale": 1, "signed": True},
    {"name": "meter_voltage_r", "addr": 9, "count": 2, "scale": 0.001},
    {"name": "meter_current_r", "addr": 11, "count": 2, "scale": 0.001},
    {"name": "meter_energy_import", "addr": 19, "count": 2, "scale": 0.001},
    {"name": "meter_energy_export", "addr": 21, "count": 2, "scale": 0.001},
    {"name": "meter_voltage_s", "addr": 23, "count": 2, "scale": 0.001},
    {"name": "meter_current_s", "addr": 25, "count": 2, "scale": 0.001},
    {"name": "meter_voltage_t", "addr": 27, "count": 2, "scale": 0.001},
    {"name": "meter_current_t", "addr": 29, "count": 2, "scale": 0.001},
]

SUNSPEC_BATTERY_MODEL_801 = [
    {"name": "sunspec_did", "addr": 0, "count": 1},
    {"name": "sunspec_length", "addr": 2, "count": 1},
    {"name": "battery_soc", "addr": 7, "count": 2, "scale": 1, "signed": True},
    {"name": "battery_power", "addr": 15, "count": 2, "scale": 1, "signed": True},
    {"name": "battery_voltage", "addr": 17, "count": 2, "scale": 0.001},
    {"name": "battery_current", "addr": 19, "count": 2, "scale": 0.001, "signed": True},
    {"name": "battery_temp", "addr": 21, "count": 2, "scale": 0.01},
]


class SunSpecCollector(BaseCollector):
    METRICS = {
        "pv_power", "pv_voltage", "grid_power", "grid_frequency", "grid_voltage",
        "inverter_temp", "pv_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
        "battery_soc", "battery_power", "battery_voltage",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        self._model_map = {}

    def _scan_models(self):
        """Scan the SunSpec model table starting at 0x0000."""
        addr = 0x0000
        while addr < 0xF000:
            try:
                raw = self._client.read_registers(addr, 2)
                if not raw or len(raw) < 2:
                    break
                did = raw[0]
                length = raw[1]
                if did == 0xFFFF:
                    break
                if did != 0 and length > 0 and length < 200:
                    self._model_map[did] = addr
                    log.info("sunspec: discovered model %d at 0x%04X (len=%d)", did, addr, length)
                addr += length + 2
            except Exception:
                break

    def _read_sunspec_block(self, base_addr: int, registers: list) -> dict:
        result = {}
        max_offset = max(r["addr"] + r.get("count", 1) for r in registers)
        raw = self._client.read_registers(base_addr, max_offset)
        if raw is None:
            return result

        for reg in registers:
            idx = reg["addr"]
            cnt = reg.get("count", 1)
            if idx + cnt > len(raw):
                continue

            if cnt == 2:
                val = (raw[idx] << 16) | raw[idx + 1]
            else:
                val = raw[idx]

            if reg.get("signed", False) and isinstance(val, int):
                if cnt == 2:
                    if val >= 0x80000000:
                        val -= 0x100000000
                else:
                    if val >= 0x8000:
                        val -= 0x10000

            scale = reg.get("scale", 1)
            if isinstance(val, int) and scale != 1:
                val = round(val * scale, 3)

            name = reg.get("name")
            if name:
                result[name] = val

        return result

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)

        if not self._model_map:
            self._scan_models()

        result = {"timestamp": ts}

        inv_model = None
        for mid in (103, 101):
            if mid in self._model_map:
                inv_model = mid
                break

        if inv_model is None:
            inv_model = 101

        if inv_model in self._model_map:
            base = self._model_map[inv_model]
            if inv_model == 101:
                data = self._read_sunspec_block(base, SUNSPEC_INVERTER_MODEL_101)
            else:
                data = self._read_sunspec_block(base, SUNSPEC_INVERTER_MODEL_103)

            if data:
                result["pv_power"] = round(data.get("pv_power", 0), 1)
                result["pv_voltage"] = round(data.get("pv_voltage", 0), 1)
                result["grid_power"] = round(data.get("grid_power_total", 0), 1)
                result["grid_frequency"] = round(data.get("grid_frequency", 0), 2)
                result["grid_voltage"] = round(data.get("grid_voltage_r", 0), 1)
                result["inverter_temp"] = round(data.get("inverter_temp", 0), 1)
                result["pv_energy_today"] = round(data.get("pv_energy_today", 0), 1)

        if 201 in self._model_map:
            base = self._model_map[201]
            data = self._read_sunspec_block(base, SUNSPEC_METER_MODEL_201)
            if data:
                meter_power = data.get("meter_power_total")
                if meter_power is not None:
                    result["grid_power"] = round(meter_power, 1)
                result["grid_energy_import_today"] = round(data.get("meter_energy_import", 0), 1)
                result["grid_energy_export_today"] = round(data.get("meter_energy_export", 0), 1)

        if 801 in self._model_map:
            base = self._model_map[801]
            data = self._read_sunspec_block(base, SUNSPEC_BATTERY_MODEL_801)
            if data:
                result["battery_soc"] = round(data.get("battery_soc", 0), 1)
                result["battery_power"] = round(data.get("battery_power", 0), 1)
                result["battery_voltage"] = round(data.get("battery_voltage", 0), 2)

        if len(result) <= 1:
            return None

        return result
