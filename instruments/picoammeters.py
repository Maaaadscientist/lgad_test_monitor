"""Concrete picoammeter implementations."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .base import PicoAmmeter
from .keithley6487 import Keithley6487Controller

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    serial = None

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .base import HVSource

@dataclass
class PicoOptions:
    serial_port: Optional[str] = None


class Keithley6487PicoAmmeter(PicoAmmeter):
    """Picoammeter wrapper that can share a Keithley 6487 controller."""

    def __init__(
        self,
        options: PicoOptions | None = None,
        controller: Optional[Keithley6487Controller] = None,
    ) -> None:
        port = (options or PicoOptions()).serial_port or "/dev/ttyUSB1"
        self._options = options or PicoOptions(serial_port=port)
        self._controller = controller or Keithley6487Controller(port=port)
        self._owns_controller = controller is None

    def connect(self) -> None:
        self._controller.connect()

    def read_current(self) -> float:
        return self._controller.read_current()

    def shutdown(self) -> None:
        if not self._owns_controller:
            return
        self._controller.close()


class Keithley6485PicoAmmeter(PicoAmmeter):
    """Minimal SCPI wrapper for the Keithley 6485 picoammeter."""

    def __init__(self, options: PicoOptions | None = None) -> None:
        if serial is None:  # pragma: no cover - hardware dependency
            raise RuntimeError("pyserial is required for Keithley 6485 support")
        self._options = options or PicoOptions(serial_port="/dev/ttyUSB2")
        self._serial = None

    def connect(self) -> None:
        port = self._options.serial_port or "/dev/ttyUSB2"
        self._serial = serial.Serial(port=port, baudrate=19200, timeout=2)
        time.sleep(0.5)
        self._write("*RST")
        self._write("*CLS")
        self._write("SYST:ZCH ON")
        self._write("SYST:ZCOR ON")
        self._write("SENS:FUNC 'CURR'")
        self._write("SENS:CURR:RANG 2E-5")
        self._write("SENS:CURR:NPLC 1")
        self._write("SYST:ZCOR:ACQ")
        time.sleep(0.5)
        self._write("SYST:ZCH OFF")

    def read_current(self) -> float:
        self._ensure_serial()
        self._write("READ?")
        response = self._serial.readline().decode("ascii", errors="ignore").strip()
        try:
            if response.endswith("A"):
                response = response[:-1]
            return float(response)
        except ValueError:
            return float("nan")

    def shutdown(self) -> None:
        if self._serial is None:
            return
        try:
            self._write("*CLS")
        finally:
            self._serial.close()
            self._serial = None

    def _write(self, command: str) -> None:
        self._ensure_serial()
        if not command.endswith("\n"):
            command += "\n"
        self._serial.write(command.encode("ascii"))
        time.sleep(0.05)

    def _ensure_serial(self) -> None:
        if self._serial is None:
            raise RuntimeError("Keithley 6485 picoammeter not connected")


class VirtualPicoAmmeter(PicoAmmeter):
    """Software picoammeter that mirrors the virtual DUT behaviour."""

    def __init__(
        self,
        noise: float = 2e-12,
        hv_source: "HVSource | None" = None,
        resistance_ohm: Optional[float] = 1e7,
    ) -> None:
        self._seed = random.Random(1337)
        self._noise = noise
        self._connected = False
        self._hv_source = hv_source
        self._resistance = resistance_ohm

    def connect(self) -> None:
        self._connected = True

    def read_current(self) -> float:
        if not self._connected:
            raise RuntimeError("Virtual picoammeter not connected")
        baseline = 0.0
        if self._hv_source is not None and self._resistance:
            try:
                baseline = self._hv_source.get_voltage() / self._resistance
            except Exception:
                baseline = 0.0
        return baseline + self._seed.gauss(0, self._noise)

    def shutdown(self) -> None:
        self._connected = False

    def attach_hv_source(self, hv_source: "HVSource | None") -> None:
        self._hv_source = hv_source

    def set_resistance(self, resistance_ohm: Optional[float]) -> None:
        self._resistance = resistance_ohm
