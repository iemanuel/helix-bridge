import time
import logging

from .base import BaseCollector
from .modbus_client import create_modbus_client, MODBUS_READ_HOLDING_REGISTERS

log = logging.getLogger("bridge.collector.sunsynk")

SUNSUNK_TO_METRIC = {
    "pv_power": "pv_power",
    "pv1_power": "pv_power_1",
    "pv2_power": "pv_power_2",
    "pv3_power": "pv_power_3",
    "pv1_voltage": "pv_voltage_1",
    "pv2_voltage": "pv_voltage_2",
    "pv3_voltage": "pv_voltage_3",
    "pv1_current": "pv_current_1",
    "pv2_current": "pv_current_2",
    "pv3_current": "pv_current_3",
    "grid_power": "grid_power",
    "grid_voltage": "grid_voltage",
    "grid_frequency": "grid_frequency",
    "load_power": "load_power",
    "battery_power": "battery_power",
    "battery_soc": "battery_soc",
    "battery_voltage": "battery_voltage",
    "battery_current": "battery_current",
    "battery_temperature": "battery_temperature",
    "radiator_temperature": "inverter_temp",
    "inverter_l1_voltage": "ac_output_voltage",
    "inverter_voltage": "ac_output_voltage",
    "day_pv_energy": "pv_energy_today",
    "day_load_energy": "load_energy_today",
    "day_grid_import": "grid_energy_import_today",
    "day_grid_export": "grid_energy_export_today",
}

# Aliases: some sensor IDs differ between single-phase and three-phase definitions
SUNSUNK_ALIASES = {
    "grid_voltage": ["grid_l1_voltage", "grid_voltage"],
}

# Derived metrics computed from raw sensor values
DERIVED_METRICS = {
    "pv_power": lambda v, s: v.get("pv_power") or (
        sum(abs(v.get(s, 0)) for s in ["pv_power_1", "pv_power_2", "pv_power_3", "pv_power_4"] if v.get(s))
    ),
    "pv_voltage": lambda v, s: max(
        v.get("pv_voltage_1", 0), v.get("pv_voltage_2", 0), v.get("pv_voltage_3", 0), v.get("pv_voltage_4", 0)
    ),
    "pv_current": lambda v, s: sum(
        v.get(s, 0) for s in ["pv_current_1", "pv_current_2", "pv_current_3", "pv_current_4"]
    ),
    "ac_output_voltage": lambda v, s: v.get("ac_output_voltage") or v.get("inverter_voltage", 0),
}

MODEL_TO_DEFS = {
    "single-phase": "sunsynk.definitions.single_phase",
    "single_phase": "sunsynk.definitions.single_phase",
    "three_phase_lv": "sunsynk.definitions.three_phase_lv",
    "three-phase-lv": "sunsynk.definitions.three_phase_lv",
    "three_phase_hv": "sunsynk.definitions.three_phase_hv",
    "three-phase-hv": "sunsynk.definitions.three_phase_hv",
}


def _import_defs(model: str):
    path = MODEL_TO_DEFS.get(model, "sunsynk.definitions.three_phase_lv")
    import importlib
    mod = importlib.import_module(path)
    return mod.SENSORS.all


class SunsynkCollector(BaseCollector):
    METRICS = {
        "pv_power", "pv_power_1", "pv_power_2", "pv_power_3",
        "grid_power", "grid_voltage", "grid_frequency",
        "load_power", "load_power_essential", "load_power_non_essential",
        "battery_power", "battery_soc", "battery_voltage", "battery_current",
        "battery_temperature",
        "pv_voltage", "pv_voltage_1", "pv_voltage_2", "pv_voltage_3",
        "pv_current", "pv_current_1", "pv_current_2", "pv_current_3",
        "inverter_temp", "ac_couple_pv_power", "auxiliary_pv_power",
        "generator_power",
        "ac_output_voltage",
        "pv_energy_today", "load_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
    }

    def __init__(self, config):
        super().__init__()
        self._client = create_modbus_client(config)
        model = (config.inverter_model or "").lower()
        self._sensor_defs = _import_defs(model)
        self._name_map = SUNSUNK_TO_METRIC.copy()

    def _resolve_sensor_id(self, sid):
        if sid in self._sensor_defs:
            return sid
        aliases = SUNSUNK_ALIASES.get(sid)
        if aliases:
            for alias in aliases:
                if alias in self._sensor_defs:
                    return alias
        return None

    def _sensors_for_metrics(self):
        wanted = {}
        for sid, mname in self._name_map.items():
            resolved = self._resolve_sensor_id(sid)
            if resolved:
                sensor = self._sensor_defs[resolved]
                wanted[mname] = (sid, sensor)
        return wanted

    def poll(self):
        ts = int(time.time() * 1000)

        wanted = self._sensors_for_metrics()
        if not wanted:
            return None

        batch_defs = []
        for mname, (sid, sensor) in wanted.items():
            for offset in range(len(sensor.address)):
                batch_defs.append({
                    "name": f"{sid}_{offset}",
                    "addr": sensor.address[offset],
                    "func": MODBUS_READ_HOLDING_REGISTERS,
                    "count": 1,
                    "scale": 1,
                    "signed": False,
                })

        raw = self._client.read_batch(batch_defs)
        if not raw:
            return None

        decoded = {}
        for mname, (sid, sensor) in wanted.items():
            regs = []
            for offset in range(len(sensor.address)):
                key = f"{sid}_{offset}"
                regs.append(raw.get(key, 0))
            try:
                val = sensor.reg_to_value(regs)
                decoded[mname] = val
            except Exception as e:
                log.warning("sunsynk decode %s: %s", sid, e)

        pv1 = decoded.get("pv_power_1", 0) or 0
        pv2 = decoded.get("pv_power_2", 0) or 0
        pv3 = decoded.get("pv_power_3", 0) or 0
        pv_total = decoded.get("pv_power", 0) or 0
        if not pv_total:
            pv_total = abs(pv1) + abs(pv2) + abs(pv3)

        load = decoded.get("load_power", 0) or 0
        load_essential = 0
        load_non_essential = 0
        if load != 0:
            load_non_essential = decoded.get("load_power_non_essential", 0) or 0
            essential = abs(load) - abs(load_non_essential)
            load_essential = max(0, essential)

        result = {
            "timestamp": ts,
            "pv_power": round(abs(pv_total), 1),
            "pv_power_1": round(abs(pv1), 1),
            "pv_power_2": round(abs(pv2), 1),
            "pv_power_3": round(abs(pv3), 1),
            "grid_power": round(decoded.get("grid_power", 0) or 0, 1),
            "grid_voltage": round(decoded.get("grid_voltage", 0) or 0, 1),
            "grid_frequency": round(decoded.get("grid_frequency", 0) or 0, 2),
            "load_power": round(abs(load), 1),
            "load_power_essential": round(load_essential, 1),
            "load_power_non_essential": round(abs(load_non_essential), 1),
            "battery_power": round(decoded.get("battery_power", 0) or 0, 1),
            "battery_soc": round(decoded.get("battery_soc", 0) or 0, 1),
            "battery_voltage": round(decoded.get("battery_voltage", 0) or 0, 2),
            "battery_current": round(decoded.get("battery_current", 0) or 0, 1),
            "battery_temperature": round(decoded.get("battery_temperature", 0) or 0, 1),
            "pv_voltage": round(max(
                decoded.get("pv_voltage_1", 0) or 0,
                decoded.get("pv_voltage_2", 0) or 0,
                decoded.get("pv_voltage_3", 0) or 0,
            ), 1),
            "pv_voltage_1": round(decoded.get("pv_voltage_1", 0) or 0, 1),
            "pv_voltage_2": round(decoded.get("pv_voltage_2", 0) or 0, 1),
            "pv_voltage_3": round(decoded.get("pv_voltage_3", 0) or 0, 1),
            "pv_current": round(
                (decoded.get("pv_current_1", 0) or 0)
                + (decoded.get("pv_current_2", 0) or 0)
                + (decoded.get("pv_current_3", 0) or 0), 1),
            "pv_current_1": round(decoded.get("pv_current_1", 0) or 0, 1),
            "pv_current_2": round(decoded.get("pv_current_2", 0) or 0, 1),
            "pv_current_3": round(decoded.get("pv_current_3", 0) or 0, 1),
            "inverter_temp": round(decoded.get("inverter_temp", 0) or 0, 1),
            "pv_energy_today": round(decoded.get("pv_energy_today", 0) or 0, 2),
            "load_energy_today": round(decoded.get("load_energy_today", 0) or 0, 2),
            "grid_energy_import_today": round(decoded.get("grid_energy_import_today", 0) or 0, 2),
            "grid_energy_export_today": round(decoded.get("grid_energy_export_today", 0) or 0, 2),
        }

        result["ac_couple_pv_power"] = round(decoded.get("ac_couple_pv_power", 0) or 0, 1)
        result["auxiliary_pv_power"] = round(decoded.get("auxiliary_pv_power", 0) or 0, 1)
        result["generator_power"] = round(decoded.get("generator_power", 0) or 0, 1)
        result["ac_output_voltage"] = round(decoded.get("ac_output_voltage", 0) or 0, 1)

        return result
