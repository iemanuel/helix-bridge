import asyncio
import logging
import signal
import sys

from settings.config import Config
from collectors.base import CollectorRegistry
from collectors.simulation import SimulationCollector
from collectors.victron_vedirect import VictronVEDirectCollector
from collectors.generic_modbus import GenericModbusCollector
from collectors.sunsynk import SunsynkCollector
from collectors.solis import SolisCollector
from collectors.growatt import GrowattCollector
from collectors.sofar import SofarCollector
from collectors.luxpower import LuxpowerCollector
from collectors.huawei import HuaweiCollector
from collectors.goodwe import GoodweCollector
from collectors.sma import SMACollector
from collectors.fronius import FroniusCollector
from collectors.voltronic import VoltronicCollector
from collectors.sunspec import SunSpecCollector
from api.routes import start_api
from ha_integration.mqtt_discovery import MQTTDiscovery

log = logging.getLogger("bridge")

COLLECTOR_MAP = {
    "simulation": SimulationCollector,
    "simulate": SimulationCollector,
    "victron_vedirect": VictronVEDirectCollector,
    "generic_modbus": GenericModbusCollector,
    "sunsynk": SunsynkCollector,
    "deye": SunsynkCollector,
    "sol_ark": SunsynkCollector,
    "solis": SolisCollector,
    "growatt": GrowattCollector,
    "sofar": SofarCollector,
    "luxpower": LuxpowerCollector,
    "huawei": HuaweiCollector,
    "goodwe": GoodweCollector,
    "sma": SMACollector,
    "fronius": FroniusCollector,
    "voltronic": VoltronicCollector,
    "axpert": VoltronicCollector,
    "mppsolar": VoltronicCollector,
    "sunspec": SunSpecCollector,
}


def create_collector(config):
    ctype = config.inverter_type
    cls = COLLECTOR_MAP.get(ctype)

    if cls is None:
        log.warning("unknown collector type '%s', using simulation", ctype)
        cls = SimulationCollector
        ctype = "simulation"

    if ctype in ("victron_vedirect", "voltronic", "axpert", "mppsolar"):
        return cls(device=config.inverter_device, baud=config.inverter_baud)
    else:
        return cls(config)


async def main():
    config = Config()
    config.load()
    config.setup_logging()

    log.info("helix-bridge starting")
    log.info("collector: %s, poll_interval: %ds", config.inverter_type, config.poll_interval)

    registry = CollectorRegistry()
    collector = create_collector(config)
    registry.register(collector)

    mqtt = None
    if config.mqtt_enabled:
        mqtt = MQTTDiscovery(
            config,
            collector.get_metric_definitions(),
            write_callback=collector.write_register,
        )
        mqtt.start()

    poll_task = asyncio.create_task(
        poll_loop(collector, mqtt, config)
    )
    api_task = asyncio.create_task(start_api(collector))

    stop_event = asyncio.Event()

    def handle_stop():
        log.info("shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_stop)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    log.info("shutting down")
    poll_task.cancel()
    api_task.cancel()
    if mqtt:
        mqtt.stop()
    log.info("shutdown complete")


def _poll_and_write(collector, mqtt):
    data = collector.poll()
    if data and mqtt:
        mqtt.publish(data)


async def poll_loop(collector, mqtt, config):
    while True:
        try:
            await asyncio.to_thread(_poll_and_write, collector, mqtt)
        except Exception as e:
            log.error("poll error: %s", e)
        await asyncio.sleep(config.poll_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
