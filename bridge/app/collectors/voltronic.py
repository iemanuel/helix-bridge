import logging
import serial
import time
import re

from .base import BaseCollector

log = logging.getLogger("bridge.collector.voltronic")

QPIGS_RESPONSE = re.compile(
    r"^\((\d{4})\s+"      # grid voltage (0.1V)
    r"(\d{4})\s+"          # grid frequency (0.01Hz)
    r"(\d{4})\s+"          # AC output voltage (0.1V)
    r"(\d{4})\s+"          # AC output frequency (0.01Hz)
    r"(\d{4})\s+"          # AC output apparent power (VA)
    r"(\d{4})\s+"          # AC output active power (W)
    r"(\d{3})\s+"          # output load percent (%)
    r"(\d{4})\s+"          # bus voltage (0.1V)
    r"(\d{4})\s+"          # battery voltage (0.01V)
    r"(\d{4})\s+"          # battery charging current (0.1A)
    r"(\d{4})\s+"          # battery discharging current (0.1A)
    r"(\d{4})\s+"          # battery capacity (%)
    r"(\d{4})\s+"          # inverter heat sink temperature (0.1C)
    r"(\d{4})\s+"          # PV input current (0.1A)
    r"(\d{4})\s+"          # PV input voltage (0.1V)
    r"(\d{1})\s+"          # battery type
    r"(\d{1})\s+"          # battery recharge voltage
    r"(\d{1})\s+"          # battery under voltage
    r"(\d{1})\s+"          # battery bulk voltage
    r"(\d{1})\s+"          # battery float voltage
    r"(\d{1})\s+"          # battery type select
    r"(\d{4})\s+"          # max charging current
    r"(\d{4})\s+"          # max discharging current
    r"(\d{2})\s+"          # charging source priority
    r"(\d{2})\s+"          # max charger time
    r"(\d{4})\s+"          # max charging time out
    r"(\d{4})\s+"          # PV power (W)
    r"(\w+)\s*"            # device status flags
    r"(\w*)\)"             # checksum
)

QPIGS2_RESPONSE = re.compile(
    r"^\((\d{4})\s+"      # PV1 power (W)
    r"(\d{4})\s+"          # PV2 power (W)
    r"(\d{4})\s+"          # PV1 voltage (0.1V)
    r"(\d{4})\s+"          # PV2 voltage (0.1V)
    r"(\w+)\s*"            # checksum
    r"(\w*)\)"
)

QMOD_RESPONSE = re.compile(r"^\((\w+)\)")


class VoltronicCollector(BaseCollector):
    METRICS = {
        "pv_power", "pv_voltage", "grid_voltage", "grid_frequency",
        "battery_voltage", "battery_soc", "inverter_temp",
        "load_power", "battery_power", "grid_power",
    }

    def __init__(self, device: str, baud: int = 2400):
        super().__init__()
        self._device = device
        self._baud = baud
        self._ser = None

    def _connect(self):
        try:
            self._ser = serial.Serial(
                port=self._device,
                baudrate=self._baud,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=2,
            )
            log.info("connected to voltronic on %s at %d baud", self._device, self._baud)
            return True
        except Exception as e:
            log.error("voltronic connect failed: %s", e)
            return False

    def _command(self, cmd: str) -> str | None:
        if self._ser is None:
            if not self._connect():
                return None
        try:
            self._ser.write((cmd + "\r\n").encode())
            self._ser.flush()
            line = self._ser.readline().decode("ascii", errors="ignore").strip()
            return line if line else None
        except Exception as e:
            log.error("voltronic cmd error: %s", e)
            self._ser = None
            return None

    def poll(self) -> dict | None:
        ts = int(time.time() * 1000)
        result = {"timestamp": ts}

        qpigs = self._command("QPIGS")
        if qpigs:
            m = QPIGS_RESPONSE.match(qpigs)
            if m:
                result["grid_voltage"] = round(int(m.group(1)) * 0.1, 1)
                result["grid_frequency"] = round(int(m.group(2)) * 0.01, 2)
                result["battery_voltage"] = round(int(m.group(9)) * 0.01, 2)
                result["battery_soc"] = round(int(m.group(12)), 1)
                result["inverter_temp"] = round(int(m.group(13)) * 0.1, 1)

                pv_voltage = int(m.group(15)) * 0.1
                pv_current = int(m.group(14)) * 0.1
                result["pv_voltage"] = round(pv_voltage, 1)
                result["pv_power"] = round(pv_voltage * pv_current, 1)

                pv_power = int(m.group(27))
                if pv_power > 0:
                    result["pv_power"] = round(pv_power, 1)

                load_power = int(m.group(6))
                result["load_power"] = round(load_power, 1)

                bat_charge_current = int(m.group(10)) * 0.1
                bat_discharge_current = int(m.group(11)) * 0.1
                bat_power = (bat_charge_current - bat_discharge_current) * (result["battery_voltage"])
                result["battery_power"] = round(bat_power, 1)

                solar_power = result.get("pv_power", 0)
                grid_power = load_power - solar_power + bat_power
                result["grid_power"] = round(grid_power, 1)

        qpigs2 = self._command("QPIGS2")
        if qpigs2:
            m = QPIGS2_RESPONSE.match(qpigs2)
            if m:
                pv1 = int(m.group(1))
                pv2 = int(m.group(2))
                total_pv = pv1 + pv2
                if total_pv > 0:
                    result["pv_power"] = round(total_pv, 1)

        if len(result) <= 1:
            return None

        return result
