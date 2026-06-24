#!/usr/bin/env python3
"""Dump raw bytes from the reader so we can see the real frame format."""
import sys, time, serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
try:
    ser = serial.Serial(port, 19200, timeout=0.2)
except serial.SerialException:
    ser = serial.Serial(port, 9600, timeout=0.2)
    ser.baudrate = 19200

print(f"Dumping raw bytes from {port} @ 19200. Ctrl+C to stop.\n")
ser.reset_input_buffer()
buf = bytearray()
try:
    t0 = time.time()
    while time.time() - t0 < 8:          # capture ~8 seconds
        n = ser.in_waiting
        if n:
            buf.extend(ser.read(n))
        else:
            time.sleep(0.02)
finally:
    ser.close()

print(f"Captured {len(buf)} bytes.\n")
print("HEX:")
print(buf.hex(" ").upper())
print("\nASCII (non-printable as '.'):")
print("".join(chr(b) if 32 <= b < 127 else "." for b in buf))
print("\nUnique byte values present:", sorted(set(buf)))
