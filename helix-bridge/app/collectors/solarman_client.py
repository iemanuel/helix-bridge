import logging

from pysolarmanv5 import PySolarmanV5

log = logging.getLogger("bridge.collector.solarman")

SOLARMAN_DEFAULT_PORT = 8899
MODBUS_READ_HOLDING_REGISTERS = 0x03
MODBUS_READ_INPUT_REGISTERS = 0x04
MODBUS_WRITE_SINGLE_REGISTER = 0x06
MODBUS_WRITE_MULTIPLE_REGISTERS = 0x10


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


class SolarmanV5Client:
    def __init__(self, host: str, port: int = SOLARMAN_DEFAULT_PORT,
                 slave_id: int = 1, logger_sn: int = 0, timeout: float = 10):
        self._dev = PySolarmanV5(
            address=host,
            serial=logger_sn,
            port=port,
            mb_slave_id=slave_id,
            socket_timeout=timeout,
            auto_reconnect=True,
            verbose=False,
        )

    def read_registers(self, reg_start: int, count: int,
                       func_code: int = MODBUS_READ_INPUT_REGISTERS) -> list[int] | None:
        try:
            if func_code == MODBUS_READ_INPUT_REGISTERS:
                return self._dev.read_input_registers(reg_start, count)
            else:
                return self._dev.read_holding_registers(reg_start, count)
        except Exception as e:
            log.warning("solarman read error: %s", e)
            return None

    def read_batch(self, registers: list[dict]) -> dict:
        result = {}
        grouped = {}
        for reg in registers:
            key = (reg["addr"] // 32, reg.get("func", MODBUS_READ_INPUT_REGISTERS))
            if key not in grouped:
                grouped[key] = {
                    "start": reg["addr"], "count": 0,
                    "func": reg.get("func", MODBUS_READ_INPUT_REGISTERS),
                    "entries": [],
                }
            g = grouped[key]
            g["entries"].append(reg)
            g["count"] = max(
                g["count"],
                reg["addr"] - g["start"] + (reg.get("count", 1)),
            )

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
                                if cnt == 2 and val > 0xFFFF:
                                    val = _to_i32(val >> 16, val & 0xFFFF)
                                else:
                                    val = _to_i16(val)
                            if isinstance(val, (list, tuple)):
                                value = [round(v * scale, 3) for v in val]
                            else:
                                value = round(val * scale, 3) if scale != 1 else val
                            result[name] = value
            except Exception as e:
                log.warning("batch read error at 0x%04X: %s", g["start"], e)

        return result

    def write_single_register(self, reg_addr: int, value: int) -> bool:
        try:
            self._dev.write_holding_register(reg_addr, value)
            return True
        except Exception as e:
            log.warning("solarman write error: %s", e)
            return False

    def close(self):
        try:
            self._dev.disconnect()
        except Exception:
            pass
