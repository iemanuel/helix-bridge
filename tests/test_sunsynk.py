from unittest.mock import patch, MagicMock
from tests.conftest import MockConfig
from collectors.sunsynk import SunsynkCollector, _import_defs, SUNSUNK_TO_METRIC


def _make_mock_client(batch_result: dict):
    """Return a mock modbus client that returns predefined batch results."""
    client = MagicMock()
    client.read_batch.return_value = batch_result
    return client


def _raw_vals_for_sensor(sensor, *values):
    """Build raw register entries as our batch reader returns them.

    Returns {sid_0: val0, sid_1: val1, ...}
    """
    out = {}
    for offset, v in enumerate(values):
        key = f"{sensor.id}_{offset}"
        out[key] = v
    return out


class TestSunsynkThreePhase:
    """Tests against the three_phase_lv sensor definitions."""

    def _build_collector(self, model="three_phase_lv"):
        cfg = MockConfig(
            inverter_modbus_host="192.168.1.70",
            inverter_modbus_port=502,
            inverter_model=model,
        )
        col = SunsynkCollector(cfg)
        return col

    def _make_raw_data(self):
        defs = _import_defs("three_phase_lv")
        raw = {}

        sensors = {
            "pv1_power": [500], "pv2_power": [300], "pv3_power": [200],
            "pv1_voltage": [3600], "pv2_voltage": [3580], "pv3_voltage": [3550],
            "pv1_current": [70], "pv2_current": [50], "pv3_current": [30],
            "grid_power": [50000, 0],
            "grid_frequency": [5001],
            "load_power": [45000, 0],
            "battery_power": [500],
            "battery_soc": [75],
            "battery_voltage": [4800],
            "battery_current": [100],
            "battery_temperature": [250],
            "radiator_temperature": [1350],
            "day_pv_energy": [153], "day_load_energy": [87],
            "day_grid_import": [42], "day_grid_export": [61],
            "inverter_l1_voltage": [2300],
        }

        for sid, regs in sensors.items():
            s = defs.get(sid)
            if s:
                raw.update(_raw_vals_for_sensor(s, *regs))
            else:
                from collectors.sunsynk import SUNSUNK_ALIASES
                for alias in SUNSUNK_ALIASES.get(sid, []):
                    s2 = defs.get(alias)
                    if s2:
                        raw.update(_raw_vals_for_sensor(s2, *regs))
                        break
        return raw

    def test_poll_returns_dict(self):
        collector = self._build_collector()
        collector._client = _make_mock_client(self._make_raw_data())
        result = collector.poll()
        assert result is not None
        assert isinstance(result, dict)
        assert "timestamp" in result

    def test_poll_expected_metrics(self):
        collector = self._build_collector()
        collector._client = _make_mock_client(self._make_raw_data())
        result = collector.poll()
        for m in SunsynkCollector.METRICS:
            assert m in result, f"Missing metric: {m}"

    def test_poll_values(self):
        collector = self._build_collector()
        collector._client = _make_mock_client(self._make_raw_data())
        result = collector.poll()

        assert result["pv_power"] == 1000.0
        assert result["pv_power_1"] == 500.0
        assert result["pv_power_2"] == 300.0
        assert result["pv_power_3"] == 200.0
        assert result["pv_voltage"] == 360.0
        assert result["pv_voltage_1"] == 360.0
        assert result["pv_voltage_2"] == 358.0
        assert result["pv_voltage_3"] == 355.0
        assert result["grid_frequency"] == 50.01
        assert result["battery_soc"] == 75.0
        assert result["battery_voltage"] == 48.0
        assert result["inverter_temp"] == 35.0
        assert result["pv_energy_today"] == 15.3
        assert result["load_energy_today"] == 8.7
        assert result["grid_energy_import_today"] == 4.2
        assert result["grid_energy_export_today"] == 6.1

    def test_poll_read_failure(self):
        collector = self._build_collector()
        collector._client = _make_mock_client({})
        result = collector.poll()
        assert result is None

    def test_metric_definitions(self):
        collector = self._build_collector()
        defs = collector.get_metric_definitions()
        names = {d["name"] for d in defs}
        assert names == SunsynkCollector.METRICS

    def test_sensor_id_resolution(self):
        collector = self._build_collector()
        assert collector._resolve_sensor_id("battery_soc") == "battery_soc"
        resolved = collector._resolve_sensor_id("grid_voltage")
        assert resolved == "grid_l1_voltage"

    def test_write_register(self):
        collector = self._build_collector()
        collector._client = _make_mock_client({})
        collector._client.write_single_register.return_value = True
        assert collector.write_register(100, 50) is True
        collector._client.write_single_register.assert_called_once_with(100, 50)

    def test_unknown_model_falls_back(self):
        cfg = MockConfig(
            inverter_modbus_host="192.168.1.70",
            inverter_model="unknown-model",
        )
        col = SunsynkCollector(cfg)
        assert len(col._sensor_defs) > 0


class TestSunsynkSinglePhase:
    """Tests against the single-phase sensor definitions."""

    def _build_collector(self):
        cfg = MockConfig(
            inverter_modbus_host="192.168.1.70",
            inverter_model="single-phase",
        )
        return SunsynkCollector(cfg)

    def _make_raw_data(self):
        defs = _import_defs("single-phase")
        raw = {}

        sensors = {
            "pv1_power": [2500], "pv2_power": [1500],
            "pv1_voltage": [3600], "pv2_voltage": [3580],
            "pv1_current": [70], "pv2_current": [42],
            "grid_power": [50000],
            "grid_voltage": [2300],
            "grid_frequency": [5001],
            "load_power": [30000],
            "battery_power": [800],
            "battery_soc": [80],
            "battery_voltage": [4850],
            "battery_current": [165],
            "battery_temperature": [230],
            "radiator_temperature": [1350],
            "day_pv_energy": [200],
            "day_load_energy": [120],
            "day_grid_import": [30],
            "day_grid_export": [90],
        }

        for sid, regs in sensors.items():
            s = defs.get(sid)
            if s:
                raw.update(_raw_vals_for_sensor(s, *regs))
        return raw

    def test_poll_expected_metrics(self):
        collector = self._build_collector()
        collector._client = _make_mock_client(self._make_raw_data())
        result = collector.poll()
        for m in SunsynkCollector.METRICS:
            assert m in result, f"Missing metric: {m}"

    def test_poll_values_single_phase(self):
        collector = self._build_collector()
        collector._client = _make_mock_client(self._make_raw_data())
        result = collector.poll()

        assert result["pv_power_1"] == 2500.0
        assert result["pv_power_2"] == 1500.0
        assert result["grid_frequency"] == 50.01
        assert result["battery_soc"] == 80.0
        assert result["pv_energy_today"] == 20.0

    def test_sensor_id_direct_resolution(self):
        collector = self._build_collector()
        assert collector._resolve_sensor_id("grid_voltage") == "grid_voltage"


def test_import_defs_all_models():
    for model in ["single-phase", "three_phase_lv", "three_phase_hv"]:
        defs = _import_defs(model)
        assert len(defs) > 0, f"Empty defs for {model}"


def test_sunsunk_to_metric_coverage():
    """All sensors in SUNSUNK_TO_METRIC should exist in at least one def set."""
    defs3 = _import_defs("three_phase_lv")
    defs1 = _import_defs("single-phase")

    from collectors.sunsynk import SUNSUNK_ALIASES

    for sid in SUNSUNK_TO_METRIC:
        in_3 = sid in defs3
        in_1 = sid in defs1
        aliases = SUNSUNK_ALIASES.get(sid, [])
        alias_ok = any(a in defs3 or a in defs1 for a in aliases)
        assert in_3 or in_1 or alias_ok, f"{sid} not found in any definition set"


def test_sunsynk_zero_values():
    """All sensors reading zero should produce zeroes (or offset), not crash.

    TempSensor with an offset (e.g. battery_temperature offset=100) will
    return -100 even from zero raw — that is expected behaviour.
    """
    collector = TestSunsynkThreePhase()._build_collector()
    defs = _import_defs("three_phase_lv")
    raw = {}
    for sid in defs:
        raw.update(_raw_vals_for_sensor(defs[sid], *([0] * len(defs[sid].address))))
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result is not None
    for key in SunsynkCollector.METRICS:
        v = result.get(key)
        ok = v == 0.0 or v == 0
        if not ok:
            # TempSensor offsets produce non-zero from zero raw — acceptable.
            if key in ("battery_temperature", "inverter_temp"):
                continue
        assert ok, f"{key} = {v}"


def test_sunsynk_negative_grid_export():
    """Negative grid_power means export to grid.

    Modbus registers are unsigned 16-bit; a signed 32-bit value like -30000
    is encoded as two little-endian words: [(-30000 & 0xFFFF), 0xFFFF].
    """
    collector = TestSunsynkThreePhase()._build_collector()
    defs = _import_defs("three_phase_lv")
    s = defs["grid_power"]
    raw = _raw_vals_for_sensor(s, 35536, 65535)  # -30000 in LE 32-bit
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result is not None
    assert result["grid_power"] == -30000.0


def test_sunsynk_negative_battery_discharge():
    """Negative battery_power means discharging.

    -2000 in signed 16-bit = 0xF830 = 63536 unsigned.
    """
    collector = TestSunsynkThreePhase()._build_collector()
    defs = _import_defs("three_phase_lv")
    s = defs["battery_power"]
    raw = _raw_vals_for_sensor(s, 63536)  # -2000 in signed 16-bit
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result is not None
    assert result["battery_power"] == -2000.0


def test_sunsynk_ac_couple_pv_zero():
    """By default AC couple PV power should be zero."""
    collector = TestSunsynkThreePhase()._build_collector()
    raw = TestSunsynkThreePhase()._make_raw_data()
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result["ac_couple_pv_power"] == 0.0


def test_sunsynk_generator_mostly_off():
    """Generator should be zero unless configured."""
    collector = TestSunsynkThreePhase()._build_collector()
    raw = TestSunsynkThreePhase()._make_raw_data()
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result["generator_power"] == 0.0


def test_sunsynk_single_phase_only_two_mppts():
    """Single-phase definitions have only 2 MPPTs (pv1, pv2)."""
    collector = TestSunsynkSinglePhase()._build_collector()
    raw = TestSunsynkSinglePhase()._make_raw_data()
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result["pv_power_1"] == 2500.0
    assert result["pv_power_2"] == 1500.0
    assert result["pv_power_3"] == 0.0
    assert result["pv_voltage_3"] == 0.0


def test_sunsynk_partial_battery_only():
    """Only battery sensors available, everything else should zero out."""
    collector = TestSunsynkThreePhase()._build_collector()
    defs = _import_defs("three_phase_lv")
    raw = {}
    for sid in ["battery_soc", "battery_voltage", "battery_current",
                 "battery_power", "battery_temperature"]:
        raw.update(_raw_vals_for_sensor(defs[sid], *([0] * len(defs[sid].address))))
    collector._client = _make_mock_client(raw)
    result = collector.poll()
    assert result is not None
    assert result["battery_soc"] == 0.0
    assert result["battery_voltage"] == 0.0
