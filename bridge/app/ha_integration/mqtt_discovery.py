import json
import logging
import threading
import time

import paho.mqtt.client as mqtt

log = logging.getLogger("bridge.mqtt")


_NAME_FIXES = {
    "pv": "PV", "soc": "SOC", "ac": "AC", "dc": "DC",
}


def _friendly_name(name):
    return " ".join(_NAME_FIXES.get(w, w.capitalize()) for w in name.replace("_", " ").split())


class MQTTDiscovery:
    def __init__(self, config, metric_defs, write_callback=None):
        self._host = config.mqtt_host
        self._port = config.mqtt_port
        self._prefix = config.mqtt_topic_prefix
        self._ha_prefix = config.mqtt_ha_discovery_prefix
        self._ha_enabled = config.mqtt_ha_discovery
        self._metric_defs = {m["name"]: m for m in metric_defs}
        self._write_callback = write_callback
        self._client = mqtt.Client(client_id=f"solar-bridge-{int(time.time())}")
        if config.mqtt_username:
            self._client.username_pw_set(config.mqtt_username, config.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._running = False

    def start(self):
        self._running = True
        try:
            self._client.connect(self._host, self._port, keepalive=60)
            self._client.loop_start()
            log.info("mqtt connected to %s:%s", self._host, self._port)
        except Exception as e:
            log.warning("mqtt connection failed: %s", e)

    def stop(self):
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()
        log.info("mqtt disconnected")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("mqtt connected successfully")
            self._client.subscribe(f"{self._prefix}/write")
            log.info("subscribed to %s/write", self._prefix)
            if self._ha_enabled:
                self._publish_ha_discovery()
        else:
            log.error("mqtt connection failed: rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        if not self._write_callback:
            return
        try:
            payload = json.loads(msg.payload)
            register = payload.get("register")
            value = payload.get("value")
            if register is not None and value is not None:
                log.info("mqtt write: reg=0x%04X value=%s", register, value)
                self._write_callback(int(register), int(value))
        except Exception as e:
            log.warning("mqtt write parse error: %s", e)

    def _publish_ha_discovery(self):
        for name, meta in self._metric_defs.items():
            topic = f"{self._ha_prefix}/sensor/{self._prefix}_{name}/config"
            state_topic = f"{self._prefix}/state"

            config_payload = {
                "name": _friendly_name(name),
                "state_topic": state_topic,
                "unit_of_measurement": meta.get("unit", ""),
                "device_class": meta.get("device_class", ""),
                "state_class": meta.get("state_class", "measurement"),
                "icon": meta.get("icon", "mdi:information"),
                "value_template": "{{ value_json." + name + " }}",
                "unique_id": f"{self._prefix}_{name}",
                "object_id": f"{self._prefix}_{name}",
                "device": {
                    "identifiers": [self._prefix],
                    "name": "Helix Bridge",
                    "model": "Helix Bridge",
                    "manufacturer": "Helix",
                    "sw_version": "1.0.0",
                },
                "availability": {
                    "topic": f"{self._prefix}/status",
                    "payload_available": "online",
                    "payload_not_available": "offline",
                },
            }

            self._client.publish(
                topic,
                json.dumps(config_payload),
                retain=True,
            )

    def publish(self, data: dict):
        if not self._running:
            return

        # Flatten and publish state
        payload = {}
        for name, value in data.items():
            if name in self._metric_defs:
                payload[name] = round(value, 2) if isinstance(value, float) else value

        self._client.publish(
            f"{self._prefix}/state",
            json.dumps(payload),
            retain=False,
        )

        # Also publish individual topics for non-HA MQTT consumers
        for name, value in data.items():
            if name in self._metric_defs:
                self._client.publish(
                    f"{self._prefix}/{name}",
                    str(round(value, 2) if isinstance(value, float) else value),
                    retain=False,
                )

        # Online status
        self._client.publish(f"{self._prefix}/status", "online", retain=True)

        if self._ha_enabled:
            loc = self._ha_prefix
            for name, value in data.items():
                if name not in self._metric_defs:
                    continue
                meta = self._metric_defs[name]
                topic = f"{loc}/sensor/{self._prefix}_{name}/state"
                self._client.publish(topic, str(round(value, 2) if isinstance(value, float) else value), retain=True)
