#!/usr/bin/env bashio
set -e

CONFIG_PATH="/config/config.yaml"
OPTIONS_PATH="/data/options.json"

bashio::log.info "Generating configuration..."

read_option() {
  python3 -c "
import json,sys
o=json.load(open('${OPTIONS_PATH}'))
keys='$1'.split('.')
val=o
for k in keys:
  val=val.get(k,{})
  if not isinstance(val,dict):
    break
if val is None or val == {}:
  val='$2'
print(val)
"
}

mode=$(read_option "mode" "simulation")
inverter_type_raw=$(read_option "type" "sunsynk")

if [ "${mode}" = "simulation" ]; then
    inverter_type="simulation"
    inverter_model="${inverter_type_raw}"
    device=""
    modbus_host=""
else
    inverter_type="${inverter_type_raw}"
    inverter_model=""
    device=$(read_option "device" "")
    modbus_host=$(read_option "modbus_host" "")
fi

modbus_port=$(read_option "modbus_port" "502")
baud=$(read_option "baud_rate" "19200")
addr=$(read_option "modbus_address" "1")
timeout=$(read_option "timeout" "5")

poll_interval=$(read_option "poll_interval" "5")
log_level=$(read_option "log_level" "info")

mqtt_host=$(read_option "mqtt.host" "core-mosquitto")
mqtt_port=$(read_option "mqtt.port" "1883")
mqtt_user=$(read_option "mqtt.username" "")
mqtt_pass=$(read_option "mqtt.password" "")
mqtt_prefix=$(read_option "mqtt.topic_prefix" "helix_bridge")
mqtt_ha=$(read_option "mqtt.ha_discovery" "true")

if bashio::var.is_empty "${mqtt_host}" || [ "${mqtt_host}" = "core-mosquitto" ]; then
    if bashio::services.available "mqtt"; then
        mqtt_host=$(bashio::services "mqtt" "host")
        mqtt_port=$(bashio::services "mqtt" "port")
        mqtt_user=$(bashio::services "mqtt" "username")
        mqtt_pass=$(bashio::services "mqtt" "password")
        bashio::log.info "Using HA MQTT service: ${mqtt_host}:${mqtt_port}"
    fi
fi

mkdir -p "$(dirname "${CONFIG_PATH}")"

cat > "${CONFIG_PATH}" << EOF
bridge:
  name: helix-bridge
  log_level: ${log_level}
  poll_interval: ${poll_interval}

inverter:
  type: ${inverter_type}
  model: "${inverter_model}"
  device: "${device}"
  baud_rate: ${baud}
  modbus_port: ${modbus_port}
  modbus_host: "${modbus_host}"
  modbus_address: ${addr}
  modbus_timeout: ${timeout}

mqtt:
  enabled: true
  host: ${mqtt_host}
  port: ${mqtt_port}
  username: "${mqtt_user}"
  password: "${mqtt_pass}"
  topic_prefix: ${mqtt_prefix}
  ha_discovery: ${mqtt_ha}
  ha_discovery_prefix: homeassistant
EOF

bashio::log.info "Configuration written to ${CONFIG_PATH}"

export BRIDGE_CONFIG="${CONFIG_PATH}"

bashio::log.info "Starting helix-bridge (${inverter_type})..."
exec python3 -m main
