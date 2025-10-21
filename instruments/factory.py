"""Factory helpers that assemble instrument suites from configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .base import HVSource, PicoAmmeter, LCRMeter
from .hv_sources import (
    HVSourceOptions,
    Keithley2470HVSource,
    Keithley6487HVSource,
    VirtualHVSource,
)
from .keithley6487 import Keithley6487Controller
from .lcr_meters import KeysightE4980ALCRMeter, LCROptions, VirtualLCRMeter
from .picoammeters import (
    PicoOptions,
    Keithley6485PicoAmmeter,
    Keithley6487PicoAmmeter,
    VirtualPicoAmmeter,
)


@dataclass
class InstrumentSettings:
    hv_source: str = "virtual"
    picoammeter: str = "virtual"
    lcr_meter: Optional[str] = "virtual"
    hv_options: dict[str, Any] = field(default_factory=dict)
    pico_options: dict[str, Any] = field(default_factory=dict)
    lcr_options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "InstrumentSettings":
        instruments_cfg = config.get("instruments", config)
        return cls(
            hv_source=instruments_cfg.get("hv_source", "virtual"),
            picoammeter=instruments_cfg.get("picoammeter", "virtual"),
            lcr_meter=instruments_cfg.get("lcr_meter", instruments_cfg.get("lcr", "virtual")),
            hv_options=instruments_cfg.get("hv_options", {}),
            pico_options=instruments_cfg.get("pico_options", {}),
            lcr_options=instruments_cfg.get("lcr_options", {}),
        )


@dataclass
class InstrumentSuite:
    hv_source: HVSource
    picoammeter: PicoAmmeter
    lcr_meter: Optional[LCRMeter] = None

    def shutdown_all(self) -> None:
        self.hv_source.shutdown()
        self.picoammeter.shutdown()
        if self.lcr_meter is not None:
            self.lcr_meter.shutdown()


def create_instrument_suite(settings: InstrumentSettings) -> InstrumentSuite:
    """Create instrument wrappers with optional shared controllers."""
    hv_type = (settings.hv_source or "virtual").lower()
    pico_type = (settings.picoammeter or "virtual").lower()
    lcr_type = (settings.lcr_meter or "virtual").lower() if settings.lcr_meter else None

    shared_6487: Optional[Keithley6487Controller] = None
    if "6487" in {hv_type, pico_type}:
        shared_port = (
            settings.hv_options.get("serial_port")
            or settings.pico_options.get("serial_port")
            or "/dev/ttyUSB0"
        )
        shared_6487 = Keithley6487Controller(port=shared_port)

    hv_source = _create_hv_source(hv_type, settings.hv_options, shared_6487)
    picoammeter = _create_picoammeter(pico_type, settings.pico_options, shared_6487, hv_source)
    lcr_meter = _create_lcr_meter(lcr_type, settings.lcr_options)

    return InstrumentSuite(hv_source=hv_source, picoammeter=picoammeter, lcr_meter=lcr_meter)


def _create_hv_source(
    hv_type: str,
    options: dict[str, Any],
    shared_6487: Optional[Keithley6487Controller],
) -> HVSource:
    if hv_type in {"keithley_2470", "keithley2470", "2470"}:
        hv_options = HVSourceOptions(
            voltage_range=options.get("voltage_range"),
        )
        try:
            return Keithley2470HVSource(hv_options)
        except Exception as exc:
            print(f"⚠️ Failed to initialize Keithley 2470 ({exc}); using virtual HV source.")
    if hv_type in {"keithley_6487", "keithley6487", "6487"}:
        hv_options = HVSourceOptions(
            serial_port=options.get("serial_port"),
            voltage_range=options.get("voltage_range"),
        )
        try:
            return Keithley6487HVSource(hv_options, controller=shared_6487)
        except Exception as exc:
            print(f"⚠️ Failed to initialize Keithley 6487 HV source ({exc}); using virtual HV source.")
    if hv_type in {"virtual", "sim", "simulation"}:
        return VirtualHVSource(
            noise=options.get("noise", 5e-12),
            load_resistance=options.get("virtual_dut_resistance", options.get("load_resistance", 1e7)),
        )
    raise ValueError(f"Unsupported HV source type: {hv_type}")


def _create_picoammeter(
    pico_type: str,
    options: dict[str, Any],
    shared_6487: Optional[Keithley6487Controller],
    hv_source: HVSource,
) -> PicoAmmeter:
    if pico_type in {"keithley_6487", "keithley6487", "6487"}:
        pico_options = PicoOptions(serial_port=options.get("serial_port"))
        try:
            controller = shared_6487 or Keithley6487Controller(port=pico_options.serial_port or "/dev/ttyUSB1")
            return Keithley6487PicoAmmeter(pico_options, controller)
        except Exception as exc:
            print(f"⚠️ Failed to initialize Keithley 6487 picoammeter ({exc}); using virtual picoammeter.")
    if pico_type in {"keithley_6485", "keithley6485", "6485"}:
        pico_options = PicoOptions(serial_port=options.get("serial_port"))
        try:
            return Keithley6485PicoAmmeter(pico_options)
        except Exception as exc:
            print(f"⚠️ Failed to initialize Keithley 6485 picoammeter ({exc}); using virtual picoammeter.")
    if pico_type in {"virtual", "sim", "simulation"}:
        noise = options.get("noise", 2e-12)
        virtual_hv = hv_source if hasattr(hv_source, "get_voltage") else None
        resistance = options.get("virtual_dut_resistance", options.get("load_resistance", 1e7))
        return VirtualPicoAmmeter(noise=noise, hv_source=virtual_hv, resistance_ohm=resistance)
    raise ValueError(f"Unsupported picoammeter type: {pico_type}")


def _create_lcr_meter(lcr_type: Optional[str], options: dict[str, Any]) -> Optional[LCRMeter]:
    if not lcr_type or lcr_type in {"none", "disabled"}:
        return None
    if lcr_type in {"keysight_e4980a", "e4980a", "keysight"}:
        lcr_options = LCROptions(
            vid=_coerce_int(options.get("vid")),
            pid=_coerce_int(options.get("pid")),
            expected_idn=options.get("expected_idn", "E4980A"),
        )
        try:
            return KeysightE4980ALCRMeter(lcr_options)
        except Exception as exc:
            print(f"⚠️ Failed to initialize Keysight E4980A ({exc}); using virtual LCR meter.")
    if lcr_type in {"virtual", "sim", "simulation"}:
        return VirtualLCRMeter(
            capacitance_pf=options.get("capacitance_pf", 50.0),
            resistance_kohm=options.get("resistance_kohm", 100.0),
        )
    raise ValueError(f"Unsupported LCR meter type: {lcr_type}")


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value, 0) if isinstance(value, str) else int(value)
    except Exception:
        return None
