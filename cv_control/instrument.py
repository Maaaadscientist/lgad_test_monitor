"""Deprecated LCR helpers kept for import compatibility.

The new instrument abstraction lives under the `instruments` package.
"""
from __future__ import annotations

from instruments import InstrumentSettings, create_instrument_suite
from iv_control.config import load_config

lcr = None  # Legacy export retained for compatibility


def setup_lcr(config: dict | None = None):
    cfg = config or load_config()
    suite = create_instrument_suite(InstrumentSettings.from_config(cfg))
    if suite.lcr_meter is None:
        raise RuntimeError("No LCR meter configured in config.yaml")
    suite.lcr_meter.connect()
    return suite.lcr_meter
