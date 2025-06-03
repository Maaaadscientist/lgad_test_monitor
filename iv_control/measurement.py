import time
import numpy as np
import pandas as pd
import os
from datetime import datetime
from iv_control.instrument import setup_instrument, instr
from iv_control.config import load_config
import threading




def set_stop_event(event):
    global stop_event
    stop_event = event

def get_iv_data():
    return time_series, current_series

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

    voltages = np.arange(start_voltage, stop_voltage + step_voltage, step_voltage)

    setup_instrument()
    iv_curve.clear()

    for v in voltages:
        if stop_event.is_set():
            print("🔴 Measurement stopped before next voltage step.")
            instr.write("OUTP OFF")
            instr.write("*CLS")
            return

        instr.write(f"SOUR:VOLT:LEV {v}")
        instr.write("OUTP ON")

        time_series.clear()
        current_series.clear()
        timestamps = []
        current_data = []
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
