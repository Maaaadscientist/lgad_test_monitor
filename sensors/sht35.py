import logging
import time

try:
    import smbus2
except ImportError:  # pragma: no cover - dependency missing during simulation
    smbus2 = None

logger = logging.getLogger(__name__)


def read_sht35():
    if smbus2 is None:
        logger.debug("smbus2 not available; returning virtual env readings")
        return None, None

    try:
        with smbus2.SMBus(1) as bus:
            bus.write_i2c_block_data(0x44, 0x24, [0x00])
            time.sleep(0.015)
            data = bus.read_i2c_block_data(0x44, 0x00, 6)
    except FileNotFoundError:
        logger.warning("I2C bus /dev/i2c-1 not found; SHT35 readings unavailable")
        return None, None
    except Exception as exc:
        logger.warning("Failed to read SHT35 sensor: %s", exc)
        return None, None

    temperature = -45 + (175 * ((data[0] << 8) + data[1]) / 65535.0)
    humidity = 100 * ((data[3] << 8) + data[4]) / 65535.0
    return round(temperature, 2), round(humidity, 2)
