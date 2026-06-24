#!/usr/bin/env python3
"""
Disable (or re-enable) the buzzer/beep on the R16-12DB UHF reader.

The beep is a hardware buzzer on the reader board. This setting is stored in
the reader's flash, so you only need to run this ONCE -- it survives reboots
and your attendance code (app.py) needs no changes.

Protocol: Granding / SYC UHF reader serial protocol.
  Command frame:  Len  Adr  Cmd  Data[]  CRC16_L  CRC16_H
  - Len  = number of bytes AFTER Len (Adr + Cmd + Data + CRC)
  - CRC  = CRC-16 (poly 0x8408, preset 0xFFFF), appended low byte first

Safety: we FIRST send a read-only "Obtain reader information" (0x21) command to
confirm the reader speaks this protocol (and to auto-find baud + address). Only
if that succeeds do we send the buzzer command. A wrong/garbled frame fails the
CRC check and is silently ignored by the reader, so nothing gets corrupted.

Usage:
    python disable_buzzer.py                 # auto-detect port, turn buzzer OFF
    python disable_buzzer.py --enable        # turn the buzzer back ON
    python disable_buzzer.py --port COM5     # force a specific COM port
    python disable_buzzer.py --baud 57600    # force a baud rate

NOTE: close app.py / any other program using the reader first, so the COM port
is free.
"""

import argparse
import sys
import time

import serial
import serial.tools.list_ports

CMD_READER_INFO = 0x21   # read-only probe
CMD_ENABLE_BUZZER = 0x40  # BeepEn: bit0  0=disable, 1=enable

# Things to try when auto-detecting. 0xFF is the broadcast/public address.
ADDRESSES = [0xFF, 0x00, 0x01]
# 19200 first: that's the rate the attendance-system server uses for this reader.
BAUDS = [19200, 9600, 38400, 57600, 115200]


def crc16(data: bytes) -> int:
    """CRC-16 used by this reader family (poly 0x8408, preset 0xFFFF)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_frame(adr: int, cmd: int, data: bytes = b"") -> bytes:
    length = 1 + 1 + len(data) + 2          # Adr + Cmd + Data + CRC16
    body = bytes([length, adr, cmd]) + data
    crc = crc16(body)
    return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def find_response(buf: bytes, recmd: int):
    """Scan a byte buffer for a CRC-valid frame whose reCmd == recmd.

    Robust against tag-inventory data interleaved on the line: every candidate
    is validated by its own CRC, so junk bytes can't produce a false match.
    """
    i = 0
    n = len(buf)
    while i < n:
        length = buf[i]
        end = i + 1 + length                # full frame = Len byte + 'length' bytes
        if 4 <= length <= 64 and end <= n:
            frame = buf[i:end]
            body, crc_rx = frame[:-2], frame[-2] | (frame[-1] << 8)
            if crc16(body) == crc_rx and len(frame) >= 4 and frame[2] == recmd:
                return frame
        i += 1
    return None


def transceive(ser, frame: bytes, recmd: int, wait: float = 0.4):
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    deadline = time.time() + wait
    buf = b""
    while time.time() < deadline:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
        else:
            time.sleep(0.02)
    return find_response(buf, recmd), buf


def autodetect_port():
    """Find the RFID reader's port. The reader is on a CH340 USB-RS232 adapter;
    the ESP32 stepper controller is the CP210x -- skip that one."""
    ports = serial.tools.list_ports.comports()
    # Prefer CH340 / USB-SERIAL (the reader), explicitly skipping CP210x (ESP32).
    for p in ports:
        desc = (p.description or "").upper()
        if p.device.upper() == "COM1" or "CP210" in desc:
            continue
        if any(k in desc for k in ("CH340", "CH9102", "USB-SERIAL", "FTDI")):
            return p.device
    # last resort: any non-COM1, non-CP210x port
    for p in ports:
        desc = (p.description or "").upper()
        if p.device.upper() != "COM1" and "CP210" not in desc:
            return p.device
    return None


def open_serial(port, baud):
    """Open the port, applying the CH340 workaround the project relies on
    (some CH340 units fail to configure 19200 directly -- open low, then bump)."""
    try:
        return serial.Serial(port, baud, timeout=0.2)
    except serial.SerialException:
        s = serial.Serial(port, 9600, timeout=0.2)
        s.baudrate = baud
        return s


def main():
    ap = argparse.ArgumentParser(description="Disable/enable the R16-12DB buzzer")
    ap.add_argument("--port", help="COM port (default: auto-detect CP210x)")
    ap.add_argument("--baud", type=int, help="force a baud rate")
    ap.add_argument("--addr", type=lambda x: int(x, 0), help="force reader address, e.g. 0x00")
    ap.add_argument("--enable", action="store_true", help="turn the buzzer back ON")
    args = ap.parse_args()

    port = args.port or autodetect_port()
    if not port:
        print("No serial port found. Plug in the reader and/or pass --port COMx.")
        print("Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"   {p.device}  ({p.description})")
        sys.exit(1)

    bauds = [args.baud] if args.baud else BAUDS
    addrs = [args.addr] if args.addr is not None else ADDRESSES

    print(f"Using port: {port}")
    print("Probing for the reader (read-only)...")

    found = None  # (ser, baud, addr)
    ser = None
    for baud in bauds:
        try:
            ser = open_serial(port, baud)
        except Exception as e:
            print(f"   could not open {port} @ {baud}: {e}")
            continue
        for addr in addrs:
            resp, _ = transceive(ser, build_frame(addr, CMD_READER_INFO), CMD_READER_INFO)
            if resp:
                found = (ser, baud, addr)
                print(f"   reader responded at baud={baud}, address=0x{addr:02X}")
                break
        if found:
            break
        ser.close()

    if not found:
        print("\nNo response to the read-only probe.")
        print("Likely causes:")
        print("  - another program (app.py, a serial monitor) is holding the port")
        print("  - the reader is in a continuous 'active/timing' mode and ignores commands")
        print("  - this reader uses a different command protocol")
        print("Try closing other programs and re-running, or use the vendor GUI.")
        sys.exit(2)

    ser, baud, addr = found
    beep_en = 0x01 if args.enable else 0x00
    action = "ENABLE" if args.enable else "DISABLE"
    frame = build_frame(addr, CMD_ENABLE_BUZZER, bytes([beep_en]))
    print(f"\nSending buzzer {action} command: {frame.hex(' ')}")
    resp, raw = transceive(ser, frame, CMD_ENABLE_BUZZER)
    ser.close()

    if resp and len(resp) >= 4:
        status = resp[3]
        if status == 0x00:
            print(f"\nSUCCESS - buzzer {action}D. Setting saved in the reader's flash.")
            print("It stays this way across reboots; no change needed to app.py.")
        else:
            print(f"\nReader replied but status=0x{status:02X} (non-zero = not applied).")
            print(f"Raw reply: {resp.hex(' ')}")
    else:
        print("\nNo valid acknowledgement received for the buzzer command.")
        print(f"Raw bytes seen: {raw.hex(' ') if raw else '(none)'}")
        print("The probe worked, so try re-running once more.")


if __name__ == "__main__":
    main()
