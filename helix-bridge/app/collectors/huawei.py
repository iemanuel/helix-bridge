import asyncio
import time
import logging

from .base import BaseCollector

log = logging.getLogger("bridge.collector.huawei")


class HuaweiCollector(BaseCollector):
    METRICS = {
        "pv_power", "grid_power", "grid_frequency", "grid_voltage",
        "pv_voltage", "inverter_temp",
        "pv_energy_today", "grid_energy_import_today", "grid_energy_export_today",
        "battery_soc", "battery_power", "battery_voltage",
    }

    def __init__(self, config):
        super().__init__()
        self._host = config.inverter_modbus_host
        self._port = config.inverter_modbus_port or 502

    def poll(self):
        import huawei_solar
        from huawei_solar.register_names import (
            INPUT_POWER, ACTIVE_POWER, GRID_FREQUENCY, PHASE_A_VOLTAGE,
            DAILY_YIELD_ENERGY, GRID_EXPORTED_ENERGY, GRID_ACCUMULATED_ENERGY,
            INTERNAL_TEMPERATURE, PV_01_VOLTAGE,
            STORAGE_UNIT_1_STATE_OF_CAPACITY,
            STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER,
            STORAGE_UNIT_1_BUS_VOLTAGE,
        )

        ts = int(time.time() * 1000)
        try:
            client = asyncio.run(
                huawei_solar.create_tcp_client(self._host, port=self._port)
            )
            device = asyncio.run(
                huawei_solar.create_device_instance(client)
            )
            results = asyncio.run(device.batch_update([
                INPUT_POWER, ACTIVE_POWER, GRID_FREQUENCY, PHASE_A_VOLTAGE,
                DAILY_YIELD_ENERGY, GRID_EXPORTED_ENERGY, GRID_ACCUMULATED_ENERGY,
                INTERNAL_TEMPERATURE, PV_01_VOLTAGE,
                STORAGE_UNIT_1_STATE_OF_CAPACITY,
                STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER,
                STORAGE_UNIT_1_BUS_VOLTAGE,
            ]))
        except Exception as e:
            log.error("huawei poll error: %s", e)
            return None

        def val(name):
            r = results.get(name)
            if r is None:
                return 0
            v = r.value
            return v if v is not None else 0

        return {
            "timestamp": ts,
            "pv_power": round(val(INPUT_POWER), 1),
            "grid_power": round(val(ACTIVE_POWER), 1),
            "grid_frequency": round(val(GRID_FREQUENCY), 2),
            "grid_voltage": round(val(PHASE_A_VOLTAGE), 1),
            "pv_voltage": round(val(PV_01_VOLTAGE), 1),
            "inverter_temp": round(val(INTERNAL_TEMPERATURE), 1),
            "pv_energy_today": round(val(DAILY_YIELD_ENERGY), 1),
            "grid_energy_import_today": round(abs(val(GRID_ACCUMULATED_ENERGY)), 1),
            "grid_energy_export_today": round(val(GRID_EXPORTED_ENERGY), 1),
            "battery_soc": round(val(STORAGE_UNIT_1_STATE_OF_CAPACITY), 1),
            "battery_power": round(val(STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER), 1),
            "battery_voltage": round(val(STORAGE_UNIT_1_BUS_VOLTAGE), 2),
        }
