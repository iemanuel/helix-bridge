import math
import random
import time
import logging

from .base import BaseCollector

log = logging.getLogger("bridge.collector.simulation")

_SUNSYNK_METRICS = {
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

_GOODWE_METRICS = {
    "pv_power", "grid_power", "battery_power", "load_power",
    "battery_soc", "battery_voltage",
    "grid_voltage", "grid_frequency", "pv_voltage", "inverter_temp",
    "pv_energy_today", "load_energy_today",
    "grid_energy_import_today", "grid_energy_export_today",
}

_HUAWEI_METRICS = {
    "pv_power", "grid_power", "grid_frequency", "grid_voltage",
    "pv_voltage", "inverter_temp",
    "pv_energy_today", "grid_energy_import_today", "grid_energy_export_today",
    "battery_soc", "battery_power", "battery_voltage",
}

_GENERIC_HYBRID_METRICS = {
    "pv_power", "grid_power", "battery_power", "load_power",
    "battery_soc", "grid_voltage", "grid_frequency",
    "pv_voltage", "battery_voltage", "inverter_temp",
}

_SOLIS_METRICS = {
    "pv_power", "grid_power", "grid_frequency", "grid_voltage",
    "pv_voltage", "inverter_temp",
    "pv_energy_today", "grid_energy_import_today", "grid_energy_export_today",
}

_GROWATT_METRICS = {
    "pv_power", "grid_power", "grid_frequency",
    "pv_energy_today", "grid_energy_import_today",
    "load_power", "battery_power", "battery_soc", "battery_voltage", "inverter_temp",
}

_SOFAR_METRICS = {
    "pv_power", "grid_power", "grid_frequency", "grid_voltage",
    "pv_voltage", "inverter_temp",
    "pv_energy_today", "grid_energy_import_today",
    "load_power", "battery_power", "battery_soc", "battery_voltage", "load_energy_today",
}

_VOLTRONIC_METRICS = {
    "pv_power", "grid_power", "grid_voltage", "grid_frequency",
    "load_power", "battery_power", "battery_soc", "battery_voltage",
    "inverter_temp", "pv_voltage",
}

_VICTRON_METRICS = {
    "pv_power", "battery_power", "battery_soc", "battery_voltage", "load_power",
}

_SUNSPEC_METRICS = {
    "pv_power", "pv_voltage", "grid_power", "grid_frequency", "grid_voltage",
    "inverter_temp", "pv_energy_today",
    "grid_energy_import_today", "grid_energy_export_today",
    "battery_soc", "battery_power", "battery_voltage",
}

SIM_PROFILES = {
    "goodwe": {
        "name": "Goodwe GW10K-ET",
        "metrics": _GOODWE_METRICS,
    },
    "deye": {
        "name": "Deye 12kW Three Phase",
        "metrics": _SUNSYNK_METRICS,
    },
    "sol_ark": {
        "name": "Sol-Ark 12K",
        "metrics": _SUNSYNK_METRICS,
    },
    "sunsynk": {
        "name": "Sunsynk 12kW Three Phase",
        "metrics": _SUNSYNK_METRICS,
    },
    "huawei": {
        "name": "Huawei SUN2000-10KTL-M1",
        "metrics": _HUAWEI_METRICS,
    },
    "solis": {
        "name": "Solis S6-GR1P10K",
        "metrics": _SOLIS_METRICS,
    },
    "growatt": {
        "name": "Growatt SPH 10000TL3 BH-UP",
        "metrics": _GROWATT_METRICS,
    },
    "sofar": {
        "name": "Sofar HYD 10KTL-3PH",
        "metrics": _SOFAR_METRICS,
    },
    "luxpower": {
        "name": "Luxpower SNA 10K",
        "metrics": _GOODWE_METRICS,
    },
    "sma": {
        "name": "SMA Sunny Boy Storage 5.0",
        "metrics": _HUAWEI_METRICS,
    },
    "fronius": {
        "name": "Fronius Symo GEN24 10.0",
        "metrics": _GENERIC_HYBRID_METRICS,
    },
    "voltronic": {
        "name": "Voltronic Axpert King 5KVA",
        "metrics": _VOLTRONIC_METRICS,
    },
    "axpert": {
        "name": "Voltronic Axpert King 5KVA",
        "metrics": _VOLTRONIC_METRICS,
    },
    "mppsolar": {
        "name": "Voltronic MPP Solar 5KVA",
        "metrics": _VOLTRONIC_METRICS,
    },
    "victron_vedirect": {
        "name": "Victron Energy Multiplus-II",
        "metrics": _VICTRON_METRICS,
    },
    "sunspec": {
        "name": "Generic SunSpec Inverter",
        "metrics": _SUNSPEC_METRICS,
    },
    "generic_modbus": {
        "name": "Generic Modbus Inverter",
        "metrics": _GENERIC_HYBRID_METRICS,
    },
}


class SimulationCollector(BaseCollector):
    def __init__(self, config):
        super().__init__()
        self._start = time.time()
        self._interval = config.poll_interval
        model = (config.inverter_model or "goodwe").lower()
        if model not in SIM_PROFILES:
            log.warning("unknown simulation profile '%s', falling back to goodwe", model)
            model = "goodwe"
        self._profile = model
        self._profile_name = SIM_PROFILES[model]["name"]
        self.METRICS = SIM_PROFILES[model]["metrics"]
        log.info("simulation profile: %s (%s)", model, self._profile_name)

    def _elapsed(self):
        return time.time() - self._start

    def _hours(self):
        return (self._elapsed() / 3600) % 24

    def _daylight(self, hours):
        return max(0, math.sin(math.pi * (hours - 6) / 12))

    def _base_poll(self):
        t = self._elapsed()
        hours = self._hours()
        dl = self._daylight(hours)

        pv_power = dl * random.uniform(3000, 5000) + random.gauss(0, 100)
        pv_power = max(0, pv_power)

        pv1 = pv_power * random.uniform(0.4, 0.6)
        pv2 = pv_power - pv1
        pv3 = pv_power * random.uniform(0, 0.1)

        pv_v = dl * (360 + random.gauss(0, 5))
        pv1_v = pv_v + random.gauss(0, 2)
        pv2_v = pv_v + random.gauss(0, 2)
        pv3_v = pv_v + random.gauss(0, 2)

        battery_soc = 50 + 40 * math.sin(t / 3600) + random.gauss(0, 0.5)
        battery_soc = max(5, min(98, battery_soc))

        battery_power = math.sin(t / 1200) * 1000
        battery_v = 48 + random.gauss(0, 0.5)
        battery_curr = battery_power / battery_v if battery_v > 0 else 0

        load_base = 500 + 400 * math.sin(math.pi * (hours - 8) / 14)
        load_power = max(200, load_base + random.gauss(0, 50))
        load_non_essential = random.uniform(0.1, 0.4) * load_power
        load_essential = load_power - load_non_essential

        grid_power = load_power - pv_power - battery_power
        grid_power += random.gauss(0, 50)

        grid_v = 230 + random.gauss(0, 2)
        grid_f = 50 + random.gauss(0, 0.05)

        inv_temp = 30 + dl * 20 + random.gauss(0, 2)
        battery_temp = 22 + dl * 8 + random.gauss(0, 1)

        pv_energy = (t / 3600) * dl * 4.0
        load_energy = (t / 3600) * 1.2
        grid_import = sum(random.uniform(0, 0.01) for _ in range(int(t / 60))) if t > 0 else 0
        grid_export = sum(random.uniform(0, 0.015) for _ in range(int(t / 60))) if t > 0 else 0

        return {
            "pv_power": round(pv_power, 1),
            "pv_power_1": round(pv1, 1),
            "pv_power_2": round(pv2, 1),
            "pv_power_3": round(pv3, 1),
            "pv_voltage": round(pv_v, 1),
            "pv_voltage_1": round(pv1_v, 1),
            "pv_voltage_2": round(pv2_v, 1),
            "pv_voltage_3": round(pv3_v, 1),
            "pv_current": round(pv_power / pv_v if pv_v > 0 else 0, 1),
            "pv_current_1": round(pv1 / pv1_v if pv1_v > 0 else 0, 1),
            "pv_current_2": round(pv2 / pv2_v if pv2_v > 0 else 0, 1),
            "pv_current_3": round(pv3 / pv3_v if pv3_v > 0 else 0, 1),
            "grid_power": round(max(-10000, min(10000, grid_power)), 1),
            "grid_voltage": round(grid_v, 1),
            "grid_frequency": round(grid_f, 2),
            "load_power": round(load_power, 1),
            "load_power_essential": round(load_essential, 1),
            "load_power_non_essential": round(load_non_essential, 1),
            "battery_power": round(battery_power, 1),
            "battery_soc": round(battery_soc, 1),
            "battery_voltage": round(battery_v, 2),
            "battery_current": round(battery_curr, 1),
            "battery_temperature": round(battery_temp, 1),
            "inverter_temp": round(inv_temp, 1),
            "ac_couple_pv_power": round(dl * random.uniform(0, 500), 1),
            "auxiliary_pv_power": round(dl * random.uniform(0, 300), 1),
            "generator_power": round(random.uniform(0, 100) if random.random() < 0.1 else 0, 1),
            "ac_output_voltage": round(grid_v + random.gauss(0, 1), 1),
            "pv_energy_today": round(pv_energy, 2),
            "load_energy_today": round(load_energy, 2),
            "grid_energy_import_today": round(grid_import, 2),
            "grid_energy_export_today": round(grid_export, 2),
            "pv_power_predicted": round(pv_power * random.uniform(0.85, 1.15), 1),
        }

    def poll(self):
        ts = int(time.time() * 1000)
        base = self._base_poll()
        result = {"timestamp": ts}
        metrics = SIM_PROFILES[self._profile]["metrics"]
        for m in metrics:
            if m in base:
                result[m] = base[m]
        return result
