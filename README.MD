Add this line to `/etc/udev/rules.d/99-keithley.rules`
```
sudo vim /etc/udev/rules.d/99-keithley.rules
```
```
SUBSYSTEM=="usb", ATTR{idVendor}=="05e6", ATTR{idProduct}=="2470", MODE="0666", GROUP="plugdev"
```
And then,
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```
