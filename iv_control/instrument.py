import usbtmc, time, usb.backend.libusb1
from iv_control.config import load_config

backend = usb.backend.libusb1.get_backend()
instr = usbtmc.Instrument(0x05E6, 0x2470, backend=backend)

def setup_instrument():
    cfg = load_config()  # ✅ 每次运行动态读取配置

    start_voltage = cfg['start_voltage']
    stop_voltage = cfg['stop_voltage']

    # 获取最大绝对电压
    max_abs_voltage = max(abs(start_voltage), abs(stop_voltage))

    # 自动选择合适的电压范围
    if max_abs_voltage <= 0.2:
        voltage_range = 0.2
    elif max_abs_voltage <= 2:
        voltage_range = 2
    elif max_abs_voltage <= 20:
        voltage_range = 20
    elif max_abs_voltage <= 200:
        voltage_range = 200
    else:
        voltage_range = 1000  # 超出范围默认使用最大支持值

    instr.write("*CLS")
    instr.write("*RST")
    time.sleep(1)
    instr.write("SOUR:FUNC VOLT")
    instr.write(f"SOUR:VOLT:RANG {voltage_range}")  # ✅ 动态范围设置
    instr.write("SENS:FUNC 'CURR'")

    return instr

