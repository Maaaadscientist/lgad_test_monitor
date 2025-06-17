import usbtmc
import time
import usb.backend.libusb1
from iv_control.config import load_config

backend = usb.backend.libusb1.get_backend()
lcr = usbtmc.Instrument(0x2a8d, 0x0101, backend=backend)  # Update if needed

def setup_lcr():
    # Setup LCR meter
    cfg = load_config()
    ac_voltage = cfg['ac_voltage'] * 1e-3  # in mV
    ac_frequency = cfg['ac_frequency'] * 1e3  # in kHz
    lcr.write("*RST")
    time.sleep(0.5)
    lcr.write("FUNC:IMP CPRP")
    lcr.write(f"VOLT {ac_voltage}")
    lcr.write(f"FREQ {ac_frequency}")
