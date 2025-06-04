import smbus2
import time

#def read_sht35():
#    bus = smbus2.SMBus(1)
#    address = 0x44
#    bus.write_i2c_block_data(address, 0x24, [0x00])
#    time.sleep(0.02)
#    data = bus.read_i2c_block_data(address, 0x00, 6)
#    raw_temp = data[0] << 8 | data[1]
#    raw_humi = data[3] << 8 | data[4]
#    temp = -45 + (175 * raw_temp / 65535.0)
#    humi = 100 * raw_humi / 65535.0
#    return temp, humi

def read_sht35():
    with smbus2.SMBus(1) as bus:
        # 替换成你的读传感器指令，例如：
        # 写入测量命令（假设你用的是 SHT3x default command 0x2400）
        bus.write_i2c_block_data(0x44, 0x24, [0x00])
        time.sleep(0.015)  # 等待测量完成

        data = bus.read_i2c_block_data(0x44, 0x00, 6)
        temperature = -45 + (175 * ((data[0] << 8) + data[1]) / 65535.0)
        humidity = 100 * ((data[3] << 8) + data[4]) / 65535.0

        return round(temperature, 2), round(humidity, 2)
