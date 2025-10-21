"""Concrete HV source implementations."""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any, Optional

from .base import HVSource
from .keithley6487 import Keithley6487Controller

try:
    import usbtmc  # type: ignore
    import usb.backend.libusb1 as libusb_backend  # type: ignore
except ImportError:  # pragma: no cover - hardware dependency
    usbtmc = None
    libusb_backend = None


@dataclass
class HVSourceOptions:
    serial_port: Optional[str] = None
    voltage_range: Optional[float] = None


class Keithley2470HVSource(HVSource):
    """Wrapper for the Keithley 2470 SMU."""

    def __init__(self, options: HVSourceOptions | None = None) -> None:
        if usbtmc is None:  # pragma: no cover - hardware dependency
            raise RuntimeError("usbtmc is required for Keithley 2470 support")
        self._options = options or HVSourceOptions()
        self._instrument = None

    def connect(self) -> None:
        backend = libusb_backend.get_backend() if libusb_backend is not None else None
        self._instrument = usbtmc.Instrument(0x05E6, 0x2470, backend=backend)
        self._write("*CLS")
        self._write("*RST")
        time.sleep(1)
        self._write("SOUR:FUNC VOLT")
        rng = self._options.voltage_range or 200
        self._write(f"SOUR:VOLT:RANG {rng}")
        self._write("SENS:FUNC 'CURR'")

    def enable_output(self, enable: bool) -> None:
        self._write(f"OUTP {'ON' if enable else 'OFF'}")

    def set_voltage(self, voltage: float) -> None:
        self._write(f"SOUR:VOLT:LEV {voltage}")

    def get_voltage(self) -> float:
        return self._float_query("SOUR:VOLT:LEV?")

    def measure_current(self) -> float:
        return self._float_query("MEAS:CURR?")

    def shutdown(self) -> None:
        if self._instrument is None:
            return
        try:
            self.enable_output(False)
            self._write("*CLS")
        finally:
            try:
                self._instrument.close()
            except Exception:
                pass
            self._instrument = None

    # Internal helpers -------------------------------------------------
    def _write(self, command: str) -> None:
        if self._instrument is None:
            raise RuntimeError("HV source not connected")
        self._instrument.write(command)

    def _float_query(self, command: str) -> float:
        if self._instrument is None:
            raise RuntimeError("HV source not connected")
        try:
            return float(self._instrument.ask(command))
        except Exception:
            return float("nan")


class Keithley6487HVSource(HVSource):
    """Keithley 6487 picoammeter used as a voltage source."""

    def __init__(
        self,
        options: HVSourceOptions | None = None,
        controller: Optional[Keithley6487Controller] = None,
    ) -> None:
        port = (options or HVSourceOptions()).serial_port or "/dev/ttyUSB0"
        self._options = options or HVSourceOptions(serial_port=port)
        self._controller = controller or Keithley6487Controller(port=port)
        self._owns_controller = controller is None

    def connect(self) -> None:
        self._controller.connect()
        self._controller.send_command("SOUR:FUNC VOLT")
        if self._options.voltage_range:
            self._controller.send_command(f"SOUR:VOLT:RANG {self._options.voltage_range}")

    def enable_output(self, enable: bool) -> None:
        self._controller.send_command(f"OUTP {'ON' if enable else 'OFF'}")

    def set_voltage(self, voltage: float) -> None:
        self._controller.send_command(f"SOUR:VOLT:LEV {voltage}")

    def get_voltage(self) -> float:
        try:
            return float(self._controller.query("SOUR:VOLT:LEV?"))
        except Exception:
            return float("nan")

    def measure_current(self) -> float:
        return self._controller.read_current()

    def shutdown(self) -> None:
        try:
            self.enable_output(False)
        finally:
            if self._owns_controller:
                self._controller.close()


class VirtualHVSource(HVSource):
    """Simulated HV source for development without hardware."""

    def __init__(self, noise: float = 5e-12, load_resistance: float = 1e7) -> None:
        self._voltage = 0.0
        self._output_enabled = False
        self._noise = noise
        self._seed = random.Random(42)
        self._load_resistance = load_resistance

    def connect(self) -> None:
        self._voltage = 0.0
        self._output_enabled = False

    def enable_output(self, enable: bool) -> None:
        self._output_enabled = enable

    def set_voltage(self, voltage: float) -> None:
        self._voltage = voltage

    def get_voltage(self) -> float:
        return self._voltage

    def measure_current(self) -> float:
        if not self._output_enabled:
            return 0.0
        base = 0.0
        if self._load_resistance:
            base = self._voltage / self._load_resistance
        perturb = self._seed.gauss(0, self._noise)
        return base + perturb

    def shutdown(self) -> None:
        self._output_enabled = False
        self._voltage = 0.0

    def set_load_resistance(self, resistance_ohm: float) -> None:
        self._load_resistance = resistance_ohm
