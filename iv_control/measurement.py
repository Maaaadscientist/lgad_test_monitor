import time
import numpy as np
import pandas as pd
import os
from datetime import datetime
from iv_control.instrument import setup_instrument
from iv_control.config import load_config
import threading

def set_stop_event(event):
    global stop_event
    stop_event = event

def get_iv_data():
    return time_series, current_series

def ramp_voltage(instr, target_voltage, step=1.0, delay=0.05, maximum_current=10e-6):
    try:
        current_voltage = float(instr.ask("SOUR:VOLT:LEV?"))
    except Exception as e:
        print(f"⚠️ Failed to read current voltage: {e}")
        current_voltage = 0.0

    if abs(current_voltage - target_voltage) < 1e-3:
        return

    step = abs(step)
    direction = 1 if target_voltage > current_voltage else -1
    steps = np.arange(current_voltage, target_voltage, direction * step)

    for v in steps:
        instr.write(f"SOUR:VOLT:LEV {v}")
        time.sleep(delay)

        # 每步测一次电流并限流保护
        try:
            current = float(instr.ask("MEAS:CURR?"))
        except Exception as e:
            print(f"⚠️ Current read error at {v:.2f}V: {e}")
            current = 0.0  # fallback, allow next step

        if abs(current) > maximum_current:
            print(f"🛑 Over-current during ramp: {current:.3e} A > {maximum_current:.3e} A")
            instr.write("OUTP OFF")
            instr.write("*CLS")
            raise RuntimeError("Ramp aborted due to overcurrent")

    # 最终电压
    instr.write(f"SOUR:VOLT:LEV {target_voltage}")

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


    instr = setup_instrument()
    iv_curve.clear()

    for v in voltages:
        if stop_event.is_set():
            print("🔴 Measurement stopped before next voltage step.")
            instr.write("OUTP OFF")
            instr.write("*CLS")
            return

        instr.write("OUTP ON")
        #instr.write(f"SOUR:VOLT:LEV {v}")
        ramp_voltage(instr, v, step=30.0, delay=0.05, maximum_current=maximum_current)  # 然后缓慢加压

        time_series.clear()
        current_series.clear()
        timestamps = []
        current_data = []
        humi = []
        temp = []

        # 初始化用于记录连续超限计数的变量（放在 while 循环前）
        over_current_count = 0

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
                over_current_count += 1
                print(f"⚠️ Over-current count: {over_current_count} ({current:.3e} A > {maximum_current:.3e} A)")
                if over_current_count >= 3:
                    print("🔴 Triggering emergency stop due to 3 consecutive over-current readings.")
                    instr.write("OUTP OFF")
                    instr.write("*CLS")
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
        
            # 更新状态
            shared_status["voltage"] = v
            shared_status["current"] = current
            shared_status["time"] = elapsed
        
            # 计算睡眠时间（周期补偿）
            loop_duration = time.perf_counter() - loop_start
            sleep_time = sample_interval - loop_duration
            if sleep_time > 0:
                time.sleep(sleep_time)


        ramp_voltage(instr, 0, step=30.0, delay=0.05, maximum_current=maximum_current)  # 然后缓慢加压
        instr.write("OUTP OFF")

        # 平均电流计算（最后几秒）
        stable_data = [i for t, i in zip(timestamps, current_data)
                       if t > (measurement_duration - stabilization_time)]
        avg_current = np.nanmean(stable_data)
        iv_curve.append((v, avg_current))

        # 保存 I-t 数据点
        df = pd.DataFrame({'Time(s)': timestamps, 'Current(A)': current_data, 'Temperature(°C)':temp, 'Humidity(%RH)':humi})
        df.to_csv(f"{output_dir}/reuslts_{v:.2f}V.csv", index=False)

    # 保存最终 I-V 曲线
    pd.DataFrame(iv_curve, columns=["Voltage(V)", "Current(A)"]).to_csv(f"{output_dir}/IV_Curve.csv", index=False)

    instr.write("OUTP OFF")
    instr.write("*CLS")
    print("✅ Measurement complete.")
