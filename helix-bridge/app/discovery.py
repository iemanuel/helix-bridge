import asyncio
import logging
import socket
import struct

log = logging.getLogger("bridge.discovery")

SOLARMAN_DEFAULT_PORT = 8899
MODBUS_DEFAULT_PORT = 502
SCAN_TIMEOUT = 2
MAX_CONCURRENT = 100


def _crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)


def _get_local_networks() -> list[str]:
    """Discover local network CIDR ranges."""
    networks = []
    try:
        import subprocess
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "scope", "global"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "inet " in line:
                parts = line.strip().split()
                for part in parts:
                    if "/" in part and "." in part:
                        networks.append(part)
    except Exception:
        pass
    if not networks:
        networks.append("192.168.1.0/24")
    return networks


async def _port_open(host: str, port: int, timeout: float = SCAN_TIMEOUT) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


def _try_modbus_identification(host: str, port: int, slave_id: int = 1) -> dict | None:
    """Read holding register 0x0000 to 0x000A (device model / serial)."""
    try:
        sock = socket.create_connection((host, port), timeout=SCAN_TIMEOUT)
        tx_id = 1
        # Read holding registers 0x0000-0x000A (11 registers)
        mbap = struct.pack(">HHHB", tx_id, 0, 6 + 4 * 6, slave_id)
        pdu = struct.pack(">BHH", 0x03, 0x0000, 11)
        sock.send(mbap + pdu)
        resp = sock.recv(1024)
        sock.close()

        if len(resp) < 9:
            return None

        values = []
        for i in range(11):
            offset = 9 + i * 2
            if offset + 2 <= len(resp):
                values.append(struct.unpack(">H", resp[offset:offset + 2])[0])

        # Try to read device name as ASCII from first registers
        name_bytes = b""
        for v in values[:5]:
            name_bytes += struct.pack(">H", v)
        name = name_bytes.decode("ascii", errors="replace").strip("\x00").strip()

        return {
            "host": host,
            "port": port,
            "protocol": "modbus_tcp",
            "values": values[:11],
            "model_hint": name if len(name) > 2 else None,
            "slave_id": slave_id,
        }
    except Exception:
        return None


def _try_solarman_identification(host: str, port: int, slave_id: int = 1) -> dict | None:
    """Read inverter info (holding regs 0-10) via Solarman V5 protocol."""
    try:
        from pysolarmanv5 import PySolarmanV5
        dev = PySolarmanV5(
            address=host, serial=0, port=port,
            mb_slave_id=slave_id, socket_timeout=SCAN_TIMEOUT,
            verbose=False,
        )
        values = dev.read_holding_registers(0x0000, 11)
        dev.disconnect()

        if not values:
            return None

        name_bytes = b""
        for v in values[:5]:
            name_bytes += struct.pack(">H", v)
        name = name_bytes.decode("ascii", errors="replace").strip("\x00").strip()

        return {
            "host": host,
            "port": port,
            "protocol": "solarman_v5",
            "values": values[:11],
            "model_hint": name if len(name) > 2 else None,
            "slave_id": slave_id,
        }
    except Exception:
        return None


async def _scan_host(host: str) -> list[dict]:
    results = []
    # Check Solarman port
    if await _port_open(host, SOLARMAN_DEFAULT_PORT):
        info = await asyncio.to_thread(_try_solarman_identification, host, SOLARMAN_DEFAULT_PORT)
        if info:
            results.append(info)
    # Check Modbus port
    if await _port_open(host, MODBUS_DEFAULT_PORT):
        info = await asyncio.to_thread(_try_modbus_identification, host, MODBUS_DEFAULT_PORT)
        if info:
            results.append(info)
    return results


def _hosts_in_cidr(cidr: str) -> list[str]:
    from ipaddress import ip_network
    net = ip_network(cidr, strict=False)
    return [str(h) for h in net.hosts()]


async def discover(timeout: float = 30) -> list[dict]:
    networks = _get_local_networks()
    log.info("scanning networks: %s", networks)

    all_hosts = []
    for net in networks:
        all_hosts.extend(_hosts_in_cidr(net))

    results = []
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def scan_one(host: str):
        async with sem:
            try:
                devs = await asyncio.wait_for(_scan_host(host), timeout=SCAN_TIMEOUT + 1)
                if devs:
                    results.extend(devs)
            except (OSError, asyncio.TimeoutError):
                pass

    tasks = [scan_one(h) for h in all_hosts]
    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)

    log.info("discovery complete: %d device(s) found", len(results))
    return results
