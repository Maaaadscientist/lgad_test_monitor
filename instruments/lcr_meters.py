"""Concrete LCR meter implementations."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .base import LCRMeter

try:
    import usbtmc  # type: ignore
    import usb.backend.libusb1 as libusb_backend  # type: ignore
except ImportError:  # pragma: no cover - hardware dependency
    usbtmc = None
    libusb_backend = None


@dataclass
class LCROptions:
    vid: Optional[int] = None
    pid: Optional[int] = None
    expected_idn: str = "E4980A"


class KeysightE4980ALCRMeter(LCRMeter):
    """USB-TMC wrapper around the Keysight E4980A."""

    def __init__(self, options: LCROptions | None = None) -> None:
        if usbtmc is None:  # pragma: no cover - hardware dependency
            raise RuntimeError("usbtmc is required for Keysight E4980A support")
        self._options = options or LCROptions()
        self._instrument = None

    def connect(self) -> None:
        backend = libusb_backend.get_backend() if libusb_backend is not None else None
        vid, pid = self._options.vid, self._options.pid
        if vid is None or pid is None:
            vid, pid = self._autodetect(backend)
        self._instrument = usbtmc.Instrument(vid, pid, backend=backend)
        self._instrument.write("*CLS")
        self._instrument.write("*RST")

    def fetch_cprp(self) -> tuple[float, float]:
        if self._instrument is None:
            raise RuntimeError("LCR meter not connected")
        response = self._instrument.ask("FETC:IMP:CPRP?")
        cp_str, rp_str, *_ = response.split(',')
        return float(cp_str), float(rp_str)

    def shutdown(self) -> None:
        if self._instrument is None:
            return
        try:
            self._instrument.write("*CLS")
        finally:
            try:
                self._instrument.close()
            finally:
                self._instrument = None

    def _autodetect(self, backend) -> tuple[int, int]:
        if libusb_backend is None:  # pragma: no cover - hardware dependency
            raise RuntimeError("pyusb is required to auto-detect the LCR meter")
        import usb.core  # type: ignore

        devices = usb.core.find(find_all=True, backend=backend)
        for dev in devices:
            try:
                instr = usbtmc.Instrument(dev.idVendor, dev.idProduct, backend=backend)
                idn = instr.ask("*IDN?").strip()
                if self._options.expected_idn in idn:
                    return dev.idVendor, dev.idProduct
            except Exception:
                continue
        raise RuntimeError(f"Unable to locate LCR meter matching '{self._options.expected_idn}'")


class VirtualLCRMeter(LCRMeter):
    """Synthetic LCR data generator."""

    def __init__(self, capacitance_pf: float = 50.0, resistance_kohm: float = 100.0) -> None:
        self._cap_pf = capacitance_pf
        self._res_ohm = resistance_kohm * 1e3
        self._seed = random.Random(7)
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def fetch_cprp(self) -> tuple[float, float]:
        if not self._connected:
            raise RuntimeError("Virtual LCR meter not connected")
        cap = self._seed.gauss(self._cap_pf, self._cap_pf * 0.01)
        rp = self._seed.gauss(self._res_ohm, self._res_ohm * 0.02)
        return cap * 1e-12, rp

    def shutdown(self) -> None:
        self._connected = False
