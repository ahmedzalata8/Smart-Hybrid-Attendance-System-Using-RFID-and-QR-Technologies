#!/usr/bin/env python3
"""
Find the reader's real baud rate.
Opens COM5 (or argv[1]) at each common baud, captures ~2s, and scores how
'text-like' the result is (printable ASCII, digits, STX/ETX/CRLF present).
"""
import sys, time, serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
BAUDS = [9600, 14400, 19200, 28800, 38400, 57600, 115200, 4800, 2400]

print(f"Probing {port} at several baud rates...\n")

best = None
for baud in BAUDS:
    try:
        ser = serial.Serial(port, baud, timeout=0.2)
    except serial.SerialException as e:
        print(f"  {baud:>7} : cannot open ({e})")
        continue
    ser.reset_input_buffer()
    time.sleep(2.0)
    n = ser.in_waiting
    data = ser.read(n) if n else b""
    ser.close()

    if not data:
        print(f"  {baud:>7} : no data")
        continue

    printable = sum(1 for b in data if 32 <= b < 127)
    digits = sum(1 for b in data if 0x30 <= b <= 0x39)
    has_stx = 0x02 in data
    has_etx = 0x03 in data
    has_crlf = b"\x0d\x0a" in data
    pct_print = printable / len(data) * 100
    pct_digit = digits / len(data) * 100

    flags = []
    if has_stx: flags.append("STX")
    if has_etx: flags.append("ETX")
    if has_crlf: flags.append("CRLF")
    flagstr = ",".join(flags) if flags else "-"

    sample = "".join(chr(b) if 32 <= b < 127 else "." for b in data[:48])
    print(f"  {baud:>7} : {len(data):>4}B  print={pct_print:5.1f}%  "
          f"digit={pct_digit:5.1f}%  [{flagstr:<12}]  {sample}")

    # Score: lots of digits + framing markers = likely correct
    score = pct_digit + (20 if has_stx else 0) + (20 if has_etx else 0) + \
            (20 if has_crlf else 0)
    if best is None or score > best[1]:
        best = (baud, score)

if best:
    print(f"\n  >>> Most text-like baud: {best[0]} (score {best[1]:.0f})")
    print(f"      Re-run: python dump_raw.py {port}   after setting 19200->{best[0]}")
