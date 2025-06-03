import smbus2
import time

def read_sht35():
    bus = smbus2.SMBus(1)
    address = 0x44
    bus.write_i2c_block_data(address, 0x24, [0x00])
    time.sleep(0.02)
    data = bus.read_i2c_block_data(address, 0x00, 6)
    raw_temp = data[0] << 8 | data[1]
    raw_humi = data[3] << 8 | data[4]
    temp = -45 + (175 * raw_temp / 65535.0)
    humi = 100 * raw_humi / 65535.0
    return temp, humi

