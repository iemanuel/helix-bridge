import logging
import socket
import struct

log = logging.getLogger("bridge.collector.modbus")

MODBUS_READ_HOLDING_REGISTERS = 0x03
MODBUS_READ_INPUT_REGISTERS = 0x04
MODBUS_WRITE_SINGLE_REGISTER = 0x06
MODBUS_WRITE_MULTIPLE_REGISTERS = 0x10
SOLARMAN_DEFAULT_PORT = 8899


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


def _to_u32(hi: int, lo: int) -> int:
    return (hi << 16) | lo


def _to_i32(hi: int, lo: int) -> int:
    val = (hi << 16) | lo
    if val >= 0x80000000:
        val -= 0x100000000
    return val


def _to_i16(val: int) -> int:
    if val >= 0x8000:
        val -= 0x10000
    return val


class ModbusRTUClient:
    def __init__(self, device: str, baud: int, slave_id: int = 1, timeout: float = 3):
        import serial
        self._ser = serial.Serial(
            port=device,
            baudrate=baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )
        self._slave_id = slave_id

    def read_registers(self, reg_start: int, count: int, func_code: int = MODBUS_READ_HOLDING_REGISTERS) -> list[int] | None:
        req = struct.pack(">BBHH", self._slave_id, func_code, reg_start, count)
        req += _crc16(req)
        self._ser.write(req)
        self._ser.flush()

        expected_len = 5 + count * 2
        resp = self._ser.read(expected_len)
        if len(resp) < 5:
            return None

        values = []
        for i in range(count):
            offset = 3 + i * 2
            val = struct.unpack(">H", resp[offset:offset + 2])[0]
            values.append(val)
        return values

    def read_batch(self, registers: list[dict]) -> dict:
        result = {}
        grouped = {}
        for reg in registers:
            key = (reg["addr"] // 32, reg.get("func", MODBUS_READ_HOLDING_REGISTERS))
            if key not in grouped:
                grouped[key] = {"start": reg["addr"], "count": 0, "func": reg.get("func", MODBUS_READ_HOLDING_REGISTERS), "entries": []}
            g = grouped[key]
            g["entries"].append(reg)
            g["count"] = max(g["count"], reg["addr"] - g["start"] + (reg.get("count", 1)))

        for g in grouped.values():
            try:
                raw = self.read_registers(g["start"], g["count"], g["func"])
                if raw is None:
                    continue
                for entry in g["entries"]:
                    idx = entry["addr"] - g["start"]
                    cnt = entry.get("count", 1)
                    if idx + cnt <= len(raw):
                        if cnt == 1:
                            val = raw[idx]
                        elif cnt == 2:
                            val = _to_u32(raw[idx], raw[idx + 1])
                        else:
                            val = raw[idx:idx + cnt]
                        name = entry.get("name")
                        if name:
                            scale = entry.get("scale", 1)
                            signed = entry.get("signed", False)
                            if signed and isinstance(val, int):
                                val = _to_i32(val >> 16, val & 0xFFFF) if cnt == 2 and val > 0xFFFF else _to_i16(val)

                            value = None
                            if isinstance(val, (list, tuple)):
                                value = [round(v * scale, 3) for v in val]
                            else:
                                value = round(val * scale, 3) if scale != 1 else val

                            result[name] = value
            except Exception as e:
                log.warning("batch read error at 0x%04X: %s", g["start"], e)

        return result

    def write_single_register(self, reg_addr: int, value: int) -> bool:
        req = struct.pack(">BBHH", self._slave_id, MODBUS_WRITE_SINGLE_REGISTER, reg_addr, value)
        req += _crc16(req)
        try:
            self._ser.write(req)
            self._ser.flush()
            resp = self._ser.read(8)
            return len(resp) == 8
        except OSError as e:
            log.warning("modbus rtu write error: %s", e)
            return False

    def close(self):
        self._ser.close()


class ModbusTCPClient:
    def __init__(self, host: str, port: int = 502, slave_id: int = 1, timeout: float = 5):
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._timeout = timeout
        self._sock = None
        self._tx_id = 0

    def _connect(self):
        if self._sock:
            try:
                self._sock.send(b"")
                return True
            except OSError:
                self._sock = None
        self._sock = socket.create_connection((self._host, self._port), timeout=self._timeout)
        return True

    def read_registers(self, reg_start: int, count: int, func_code: int = MODBUS_READ_HOLDING_REGISTERS) -> list[int] | None:
        if not self._connect():
            return None

        self._tx_id = (self._tx_id + 1) & 0xFFFF
        mbap = struct.pack(">HHHB", self._tx_id, 0, 6 + count * 2, self._slave_id)
        pdu = struct.pack(">BHH", func_code, reg_start, count)
        req = mbap + pdu

        try:
            self._sock.send(req)
            resp = self._sock.recv(1024)
            if len(resp) < 9:
                return None

            byte_count = resp[8]
            values = []
            for i in range(count):
                offset = 9 + i * 2
                val = struct.unpack(">H", resp[offset:offset + 2])[0]
                values.append(val)
            return values
        except OSError as e:
            log.error("modbus tcp error: %s", e)
            self._sock = None
            return None

    def read_batch(self, registers: list[dict]) -> dict:
        result = {}
        grouped = {}
        for reg in registers:
            key = (reg["addr"] // 32, reg.get("func", MODBUS_READ_HOLDING_REGISTERS))
            if key not in grouped:
                grouped[key] = {"start": reg["addr"], "count": 0, "func": reg.get("func", MODBUS_READ_HOLDING_REGISTERS), "entries": []}
            g = grouped[key]
            g["entries"].append(reg)
            g["count"] = max(g["count"], reg["addr"] - g["start"] + (reg.get("count", 1)))

        for g in grouped.values():
            try:
                raw = self.read_registers(g["start"], g["count"], g["func"])
                if raw is None:
                    continue
                for entry in g["entries"]:
                    idx = entry["addr"] - g["start"]
                    cnt = entry.get("count", 1)
                    if idx + cnt <= len(raw):
                        if cnt == 1:
                            val = raw[idx]
                        elif cnt == 2:
                            val = _to_u32(raw[idx], raw[idx + 1])
                        else:
                            val = raw[idx:idx + cnt]
                        name = entry.get("name")
                        if name:
                            scale = entry.get("scale", 1)
                            signed = entry.get("signed", False)
                            if signed and isinstance(val, int):
                                val = _to_i32(val >> 16, val & 0xFFFF) if cnt == 2 and val > 0xFFFF else _to_i16(val)

                            if isinstance(val, (list, tuple)):
                                value = [round(v * scale, 3) for v in val]
                            else:
                                value = round(val * scale, 3) if scale != 1 else val

                            result[name] = value
            except Exception as e:
                log.warning("batch read error at 0x%04X: %s", g["start"], e)

        return result

    def write_single_register(self, reg_addr: int, value: int) -> bool:
        if not self._connect():
            return False
        self._tx_id = (self._tx_id + 1) & 0xFFFF
        mbap = struct.pack(">HHHB", self._tx_id, 0, 6, self._slave_id)
        pdu = struct.pack(">BHH", MODBUS_WRITE_SINGLE_REGISTER, reg_addr, value)
        req = mbap + pdu
        try:
            self._sock.send(req)
            resp = self._sock.recv(12)
            return len(resp) >= 12
        except OSError as e:
            log.warning("modbus tcp write error: %s", e)
            self._sock = None
            return False

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None


def create_modbus_client(config):
    if config.inverter_device:
        if config.inverter_device.startswith("solarman://"):
            from .solarman_client import SolarmanV5Client
            host = config.inverter_device.removeprefix("solarman://")
            if ":" in host:
                host, port_str = host.split(":", 1)
                port = int(port_str)
            else:
                port = SOLARMAN_DEFAULT_PORT
            return SolarmanV5Client(
                host=host,
                port=port,
                slave_id=config.inverter_modbus_address,
                logger_sn=config.inverter_logger_sn,
                timeout=config.inverter_modbus_timeout,
            )
        return ModbusRTUClient(
            device=config.inverter_device,
            baud=config.inverter_baud,
            slave_id=config.inverter_modbus_address,
            timeout=config.inverter_modbus_timeout,
        )

    host = config.inverter_modbus_host or "localhost"

    if config.inverter_modbus_port == SOLARMAN_DEFAULT_PORT or config.inverter_solarman:
        from .solarman_client import SolarmanV5Client
        return SolarmanV5Client(
            host=host,
            port=config.inverter_modbus_port,
            slave_id=config.inverter_modbus_address,
            logger_sn=config.inverter_logger_sn,
            timeout=config.inverter_modbus_timeout,
        )

    return ModbusTCPClient(
        host=host,
        port=config.inverter_modbus_port,
        slave_id=config.inverter_modbus_address,
        timeout=config.inverter_modbus_timeout,
    )
