from abc import ABC, abstractmethod
import time


metric_definitions = [
    {"name": "pv_power", "description": "PV Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_power_1", "description": "PV Power 1", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_power_2", "description": "PV Power 2", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_power_3", "description": "PV Power 3", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_power_predicted", "description": "PV Power Predicted", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_voltage", "description": "PV Voltage", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_voltage_1", "description": "PV Voltage 1", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_voltage_2", "description": "PV Voltage 2", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_voltage_3", "description": "PV Voltage 3", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "pv_current", "description": "PV Current", "unit": "A", "device_class": "current", "state_class": "measurement", "icon": "mdi:current-dc"},
    {"name": "pv_current_1", "description": "PV Current 1", "unit": "A", "device_class": "current", "state_class": "measurement", "icon": "mdi:current-dc"},
    {"name": "pv_current_2", "description": "PV Current 2", "unit": "A", "device_class": "current", "state_class": "measurement", "icon": "mdi:current-dc"},
    {"name": "pv_current_3", "description": "PV Current 3", "unit": "A", "device_class": "current", "state_class": "measurement", "icon": "mdi:current-dc"},
    {"name": "grid_power", "description": "Grid Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower"},
    {"name": "battery_power", "description": "Battery Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:battery"},
    {"name": "load_power", "description": "Load Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:flash"},
    {"name": "load_power_essential", "description": "Load Power Essential", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:flash"},
    {"name": "load_power_non_essential", "description": "Load Power Non-Essential", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:flash"},
    {"name": "battery_soc", "description": "Battery State of Charge", "unit": "%", "device_class": "battery", "state_class": "measurement", "icon": "mdi:battery"},
    {"name": "battery_voltage", "description": "Battery Voltage", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:battery"},
    {"name": "battery_current", "description": "Battery Current", "unit": "A", "device_class": "current", "state_class": "measurement", "icon": "mdi:current-dc"},
    {"name": "battery_temperature", "description": "Battery Temperature", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"name": "grid_voltage", "description": "Grid Voltage", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:sine-wave"},
    {"name": "grid_frequency", "description": "Grid Frequency", "unit": "Hz", "device_class": "frequency", "state_class": "measurement", "icon": "mdi:sine-wave"},
    {"name": "inverter_temp", "description": "Inverter Temperature", "unit": "°C", "device_class": "temperature", "state_class": "measurement", "icon": "mdi:thermometer"},
    {"name": "ac_output_voltage", "description": "AC Output Voltage", "unit": "V", "device_class": "voltage", "state_class": "measurement", "icon": "mdi:sine-wave"},
    {"name": "ac_couple_pv_power", "description": "AC Couple PV Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "auxiliary_pv_power", "description": "Auxiliary PV Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:solar-power"},
    {"name": "generator_power", "description": "Generator Power", "unit": "W", "device_class": "power", "state_class": "measurement", "icon": "mdi:engine"},
    {"name": "load_energy_today", "description": "Load Energy Today", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "icon": "mdi:flash"},
    {"name": "pv_energy_today", "description": "PV Energy Today", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "icon": "mdi:solar-power"},
    {"name": "grid_energy_import_today", "description": "Grid Energy Imported Today", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "icon": "mdi:transmission-tower"},
    {"name": "grid_energy_export_today", "description": "Grid Energy Exported Today", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing", "icon": "mdi:transmission-tower"},
]


class BaseCollector(ABC):
    def __init__(self):
        self._last_poll = 0

    @abstractmethod
    def poll(self) -> dict | None:
        ...

    def write_register(self, reg_addr: int, value: int) -> bool:
        client = getattr(self, '_client', None)
        if client is not None and hasattr(client, 'write_single_register'):
            return client.write_single_register(reg_addr, value)
        return False

    def get_metric_definitions(self):
        names = getattr(self, 'METRICS', None)
        if names:
            name_set = set(names)
            return [m for m in metric_definitions if m["name"] in name_set]
        return metric_definitions


class CollectorRegistry:
    def __init__(self):
        self._collectors: list[BaseCollector] = []

    def register(self, collector: BaseCollector):
        self._collectors.append(collector)

    def get_collector(self):
        if not self._collectors:
            raise RuntimeError("no collectors registered")
        return self._collectors[0]

    def all(self):
        return list(self._collectors)
