from unittest.mock import MagicMock
from bridge.app.collectors.base import BaseCollector, CollectorRegistry, metric_definitions


class MinimalCollector(BaseCollector):
    METRICS = {"pv_power", "grid_power", "battery_soc"}

    def poll(self):
        return {"timestamp": 0, "pv_power": 100}


class NoMetricsCollector(BaseCollector):
    def poll(self):
        return {"timestamp": 0}


def test_base_collector_abstract():
    """Can't instantiate BaseCollector directly because poll is abstract."""
    try:
        BaseCollector()
        assert False, "should have raised TypeError"
    except TypeError:
        pass


def test_minimal_collector_poll():
    c = MinimalCollector()
    r = c.poll()
    assert r["pv_power"] == 100


def test_get_metric_definitions_filters():
    c = MinimalCollector()
    defs = c.get_metric_definitions()
    names = {d["name"] for d in defs}
    assert names == {"pv_power", "grid_power", "battery_soc"}


def test_get_metric_definitions_all():
    c = NoMetricsCollector()
    defs = c.get_metric_definitions()
    assert len(defs) == len(metric_definitions)


def test_write_register_no_client():
    c = MinimalCollector()
    assert c.write_register(1, 100) is False


def test_write_register_with_client():
    c = MinimalCollector()
    client = MagicMock()
    client.write_single_register.return_value = True
    c._client = client
    assert c.write_register(42, 6000) is True
    client.write_single_register.assert_called_once_with(42, 6000)


def test_write_register_client_fails():
    c = MinimalCollector()
    client = MagicMock()
    client.write_single_register.return_value = False
    c._client = client
    assert c.write_register(1, 1) is False


def test_collector_registry_register_and_get():
    reg = CollectorRegistry()
    c1 = MinimalCollector()
    c2 = NoMetricsCollector()
    reg.register(c1)
    reg.register(c2)

    assert reg.get_collector() is c1
    assert reg.all() == [c1, c2]


def test_collector_registry_empty():
    reg = CollectorRegistry()
    try:
        reg.get_collector()
        assert False, "should raise"
    except RuntimeError:
        pass


def test_metric_definitions_completeness():
    names = {m["name"] for m in metric_definitions}
    expected = {
        "pv_power", "pv_power_1", "pv_power_2", "pv_power_3",
        "pv_power_predicted",
        "pv_voltage", "pv_voltage_1", "pv_voltage_2", "pv_voltage_3",
        "pv_current", "pv_current_1", "pv_current_2", "pv_current_3",
        "grid_power", "battery_power", "load_power",
        "load_power_essential", "load_power_non_essential",
        "battery_soc", "battery_voltage", "battery_current",
        "battery_temperature",
        "grid_voltage", "grid_frequency", "inverter_temp",
        "ac_output_voltage",
        "ac_couple_pv_power", "auxiliary_pv_power", "generator_power",
        "load_energy_today", "pv_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
    }
    assert names == expected, f"Missing: {expected - names}, Extra: {names - expected}"
