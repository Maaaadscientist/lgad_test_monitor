import math
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd

from instruments import InstrumentSettings, create_instrument_suite
from instruments.base import HVSource, PicoAmmeter
from instruments.hv_sources import VirtualHVSource
from instruments.picoammeters import VirtualPicoAmmeter
from iv_control.config import load_config


def _over_limit(value: float, limit: float) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    return abs(value) > limit


def ramp_voltage(
    hv_source: HVSource,
    picoammeter: PicoAmmeter,
    target_voltage: float,
    step: float = 1.0,
    delay: float = 0.05,
    maximum_current: float = 10e-6,
) -> bool:
    try:
        current_voltage = float(hv_source.get_voltage())
    except Exception as e:
        print(f"⚠️ Failed to read current voltage: {e}")
        current_voltage = 0.0

    if abs(current_voltage - target_voltage) < 1e-3:
        return True

    step = abs(step)
    direction = 1 if target_voltage > current_voltage else -1
    steps = np.arange(current_voltage, target_voltage, direction * step)
    steps = np.append(steps, target_voltage)
    
    print(target_voltage, steps)
    for v in steps:
        hv_source.set_voltage(v)
        time.sleep(delay)

        # 每步测一次电流并限流保护
        try:
            current_source = float(hv_source.measure_current())
            current = float(picoammeter.read_current())
        except Exception as e:
            print(f"⚠️ Current read error at {v:.2f}V: {e}")
            current = 0.0  # fallback, allow next step
            current_source = 0.0

        if (
            _over_limit(current, maximum_current)
            or _over_limit(current_source, 3 * maximum_current)
        ):
            print(f"🛑 Over-current during ramp: {current:.3e} A > {maximum_current:.3e} A")
            hv_source.enable_output(False)
            return False

    # 最终电压
    hv_source.set_voltage(target_voltage)
    time.sleep(delay)
    return True


def _ensure_hv_source(hv_source: HVSource, suite, hv_options) -> HVSource:
    try:
        hv_source.connect()
        return hv_source
    except Exception as exc:
        print(f"⚠️ HV source unavailable ({exc}); switching to virtual source.")
        fallback = VirtualHVSource(
            noise=hv_options.get("noise", 5e-12),
            load_resistance=hv_options.get("virtual_dut_resistance", hv_options.get("load_resistance", 1e7)),
        )
        fallback.connect()
        suite.hv_source = fallback
        return fallback


def _ensure_picoammeter(picoammeter: PicoAmmeter, suite, hv_source: HVSource, pico_options) -> PicoAmmeter:
    try:
        picoammeter.connect()
        if isinstance(picoammeter, VirtualPicoAmmeter):
            picoammeter.attach_hv_source(hv_source)
            picoammeter.set_resistance(pico_options.get("virtual_dut_resistance", pico_options.get("load_resistance", 1e7)))
        return picoammeter
    except Exception as exc:
        print(f"⚠️ Picoammeter unavailable ({exc}); using virtual DUT (10MΩ).")
        fallback = VirtualPicoAmmeter(
            noise=pico_options.get("noise", 2e-12),
            hv_source=hv_source,
            resistance_ohm=pico_options.get("virtual_dut_resistance", pico_options.get("load_resistance", 1e7)),
        )
        fallback.connect()
        suite.picoammeter = fallback
        return fallback
def perform_measurement(shared_status, time_series, current_series, iv_curve, stop_event):
    """
    主测量函数，负责控制 Keithley 2470，记录数据并实时更新状态。

    参数:
        status_data: dict，包含 voltage, current, time
        time_series: list，当前电压点的时间序列
        current_series: list，当前电压点的电流序列
        iv_curve: list，最终保存的 (V, I) 点
        stop_event: threading.Event，外部中止控制
    """
    timestamp = datetime.now().strftime("%m%d%H%M")
    output_dir = f"outputs/iv_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    cfg = load_config()  # ✅ 每次运行动态读取配置

    start_voltage = cfg['start_voltage']
    stop_voltage = cfg['stop_voltage']
    step_voltage = cfg['step_voltage']
    measurement_duration = cfg['measurement_duration']
    sample_interval = cfg['sample_interval']
    stabilization_time = cfg['stabilization_time']
    maximum_current = cfg['maximum_current'] * 1e-6

    if start_voltage < stop_voltage:
        voltages = np.arange(start_voltage, stop_voltage + step_voltage, step_voltage)
    else:
        voltages = np.arange(start_voltage, stop_voltage - step_voltage, -step_voltage)


    instruments_cfg = InstrumentSettings.from_config(cfg)
    suite = create_instrument_suite(instruments_cfg)
    hv_source = suite.hv_source
    picoammeter = suite.picoammeter

    hv_source = _ensure_hv_source(hv_source, suite, instruments_cfg.hv_options)
    picoammeter = _ensure_picoammeter(
        picoammeter,
        suite,
        hv_source,
        instruments_cfg.pico_options,
    )

    if isinstance(hv_source, VirtualHVSource) and not isinstance(picoammeter, VirtualPicoAmmeter):
        print("⚠️ HV source fallback detected; routing current through virtual 10MΩ DUT.")
        try:
            picoammeter.shutdown()
        except Exception:
            pass
        picoammeter = VirtualPicoAmmeter(
            noise=instruments_cfg.pico_options.get("noise", 2e-12),
            hv_source=hv_source,
            resistance_ohm=instruments_cfg.pico_options.get("virtual_dut_resistance", 1e7),
        )
        picoammeter.connect()
        suite.picoammeter = picoammeter

    print(
        "▶️ Starting IV measurement using",
        hv_source.__class__.__name__,
        "HV and",
        picoammeter.__class__.__name__,
        "ammeter",
    )

    iv_curve.clear()

    try:
        for v in voltages:
            if stop_event.is_set():
                print("🔴 Measurement stopped before next voltage step.")
                return

            hv_source.enable_output(True)
            voltage_output = ramp_voltage(
                hv_source,
                picoammeter,
                v,
                step=30.0,
                delay=0.05,
                maximum_current=maximum_current,
            )

            if not voltage_output:
                break
            time_series.clear()
            current_series.clear()
            timestamps = []
            current_data = []
            current_total = []
            humi = []
            temp = []

            # 初始化用于记录连续超限计数的变量（放在 while 循环前）
            over_current_count = 0

            start_time = time.perf_counter()
            
            while (time.perf_counter() - start_time) < measurement_duration:
                if stop_event.is_set():
                    return
                loop_start = time.perf_counter()
                elapsed = loop_start - start_time
            
            try:
                current_source = float(hv_source.measure_current())
            except Exception as e:
                print(f"⚠️ Source read error: {e}")
                current_source = np.nan

            try:
                current = float(picoammeter.read_current())
            except Exception as e:
                print(f"⚠️ Read error: {e}")
                current = np.nan

            if isinstance(picoammeter, VirtualPicoAmmeter) and not math.isnan(current):
                current_source = current
                if _over_limit(current, maximum_current):
                    over_current_count += 1
                    print(f"⚠️ Over-current count: {over_current_count} ({current:.3e} A > {maximum_current:.3e} A)")
                    if over_current_count > 3:
                        print("🔴 Triggering emergency stop due to 3 consecutive over-current readings.")
                        stop_event.set()
                        return
            
                # 获取当前温湿度
                humidity = shared_status.get("humidity", "N/A")
                temperature = shared_status.get("temperature", "N/A")
            
                # 记录数据
                timestamps.append(elapsed)
                current_data.append(current)
                humi.append(humidity)
                temp.append(temperature)
                time_series.append(elapsed)
                current_series.append(current)
                current_total.append(current_source)
            
                # 更新状态
                shared_status["voltage"] = v
                shared_status["current"] = current
                shared_status["time"] = elapsed
            
                # 计算睡眠时间（周期补偿）
                loop_duration = time.perf_counter() - loop_start
                sleep_time = sample_interval - loop_duration
                if sleep_time > 0:
                    time.sleep(sleep_time)


            voltage_turnoff = ramp_voltage(
                hv_source,
                picoammeter,
                0,
                step=30.0,
                delay=0.05,
                maximum_current=maximum_current,
            )
            hv_source.enable_output(False)
            if not voltage_turnoff:
                break

            # 平均电流计算（最后几秒）
            stable_data = [i for t, i in zip(timestamps, current_data)
                           if t > (measurement_duration - stabilization_time)]
            avg_current = np.nanmean(stable_data)
            iv_curve.append((v, avg_current))

            # 保存 I-t 数据点
            df = pd.DataFrame({
                'Time(s)': timestamps,
                'Current(A)': current_data,
                'Temperature(°C)': temp,
                'Humidity(%RH)': humi,
                'SourceCurrent(A)': current_total,
            })
            df.to_csv(f"{output_dir}/results_{v:.2f}V.csv", index=False)

        # 保存最终 I-V 曲线
        pd.DataFrame(iv_curve, columns=["Voltage(V)", "Current(A)"]).to_csv(
            f"{output_dir}/IV_Curve.csv", index=False)
        print("✅ Measurement complete.")
    finally:
        hv_source.enable_output(False)
        suite.shutdown_all()
