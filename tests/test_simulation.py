from tests.conftest import MockConfig
from collectors.simulation import SimulationCollector, SIM_PROFILES


def test_simulation_default_profile():
    config = MockConfig(inverter_model="")
    collector = SimulationCollector(config)
    assert collector._profile == "goodwe"
    assert collector.METRICS == SIM_PROFILES["goodwe"]["metrics"]


def test_simulation_unknown_profile():
    config = MockConfig(inverter_model="nonexistent")
    collector = SimulationCollector(config)
    assert collector._profile == "goodwe"


def test_simulation_goodwe_profile():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    assert collector._profile == "goodwe"
    assert collector.METRICS == SIM_PROFILES["goodwe"]["metrics"]


def test_simulation_huawei_profile():
    config = MockConfig(inverter_model="huawei")
    collector = SimulationCollector(config)
    assert collector._profile == "huawei"
    assert collector.METRICS == SIM_PROFILES["huawei"]["metrics"]


def test_simulation_sunsynk_profile():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    assert collector._profile == "sunsynk"
    assert collector.METRICS == SIM_PROFILES["sunsynk"]["metrics"]


def test_simulation_poll_returns_dict():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    result = collector.poll()
    assert isinstance(result, dict)
    assert "timestamp" in result


def test_simulation_poll_has_timestamp():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    result = collector.poll()
    assert isinstance(result["timestamp"], int)
    assert result["timestamp"] > 0


def test_simulation_goodwe_metrics():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    result = collector.poll()
    expected = SIM_PROFILES["goodwe"]["metrics"]
    for m in expected:
        assert m in result, f"missing metric: {m}"
    assert len(result) == len(expected) + 1  # +1 for timestamp


def test_simulation_huawei_metrics():
    config = MockConfig(inverter_model="huawei")
    collector = SimulationCollector(config)
    result = collector.poll()
    expected = SIM_PROFILES["huawei"]["metrics"]
    for m in expected:
        assert m in result, f"missing metric: {m}"
    assert len(result) == len(expected) + 1


def test_simulation_sunsynk_metrics():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    result = collector.poll()
    expected = SIM_PROFILES["sunsynk"]["metrics"]
    for m in expected:
        assert m in result, f"missing metric: {m}"
    assert len(result) == len(expected) + 1


def test_simulation_values_in_range():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)

    for _ in range(20):
        result = collector.poll()
        assert 0 <= result["battery_soc"] <= 100
        assert -10000 <= result["grid_power"] <= 10000
        assert -10000 <= result["battery_power"] <= 10000
        assert 0 <= result["load_power"] <= 10000
        assert 0 <= result.get("pv_power", 0) <= 10000
        assert 0 <= result.get("inverter_temp", 0) <= 70
        assert 18 <= result.get("battery_voltage", 0) <= 60
        assert 200 <= result.get("grid_voltage", 0) <= 260
        assert 49 <= result.get("grid_frequency", 0) <= 51


def test_simulation_values_change_over_time():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)

    results = set()
    for _ in range(20):
        results.add(collector.poll()["grid_voltage"])
    assert len(results) > 1


def test_simulation_timestamp_increases():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)

    first = collector.poll()
    import time
    time.sleep(0.001)
    second = collector.poll()

    assert second["timestamp"] >= first["timestamp"]


def test_simulation_collector_is_base_collector():
    from collectors.base import BaseCollector
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    assert isinstance(collector, BaseCollector)


def test_simulation_supports_write_register():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    result = collector.write_register(0, 100)
    assert result is False


def test_simulation_goodwe_no_extra_metrics():
    config = MockConfig(inverter_model="goodwe")
    collector = SimulationCollector(config)
    result = collector.poll()
    goodwe_only = SIM_PROFILES["goodwe"]["metrics"]
    for m in result:
        if m == "timestamp":
            continue
        assert m in goodwe_only, f"unexpected metric: {m}"


def test_simulation_huawei_no_load_power():
    config = MockConfig(inverter_model="huawei")
    collector = SimulationCollector(config)
    result = collector.poll()
    assert "load_power" not in result


def test_simulation_sunsynk_has_sub_mppts():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    result = collector.poll()
    assert "pv_power_1" in result
    assert "pv_power_2" in result
    assert "pv_power_3" in result
    assert "pv_current" in result
    assert "load_power_essential" in result
    assert "battery_temperature" in result


def test_simulation_all_values_numeric():
    for profile in ["goodwe", "huawei", "sunsynk"]:
        config = MockConfig(inverter_model=profile)
        collector = SimulationCollector(config)
        for _ in range(10):
            result = collector.poll()
            for key, val in result.items():
                if key == "timestamp":
                    assert isinstance(val, int), f"{profile}/{key} is not int: {type(val)}"
                else:
                    assert isinstance(val, (int, float)), f"{profile}/{key} is {type(val)}: {val!r}"


def test_simulation_energy_non_negative():
    for profile in ["goodwe", "huawei", "sunsynk"]:
        config = MockConfig(inverter_model=profile)
        collector = SimulationCollector(config)
        for _ in range(10):
            result = collector.poll()
            for key in result:
                if "energy" in key or "today" in key:
                    assert result[key] >= 0, f"{profile}/{key} = {result[key]}"


def test_simulation_pv_power_consistent():
    """pv_power >= each individual MPPT sub-power."""
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    for _ in range(10):
        result = collector.poll()
        total = result.get("pv_power", 0)
        for i in (1, 2, 3):
            sub = result.get(f"pv_power_{i}", 0)
            assert total >= sub - 1, f"pv_power {total} < pv_power_{i} {sub}"


def test_simulation_load_power_breakdown():
    """load_power = load_power_essential + load_power_non_essential (within rounding)."""
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    for _ in range(10):
        result = collector.poll()
        total = result.get("load_power", 0)
        essential = result.get("load_power_essential", 0)
        non_essential = result.get("load_power_non_essential", 0)
        assert abs(total - (essential + non_essential)) < 1, (
            f"load_power {total} != {essential} + {non_essential}"
        )


def test_simulation_nighttime_pv():
    """When the simulation starts, elapsed time ~0, so daylight = 0 and pv should be near-zero."""
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    pvs = [collector.poll()["pv_power"] for _ in range(20)]
    avg = sum(pvs) / len(pvs)
    assert avg < 150, f"Expected near-zero pv at startup, average over 20 polls: {avg}"


def test_simulation_profile_metrics_subset_of_definitions():
    from collectors.base import metric_definitions
    defined_names = {m["name"] for m in metric_definitions}
    for profile in SIM_PROFILES:
        unknown = SIM_PROFILES[profile]["metrics"] - defined_names
        assert not unknown, f"{profile} has undefined metrics: {unknown}"


def test_simulation_get_metric_definitions():
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    defs = collector.get_metric_definitions()
    names = {d["name"] for d in defs}
    assert names == SIM_PROFILES["sunsynk"]["metrics"]


def test_simulation_each_profile_no_extra_metrics():
    for profile in SIM_PROFILES:
        config = MockConfig(inverter_model=profile)
        collector = SimulationCollector(config)
        result = collector.poll()
        expected = SIM_PROFILES[profile]["metrics"]
        for m in result:
            if m == "timestamp":
                continue
            assert m in expected, f"{profile}: unexpected metric {m}"


def test_simulation_battery_soc_never_out_of_range():
    for profile in ["goodwe", "huawei", "sunsynk"]:
        config = MockConfig(inverter_model=profile)
        collector = SimulationCollector(config)
        for _ in range(50):
            result = collector.poll()
            if "battery_soc" in result:
                assert 0 <= result["battery_soc"] <= 100, f"{profile}: soc {result['battery_soc']}"


def test_simulation_temperature_sane():
    """Inverter temp should never exceed 120°C, battery temp never exceed 60°C."""
    config = MockConfig(inverter_model="sunsynk")
    collector = SimulationCollector(config)
    for _ in range(50):
        result = collector.poll()
        assert 0 <= result.get("inverter_temp", 0) <= 120
        assert 0 <= result.get("battery_temperature", 0) <= 60
