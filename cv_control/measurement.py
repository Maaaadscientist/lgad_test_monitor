import os
import time
from datetime import datetime

import numpy as np
import pandas as pd

from instruments import InstrumentSettings, create_instrument_suite
from instruments.base import LCRMeter
from instruments.hv_sources import VirtualHVSource
from instruments.picoammeters import VirtualPicoAmmeter
from iv_control.config import load_config


def perform_cv_measurement(shared_status, time_series, current_series, cv_curve, stop_event):
    """
    Control Keithley 2470 (DC bias) and LCR meter (Cp, Rp measurement) in parallel to measure C-V curve.
    Save data for each DC bias step including capacitance and resistance.

    Parameters:
        shared_status: dict, contains environment data like temperature and humidity
        time_series, current_series: list, data series for plotting
        cv_curve: list, stores (V, Cp, Rp)
        stop_event: threading.Event, allows external interruption
    """
    timestamp = datetime.now().strftime("%m%d%H%M")
    output_dir = f"outputs/cv_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    cfg = load_config()
    start_voltage = cfg['start_voltage']
    stop_voltage = cfg['stop_voltage']
    step_voltage = cfg['step_voltage']
    measurement_duration = cfg['measurement_duration']
    sample_interval = cfg['sample_interval']
    stabilization_time = cfg['stabilization_time']
    maximum_current = cfg['maximum_current'] * 1e-6

    voltages = np.arange(start_voltage, stop_voltage + step_voltage, step_voltage)

    instruments_cfg = InstrumentSettings.from_config(cfg)
    suite = create_instrument_suite(instruments_cfg)
    hv_source = _ensure_hv_source(suite, instruments_cfg.hv_options)
    lcr_meter = suite.lcr_meter

    if lcr_meter is None:
        raise RuntimeError("No LCR meter configured. Set instruments.lcr_meter in config.yaml")

    suite.picoammeter = _ensure_picoammeter(suite.picoammeter, suite, hv_source, instruments_cfg.pico_options)
    lcr_meter.connect()

    print(
        "▶️ Starting CV measurement using",
        hv_source.__class__.__name__,
        "HV,",
        suite.picoammeter.__class__.__name__,
        "ammeter, and",
        lcr_meter.__class__.__name__,
    )

    cv_curve.clear()

    try:
        for v in voltages:
            if stop_event.is_set():
                print("🔴 Measurement stopped.")
                return

            hv_source.enable_output(True)
            hv_source.set_voltage(v)

            time_series.clear()
            current_series.clear()
            timestamps = []
            current_data = []
            cp_list = []
            rp_list = []

            humi = []
            temp = []

            start_time = time.perf_counter()

            while (time.perf_counter() - start_time) < measurement_duration:
                if stop_event.is_set():
                    return
                loop_start = time.perf_counter()
                elapsed = loop_start - start_time

                try:
                    current = float(hv_source.measure_current())
                except Exception as e:
                    print(f"⚠️ Read error: {e}")
                    current = np.nan

                if _over_limit(current, maximum_current):
                    print(f"⚠️ Over-current! {current:.3e} A > {maximum_current:.3e} A")
                    stop_event.set()
                    return

                humidity = shared_status.get("humidity", "N/A")
                temperature = shared_status.get("temperature", "N/A")

                cp, rp = _fetch_cprp(lcr_meter)
                cp_list.append(cp)
                rp_list.append(rp)
                timestamps.append(elapsed)
                current_data.append(current)
                humi.append(humidity)
                temp.append(temperature)
                time_series.append(elapsed)
                current_series.append(current)

                shared_status["voltage"] = v
                shared_status["current"] = current
                shared_status["parallel-resistance"] = rp
                shared_status["parallel-capacitance"] = cp
                shared_status["time"] = elapsed

                loop_duration = time.perf_counter() - loop_start
                sleep_time = sample_interval - loop_duration
                if sleep_time > 0:
                    time.sleep(sleep_time)

            hv_source.enable_output(False)

            df = pd.DataFrame({
                'Time(s)': timestamps,
                'Current(A)': current_data,
                'Cp(F)': cp_list,
                'Rp(ohm)': rp_list,
                'Temperature(°C)': temp,
                'Humidity(%RH)': humi
            })
            df.to_csv(f"{output_dir}/results_{v:.2f}V.csv", index=False)

        print("✅ C–V measurement complete.")
    finally:
        hv_source.enable_output(False)
        suite.shutdown_all()


def _over_limit(value: float, limit: float) -> bool:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False
    return abs(value) > limit


def _fetch_cprp(lcr_meter: LCRMeter) -> tuple[float, float]:
    cp, rp = lcr_meter.fetch_cprp()
    return cp, rp


def _ensure_hv_source(suite, hv_options):
    hv_source = suite.hv_source
    try:
        hv_source.connect()
        return hv_source
    except Exception as exc:
        print(f"⚠️ HV source unavailable for CV measurement ({exc}); switching to virtual source.")
        fallback = VirtualHVSource(
            noise=hv_options.get("noise", 5e-12),
            load_resistance=hv_options.get("virtual_dut_resistance", hv_options.get("load_resistance", 1e7)),
        )
        fallback.connect()
        suite.hv_source = fallback
        return fallback


def _ensure_picoammeter(picoammeter, suite, hv_source, pico_options):
    try:
        picoammeter.connect()
        if isinstance(picoammeter, VirtualPicoAmmeter):
            picoammeter.attach_hv_source(hv_source)
            picoammeter.set_resistance(pico_options.get("virtual_dut_resistance", pico_options.get("load_resistance", 1e7)))
        return picoammeter
    except Exception as exc:
        print(f"⚠️ Picoammeter unavailable for CV measurement ({exc}); using virtual DUT (10MΩ).")
        fallback = VirtualPicoAmmeter(
            noise=pico_options.get("noise", 2e-12),
            hv_source=hv_source,
            resistance_ohm=pico_options.get("virtual_dut_resistance", pico_options.get("load_resistance", 1e7)),
        )
        fallback.connect()
        suite.picoammeter = fallback
        return fallback
