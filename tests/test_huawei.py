from unittest.mock import patch, MagicMock, AsyncMock
from tests.conftest import MockConfig
from collectors.huawei import HuaweiCollector
from huawei_solar.register_names import (
    INPUT_POWER, ACTIVE_POWER, GRID_FREQUENCY, PHASE_A_VOLTAGE,
    DAILY_YIELD_ENERGY, GRID_EXPORTED_ENERGY, GRID_ACCUMULATED_ENERGY,
    INTERNAL_TEMPERATURE, PV_01_VOLTAGE,
    STORAGE_UNIT_1_STATE_OF_CAPACITY,
    STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER,
    STORAGE_UNIT_1_BUS_VOLTAGE,
)


def _make_result(value, unit=""):
    """Build a minimal Result-like object."""
    from huawei_solar.register_definitions.base import Result
    return Result(value=value, unit=unit)


def _fake_results():
    return {
        INPUT_POWER: _make_result(4500.0, "W"),
        ACTIVE_POWER: _make_result(-1200.0, "W"),
        GRID_FREQUENCY: _make_result(50.01, "Hz"),
        PHASE_A_VOLTAGE: _make_result(231.2, "V"),
        DAILY_YIELD_ENERGY: _make_result(15.3, "kWh"),
        GRID_EXPORTED_ENERGY: _make_result(6.1, "kWh"),
        GRID_ACCUMULATED_ENERGY: _make_result(-4.2, "kWh"),
        INTERNAL_TEMPERATURE: _make_result(38.5, "°C"),
        PV_01_VOLTAGE: _make_result(362.0, "V"),
        STORAGE_UNIT_1_STATE_OF_CAPACITY: _make_result(68.0, "%"),
        STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER: _make_result(500.0, "W"),
        STORAGE_UNIT_1_BUS_VOLTAGE: _make_result(49.2, "V"),
    }


class FakeClient:
    def __init__(self):
        pass

    async def stop(self):
        pass


class FakeDevice:
    def __init__(self):
        self._results = _fake_results()

    async def batch_update(self, register_names):
        return {
            name: self._results.get(name, _make_result(0))
            for name in register_names
        }


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_poll_returns_dict(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    mock_create_dev.return_value = FakeDevice()

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result is not None
    assert isinstance(result, dict)
    assert "timestamp" in result


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_poll_expected_metrics(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    mock_create_dev.return_value = FakeDevice()

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    expected = {
        "pv_power", "grid_power", "grid_frequency", "grid_voltage",
        "pv_voltage", "inverter_temp",
        "pv_energy_today", "grid_energy_import_today", "grid_energy_export_today",
        "battery_soc", "battery_power", "battery_voltage",
    }
    assert expected.issubset(result.keys()), f"Missing: {expected - result.keys()}"


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_poll_values(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    mock_create_dev.return_value = FakeDevice()

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result["pv_power"] == 4500.0
    assert result["grid_power"] == -1200.0
    assert result["grid_frequency"] == 50.01
    assert result["grid_voltage"] == 231.2
    assert result["pv_voltage"] == 362.0
    assert result["inverter_temp"] == 38.5
    assert result["pv_energy_today"] == 15.3
    assert result["grid_energy_export_today"] == 6.1
    assert result["grid_energy_import_today"] == 4.2
    assert result["battery_soc"] == 68.0
    assert result["battery_power"] == 500.0
    assert result["battery_voltage"] == 49.2


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_poll_error(mock_create_dev, mock_create_tcp):
    mock_create_tcp.side_effect = RuntimeError("timeout")

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result is None


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_metric_definitions(mock_create_dev, mock_create_tcp):
    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    defs = collector.get_metric_definitions()
    names = {d["name"] for d in defs}
    assert names == HuaweiCollector.METRICS


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_empty_results(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    dev = FakeDevice()
    dev._results = {}
    mock_create_dev.return_value = dev

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result is not None
    for key in HuaweiCollector.METRICS:
        assert key in result
        assert result[key] == 0.0 or result[key] == 0


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_negative_values(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    dev = FakeDevice()
    dev._results = {
        INPUT_POWER: _make_result(5000.0, "W"),
        ACTIVE_POWER: _make_result(-3000.0, "W"),
        GRID_FREQUENCY: _make_result(50.02, "Hz"),
        PHASE_A_VOLTAGE: _make_result(230.0, "V"),
        DAILY_YIELD_ENERGY: _make_result(20.5, "kWh"),
        GRID_EXPORTED_ENERGY: _make_result(12.3, "kWh"),
        GRID_ACCUMULATED_ENERGY: _make_result(-8.1, "kWh"),
        INTERNAL_TEMPERATURE: _make_result(42.0, "°C"),
        PV_01_VOLTAGE: _make_result(370.0, "V"),
        STORAGE_UNIT_1_STATE_OF_CAPACITY: _make_result(55.0, "%"),
        STORAGE_UNIT_1_CHARGE_DISCHARGE_POWER: _make_result(-1500.0, "W"),
        STORAGE_UNIT_1_BUS_VOLTAGE: _make_result(50.1, "V"),
    }
    mock_create_dev.return_value = dev

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result is not None
    assert result["grid_power"] == -3000.0
    assert result["battery_power"] == -1500.0
    assert result["grid_energy_import_today"] == 8.1
    assert result["grid_energy_export_today"] == 12.3


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_no_battery(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    dev = FakeDevice()
    dev._results = {
        INPUT_POWER: _make_result(3200.0, "W"),
        ACTIVE_POWER: _make_result(-500.0, "W"),
        GRID_FREQUENCY: _make_result(50.01, "Hz"),
        PHASE_A_VOLTAGE: _make_result(229.5, "V"),
        DAILY_YIELD_ENERGY: _make_result(10.1, "kWh"),
        GRID_EXPORTED_ENERGY: _make_result(4.2, "kWh"),
        GRID_ACCUMULATED_ENERGY: _make_result(-0.5, "kWh"),
        INTERNAL_TEMPERATURE: _make_result(36.0, "°C"),
        PV_01_VOLTAGE: _make_result(355.0, "V"),
    }
    mock_create_dev.return_value = dev

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    assert result is not None
    assert result["pv_power"] == 3200.0
    assert result["battery_soc"] == 0.0
    assert result["battery_power"] == 0.0
    assert result["battery_voltage"] == 0.0


@patch("huawei_solar.create_tcp_client", new_callable=AsyncMock)
@patch("huawei_solar.create_device_instance", new_callable=AsyncMock)
def test_huawei_no_extra_metrics(mock_create_dev, mock_create_tcp):
    mock_create_tcp.return_value = FakeClient()
    mock_create_dev.return_value = FakeDevice()

    config = MockConfig(inverter_modbus_host="192.168.1.60")
    collector = HuaweiCollector(config)
    result = collector.poll()

    for m in result:
        if m == "timestamp":
            continue
        assert m in HuaweiCollector.METRICS, f"unexpected metric: {m}"
