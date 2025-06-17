import os
import numpy as np
import pandas as pd
import time
from datetime import datetime
from iv_control.instrument import setup_instrument, instr  # Keithley 2470
from cv_control.instrument import setup_lcr, lcr  # Keysight E4980AL-102
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

    # Setup Keithley
    setup_instrument()
    
    # Setup LCR meter
    setup_lcr()

    cv_curve.clear()

    for v in voltages:
        if stop_event.is_set():
            print("🔴 Measurement stopped.")
            instr.write("OUTP OFF")
            instr.write("*CLS")
            return

        instr.write(f"SOUR:VOLT:LEV {v}")
        instr.write("OUTP ON")

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
                instr.write("OUTP OFF")
                instr.write("*CLS")
                return
            loop_start = time.perf_counter()
            elapsed = loop_start - start_time

            try:
                current = float(instr.ask("MEAS:CURR?"))
            except Exception as e:
                print(f"⚠️ Read error: {e}")
                current = np.nan

            if abs(current) > maximum_current:
                print(f"⚠️ Over-current! {current:.3e} A > {maximum_current:.3e} A")
                instr.write("OUTP OFF")
                instr.write("*CLS")
                stop_event.set()
                return

            humidity = shared_status.get("humidity", "N/A")
            temperature = shared_status.get("temperature", "N/A")

            cp, rp = map(float, lcr.ask("FETC:IMP:CPRP?").split(','))
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

        instr.write("OUTP OFF")


        df = pd.DataFrame({
            'Time(s)': timestamps,
            'Current(A)': current_data,
            'Cp(uF)': cp_list,
            'Rp(ohm)': rp_list,
            'Temperature(°C)': temp,
            'Humidity(%RH)': humi
        })
        df.to_csv(f"{output_dir}/results_{v:.2f}V.csv", index=False)


    instr.write("OUTP OFF")
    instr.write("*CLS")
    print("✅ C–V measurement complete.")

