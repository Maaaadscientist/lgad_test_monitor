"""Abstract interfaces for LGAD measurement instruments."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class SupportsShutdown(Protocol):
    def shutdown(self) -> None: ...


class HVSource(ABC):
    """High-voltage source capable of sourcing voltage and reporting current."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def enable_output(self, enable: bool) -> None: ...

    @abstractmethod
    def set_voltage(self, voltage: float) -> None: ...

    @abstractmethod
    def get_voltage(self) -> float: ...

    @abstractmethod
    def measure_current(self) -> float: ...

    @abstractmethod
    def shutdown(self) -> None: ...


class PicoAmmeter(ABC):
    """Low-current measurement device."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def read_current(self) -> float: ...

    @abstractmethod
    def shutdown(self) -> None: ...


class LCRMeter(ABC):
    """Measures capacitance/resistance under applied bias."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def fetch_cprp(self) -> tuple[float, float]: ...

    @abstractmethod
    def shutdown(self) -> None: ...
