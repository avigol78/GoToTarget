import serial
import time

cli = serial.Serial('/dev/ttyUSB0',115200)

data = serial.Serial('/dev/ttyUSB1',921600)

while True:
    raw = data.read(4096)
    print(len(raw))

for line in open("profile.cfg"):
    cli.write((line+'\n').encode())
    time.sleep(0.1)