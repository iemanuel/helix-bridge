import asyncio
import time
import logging

from .base import BaseCollector

log = logging.getLogger("bridge.collector.goodwe")


class GoodweCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "battery_power", "load_power",
        "battery_soc", "battery_voltage",
        "grid_voltage", "grid_frequency", "pv_voltage", "inverter_temp",
        "pv_energy_today", "load_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
    }

    def __init__(self, config):
        super().__init__()
        self._host = config.inverter_modbus_host
        self._port = config.inverter_modbus_port or 8899

    def poll(self):
        import goodwe

        ts = int(time.time() * 1000)
        try:
            inverter = asyncio.run(goodwe.connect(self._host, port=self._port))
            data = asyncio.run(inverter.read_runtime_data())
        except Exception as e:
            log.error("goodwe poll error: %s", e)
            return None

        pv1 = data.get("ppv1", 0) or 0
        pv2 = data.get("ppv2", 0) or 0
        pv1_v = data.get("vpv1", 0) or 0
        pv2_v = data.get("vpv2", 0) or 0

        return {
            "timestamp": ts,
            "pv_power": round(data.get("ppv", pv1 + pv2) or 0, 1),
            "grid_power": round(data.get("pgrid", 0) or 0, 1),
            "battery_power": round(data.get("pbattery1", 0) or 0, 1),
            "load_power": round(data.get("load_ptotal", 0) or 0, 1),
            "battery_soc": round(data.get("battery_soc", 0) or 0, 1),
            "battery_voltage": round(data.get("vbattery1", 0) or 0, 2),
            "grid_voltage": round(data.get("vgrid", 0) or 0, 1),
            "grid_frequency": round(data.get("fgrid", 0) or 0, 2),
            "pv_voltage": round(max(pv1_v, pv2_v), 1),
            "inverter_temp": round(data.get("temperature", 0) or 0, 1),
            "pv_energy_today": round(data.get("e_day", 0) or 0, 1),
            "load_energy_today": round(data.get("e_load_day", 0) or 0, 1),
            "grid_energy_import_today": round(abs(data.get("e_day_imp", 0) or 0), 1),
            "grid_energy_export_today": round(data.get("e_day_exp", 0) or 0, 1),
        }
