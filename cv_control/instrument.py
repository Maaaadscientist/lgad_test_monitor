import usbtmc
import time
import usb.core
import usb.backend.libusb1
from iv_control.config import load_config

#backend = usb.backend.libusb1.get_backend()
#lcr = usbtmc.Instrument(0x2a8d, 0x0101, backend=backend)  # Update if needed

def find_lcr_vid_pid(expected_idn="E4980A"):
    backend = usb.backend.libusb1.get_backend()
    devices = usb.core.find(find_all=True, backend=backend)

    for dev in devices:
        try:
            # Try creating a USBTMC instrument
            instr = usbtmc.Instrument(dev.idVendor, dev.idProduct, backend=backend)
            idn = instr.ask("*IDN?").strip()
            if expected_idn in idn:
                print(f"✅ Found: {idn} (VID=0x{dev.idVendor:04x}, PID=0x{dev.idProduct:04x})")
                return dev.idVendor, dev.idProduct
        except Exception as e:
            continue

    raise RuntimeError(f"❌ No USBTMC device responding with '{expected_idn}' found.")

# Automatically detect and connect
VID, PID = find_lcr_vid_pid()
backend = usb.backend.libusb1.get_backend()
lcr = usbtmc.Instrument(VID, PID, backend=backend)

