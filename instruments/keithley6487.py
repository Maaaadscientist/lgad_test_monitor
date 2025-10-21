"""Shared controller for Keithley 6487 interactions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from iv_control.SimpleKeithley6487 import SimpleKeithley6487
except ImportError:  # pragma: no cover - hardware dependency
    SimpleKeithley6487 = None


@dataclass
class Keithley6487Controller:
    port: str = "/dev/ttyUSB0"
    _device: Optional[SimpleKeithley6487] = None

    def connect(self) -> None:
        if SimpleKeithley6487 is None:
            raise RuntimeError("pyserial support for Keithley 6487 is unavailable")
        if self._device is not None:
            return
        self._device = SimpleKeithley6487(port=self.port)
        self._device.setup_for_measurement()

    def send_command(self, command: str) -> None:
        self._ensure_device()
        self._device.send_command(command)

    def query(self, command: str) -> str:
        self._ensure_device()
        return self._device.query(command)

    def read_current(self) -> float:
        self._ensure_device()
        value = self._device.read_current()
        return float(value) if value is not None else float("nan")

    def close(self) -> None:
        if self._device is None:
            return
        try:
            self._device.send_command("*CLS")
        finally:
            self._device.ser.close()
            self._device = None

    def _ensure_device(self) -> None:
        if self._device is None:
            raise RuntimeError("Keithley 6487 controller not connected")
