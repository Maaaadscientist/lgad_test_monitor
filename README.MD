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

Same for the LCR meter,
```
sudo vim /etc/udev/rules.d/99-keysight-e4980a.rules
```
add this line
```
SUBSYSTEM=="usb", ATTR{idVendor}=="2a8d", ATTR{idProduct}=="2f01", MODE="0666"
```
and the execute
```
sudo udevadm control --reload
sudo udevadm trigger
```

