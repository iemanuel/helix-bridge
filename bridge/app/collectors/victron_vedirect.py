import logging
import serial
import time
import re

from .base import BaseCollector

log = logging.getLogger("bridge.collector.victron")


class VictronVEDirectCollector(BaseCollector):
    METRICS = {"pv_power", "battery_power", "battery_soc", "battery_voltage", "load_power"}
    VE_PATTERN = re.compile(r"^(\w+)\t(.+)$")

    def __init__(self, device: str, baud: int = 19200):
        super().__init__()
        self._device = device
        self._baud = baud
        self._ser = None
        self._last_data = {}

    def connect(self):
        try:
            self._ser = serial.Serial(
                port=self._device,
                baudrate=self._baud,
                timeout=3,
            )
            log.info("connected to victron device on %s", self._device)
            return True
        except Exception as e:
            log.error("victron connect failed: %s", e)
            return False

    def poll(self) -> dict | None:
        if self._ser is None:
            if not self.connect():
                return None

        try:
            data = self._read_frame()
            if data:
                self._last_data = data
                return self._map_to_metrics(data)
            return self._map_to_metrics(self._last_data) if self._last_data else None
        except Exception as e:
            log.error("victron read error: %s", e)
            self._ser = None
            return None

    def _read_frame(self) -> dict | None:
        frame = {}
        while True:
            line = self._ser.readline().decode("ascii", errors="ignore").strip()
            if line == "Checksum\t":
                continue
            if line.startswith("PID\t") or line.startswith("FW\t") or line.startswith("SER#"):
                continue
            m = self.VE_PATTERN.match(line)
            if m:
                key, value = m.group(1), m.group(2)
                frame[key] = value
            if line == "" and frame:
                break
            if "Checksum" in line:
                break
        return frame if frame else None

    def _map_to_metrics(self, data: dict) -> dict:
        ts = int(time.time() * 1000)

        def _float(key, default=0):
            try:
                return float(data.get(key, default))
            except (ValueError, TypeError):
                return default

        bat_voltage = _float("V")

        pv_power = _float("PPV")
        if pv_power == 0:
            bat_current = _float("I")
            if bat_current > 0:
                pv_power = bat_voltage * bat_current

        bat_power = _float("P")
        soc = _float("SOC")
        load_current = _float("LOAD")
        load_power = load_current * bat_voltage if load_current > 0 else 0

        return {
            "timestamp": ts,
            "pv_power": round(pv_power, 1),
            "battery_power": round(-bat_power if bat_power > 0 else abs(bat_power), 1),
            "battery_soc": round(soc, 1),
            "battery_voltage": round(bat_voltage, 2),
            "load_power": round(load_power, 1),
        }
