import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bridge", "app"))


class MockConfig:
    """Minimal config stub for testing collectors."""

    def __init__(self, **kwargs):
        self.inverter_type = "simulation"
        self.inverter_device = ""
        self.inverter_model = ""
        self.inverter_baud = 19200
        self.inverter_modbus_port = 502
        self.inverter_modbus_host = "192.168.1.100"
        self.inverter_modbus_address = 1
        self.inverter_modbus_timeout = 5
        self.inverter_solarman = False
        self.inverter_logger_sn = 0
        self.poll_interval = 5
        for k, v in kwargs.items():
            setattr(self, k, v)
