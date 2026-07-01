import os
import logging
import yaml

log = logging.getLogger("bridge.config")


class Config:
    def __init__(self):
        self.bridge_name = "helix-bridge"
        self.log_level = "info"
        self.poll_interval = 5

        self.inverter_type = "simulation"
        self.inverter_device = ""
        self.inverter_model = ""
        self.inverter_baud = 19200
        self.inverter_modbus_port = 502
        self.inverter_modbus_host = ""
        self.inverter_modbus_address = 1
        self.inverter_modbus_timeout = 5
        self.inverter_solarman = False
        self.inverter_logger_sn = 0

        self.mqtt_enabled = True
        self.mqtt_host = "mqtt"
        self.mqtt_port = 1883
        self.mqtt_username = ""
        self.mqtt_password = ""
        self.mqtt_topic_prefix = "helix_bridge"
        self.mqtt_ha_discovery = True
        self.mqtt_ha_discovery_prefix = "homeassistant"

        self.metric_defs = []

    def load(self):
        path = os.environ.get("BRIDGE_CONFIG", "/config/config.yaml")
        if os.path.exists(path):
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}

            b = cfg.get("bridge", {})
            self.bridge_name = b.get("name", self.bridge_name)
            self.log_level = b.get("log_level", self.log_level)
            self.poll_interval = b.get("poll_interval", self.poll_interval)

            inv = cfg.get("inverter", {})
            self.inverter_type = inv.get("type", self.inverter_type)
            self.inverter_device = inv.get("device", self.inverter_device)
            self.inverter_model = inv.get("model", self.inverter_model)
            self.inverter_baud = inv.get("baud_rate", self.inverter_baud)
            self.inverter_modbus_port = inv.get("modbus_port", self.inverter_modbus_port)
            self.inverter_modbus_host = inv.get("modbus_host", self.inverter_modbus_host)
            self.inverter_modbus_address = inv.get("modbus_address", self.inverter_modbus_address)
            self.inverter_modbus_timeout = inv.get("modbus_timeout", self.inverter_modbus_timeout)
            self.inverter_solarman = inv.get("solarman", self.inverter_solarman)
            self.inverter_logger_sn = inv.get("logger_sn", self.inverter_logger_sn)

            mq = cfg.get("mqtt", {})
            self.mqtt_enabled = mq.get("enabled", self.mqtt_enabled)
            self.mqtt_host = mq.get("host", self.mqtt_host)
            self.mqtt_port = mq.get("port", self.mqtt_port)
            self.mqtt_username = mq.get("username", self.mqtt_username) or ""
            self.mqtt_password = mq.get("password", self.mqtt_password) or ""
            self.mqtt_topic_prefix = mq.get("topic_prefix", self.mqtt_topic_prefix)
            self.mqtt_ha_discovery = mq.get("ha_discovery", self.mqtt_ha_discovery)
            self.mqtt_ha_discovery_prefix = mq.get("ha_discovery_prefix", self.mqtt_ha_discovery_prefix)

            self.metric_defs = cfg.get("metrics", self.metric_defs)

        self._override_from_env()

    def _override_from_env(self):
        overrides = {
            "BRIDGE_LOG_LEVEL": ("log_level", str),
            "BRIDGE_POLL_INTERVAL": ("poll_interval", int),
            "INVERTER_TYPE": ("inverter_type", str),
            "INVERTER_MODEL": ("inverter_model", str),
            "INVERTER_DEVICE": ("inverter_device", str),
            "INVERTER_BAUD": ("inverter_baud", int),
            "MQTT_HOST": ("mqtt_host", str),
            "MQTT_PORT": ("mqtt_port", int),
        }
        for env_key, (attr, cast) in overrides.items():
            val = os.environ.get(env_key)
            if val is not None:
                setattr(self, attr, cast(val))

    def setup_logging(self):
        level_name = (self.log_level or "info").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
