from unittest.mock import patch, MagicMock
from tests.conftest import MockConfig
from collectors.goodwe import GoodweCollector


class FakeGoodweInverter:
    """Simulates a goodwe Inverter returned by connect()."""

    async def read_runtime_data(self):
        return {
            "ppv": 5200,
            "ppv1": 2600,
            "ppv2": 2600,
            "ppv3": 0,
            "ppv4": 0,
            "vpv1": 360.5,
            "vpv2": 358.2,
            "ipv1": 7.2,
            "ipv2": 7.3,
            "pgrid": -1500,
            "vgrid": 230.1,
            "fgrid": 50.02,
            "load_ptotal": 3200,
            "pbattery1": 800,
            "vbattery1": 48.5,
            "battery_soc": 75,
            "temperature": 42.3,
            "e_day": 12.5,
            "e_day_exp": 5.2,
            "e_day_imp": 3.1,
            "e_load_day": 8.7,
        }


class FakeGoodweInverterNoBattery:
    async def read_runtime_data(self):
        return {
            "ppv": 3200,
            "ppv1": 1600,
            "ppv2": 1600,
            "vpv1": 340.0,
            "vpv2": 338.5,
            "pgrid": -500,
            "vgrid": 229.8,
            "fgrid": 50.01,
            "load_ptotal": 2700,
            "temperature": 38.1,
            "e_day": 8.2,
            "e_day_exp": 2.1,
            "e_day_imp": 0.5,
            "e_load_day": 6.0,
        }


async def _mock_goodwe_connect(host, port=8899, **_):
    return FakeGoodweInverter()


async def _mock_goodwe_connect_no_battery(host, port=8899, **_):
    return FakeGoodweInverterNoBattery()


@patch("goodwe.connect", side_effect=_mock_goodwe_connect)
def test_goodwe_poll_returns_dict(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50", inverter_modbus_port=8899)
    collector = GoodweCollector(config)
    result = collector.poll()

    assert result is not None
    assert isinstance(result, dict)
    assert "timestamp" in result


@patch("goodwe.connect", side_effect=_mock_goodwe_connect)
def test_goodwe_poll_expected_metrics(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()

    expected = {
        "pv_power", "grid_power", "battery_power", "load_power",
        "battery_soc", "battery_voltage",
        "grid_voltage", "grid_frequency", "pv_voltage", "inverter_temp",
        "pv_energy_today", "load_energy_today",
        "grid_energy_import_today", "grid_energy_export_today",
    }
    assert expected.issubset(result.keys()), f"Missing: {expected - result.keys()}"


@patch("goodwe.connect", side_effect=_mock_goodwe_connect)
def test_goodwe_poll_values(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()

    assert result["pv_power"] == 5200.0
    assert result["grid_power"] == -1500.0
    assert result["battery_power"] == 800.0
    assert result["load_power"] == 3200.0
    assert result["battery_soc"] == 75.0
    assert result["battery_voltage"] == 48.5
    assert result["grid_voltage"] == 230.1
    assert result["grid_frequency"] == 50.02
    assert result["pv_voltage"] == 360.5
    assert result["inverter_temp"] == 42.3
    assert result["pv_energy_today"] == 12.5
    assert result["load_energy_today"] == 8.7
    assert result["grid_energy_import_today"] == 3.1
    assert result["grid_energy_export_today"] == 5.2


@patch("goodwe.connect", side_effect=_mock_goodwe_connect_no_battery)
def test_goodwe_no_battery(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()

    assert result is not None
    assert result["pv_power"] == 3200.0
    assert result["battery_soc"] == 0.0
    assert result["battery_power"] == 0.0


@patch("goodwe.connect", side_effect=Exception("connection refused"))
def test_goodwe_connection_error(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.99")
    collector = GoodweCollector(config)
    result = collector.poll()

    assert result is None


@patch("goodwe.connect", side_effect=_mock_goodwe_connect)
def test_goodwe_metric_definitions(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    defs = collector.get_metric_definitions()

    names = {d["name"] for d in defs}
    assert names == GoodweCollector.METRICS


def test_goodwe_write_register_not_supported():
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    assert collector.write_register(1, 1000) is False


class FakeGoodweInverterZero:
    async def read_runtime_data(self):
        return {}


async def _mock_goodwe_connect_zero(host, port=8899, **_):
    return FakeGoodweInverterZero()


@patch("goodwe.connect", side_effect=_mock_goodwe_connect_zero)
def test_goodwe_empty_data(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()
    assert result is not None
    assert result["pv_power"] == 0.0
    assert result["grid_power"] == 0.0
    assert result["battery_power"] == 0.0
    assert result["battery_soc"] == 0.0


class FakeGoodweInverterHigh:
    async def read_runtime_data(self):
        return {
            "ppv": 15000,
            "ppv1": 7600,
            "ppv2": 7400,
            "vpv1": 400.0,
            "vpv2": 395.0,
            "pgrid": -8000,
            "vgrid": 253.0,
            "fgrid": 50.98,
            "load_ptotal": 6000,
            "pbattery1": 3000,
            "vbattery1": 56.0,
            "battery_soc": 98,
            "temperature": 55.0,
            "e_day": 45.2,
            "e_day_exp": 22.1,
            "e_day_imp": 0.0,
            "e_load_day": 18.5,
        }


async def _mock_goodwe_connect_high(host, port=8899, **_):
    return FakeGoodweInverterHigh()


@patch("goodwe.connect", side_effect=_mock_goodwe_connect_high)
def test_goodwe_high_values(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()
    assert result["pv_power"] == 15000.0
    assert result["grid_power"] == -8000.0
    assert result["battery_power"] == 3000.0
    assert result["battery_soc"] == 98.0
    assert result["battery_voltage"] == 56.0
    assert result["grid_voltage"] == 253.0
    assert result["grid_frequency"] == 50.98
    assert result["inverter_temp"] == 55.0
    assert result["pv_voltage"] == 400.0
    assert result["grid_energy_import_today"] == 0.0


@patch("goodwe.connect", side_effect=_mock_goodwe_connect)
def test_goodwe_no_extra_metrics(mock_connect):
    config = MockConfig(inverter_modbus_host="192.168.1.50")
    collector = GoodweCollector(config)
    result = collector.poll()
    for m in result:
        if m == "timestamp":
            continue
        assert m in GoodweCollector.METRICS, f"unexpected metric: {m}"
