import asyncio
import json
import logging
from aiohttp import web

log = logging.getLogger("bridge.api")


async def start_api(collector):
    app = web.Application()

    async def handle_metrics(request):
        data = collector.poll()
        return web.json_response(data if data else {})

    async def handle_status(request):
        return web.json_response({
            "status": "running",
            "collector": collector.__class__.__name__,
        })

    async def handle_config(request):
        from settings.config import Config
        cfg = Config()
        cfg.load()
        return web.json_response({
            "inverter_type": cfg.inverter_type,
            "poll_interval": cfg.poll_interval,
            "mqtt_enabled": cfg.mqtt_enabled,
            "mqtt_host": cfg.mqtt_host,
        })

    async def handle_health(request):
        return web.json_response({"ok": True})

    async def handle_write(request):
        try:
            body = await request.json()
            register = body.get("register")
            value = body.get("value")
            if register is None or value is None:
                return web.json_response({"error": "missing register or value"}, status=400)
            ok = collector.write_register(int(register), int(value))
            return web.json_response({"ok": ok, "register": register, "value": value})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_discover(request):
        from discovery import discover
        try:
            devices = await asyncio.wait_for(discover(timeout=30), timeout=35)
            return web.json_response({"devices": devices})
        except asyncio.TimeoutError:
            return web.json_response({"error": "discovery timed out"}, status=504)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_get("/api/v1/metrics", handle_metrics)
    app.router.add_get("/api/v1/status", handle_status)
    app.router.add_get("/api/v1/config", handle_config)
    app.router.add_post("/api/v1/write", handle_write)
    app.router.add_post("/api/v1/discover", handle_discover)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log.info("api server started on :8080")
