"""Minimal Linux /dev/i2c-N access via the I2C_RDWR ioctl (no dependencies)."""

import ctypes
import fcntl
import os

I2C_RDWR = 0x0707
I2C_M_RD = 0x0001


class _Msg(ctypes.Structure):
    _fields_ = [
        ("addr", ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("len", ctypes.c_uint16),
        ("buf", ctypes.POINTER(ctypes.c_uint8)),
    ]


class _RdwrData(ctypes.Structure):
    _fields_ = [("msgs", ctypes.POINTER(_Msg)), ("nmsgs", ctypes.c_uint32)]


class I2CBus:
    """One adapter. Writes send `[reg, *data]`; reads send `reg`, then a repeated-start read."""

    def __init__(self, bus: int):
        self.bus = bus
        self.fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _transfer(self, msgs):
        arr = (_Msg * len(msgs))(*msgs)
        fcntl.ioctl(self.fd, I2C_RDWR, _RdwrData(arr, len(msgs)))

    def write(self, addr: int, reg: int, data: bytes):
        payload = bytes([reg]) + bytes(data)
        buf = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
        self._transfer([_Msg(addr, 0, len(payload), buf)])

    def read(self, addr: int, reg: int, length: int) -> bytes:
        wbuf = (ctypes.c_uint8 * 1)(reg)
        rbuf = (ctypes.c_uint8 * length)()
        self._transfer([_Msg(addr, 0, 1, wbuf), _Msg(addr, I2C_M_RD, length, rbuf)])
        return bytes(rbuf)
