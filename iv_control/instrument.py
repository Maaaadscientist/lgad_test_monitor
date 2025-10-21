"""Deprecated helpers for backward compatibility.

Use the classes under `instruments.*` instead of this module.
"""
from __future__ import annotations

from instruments import InstrumentSettings, create_instrument_suite
from iv_control.config import load_config

instr = None  # Legacy name retained for backward compatibility


def setup_instrument(config: dict | None = None):
    """Return instrument wrappers for legacy callers.

    This now returns the new HV source and picoammeter wrappers. Prefer using
    `instruments.create_instrument_suite` directly in new code.
    """
    cfg = config or load_config()
    suite = create_instrument_suite(InstrumentSettings.from_config(cfg))
    suite.hv_source.connect()
    suite.picoammeter.connect()
    return suite.hv_source, suite.picoammeter
