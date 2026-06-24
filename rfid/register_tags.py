#!/usr/bin/env python3
"""
RFID Tag Registration Tool
============================
Scan 20 tags one by one and name them sequentially (Tag-1 through Tag-20).
Each tag is scanned multiple times to get a stable ID via clustering.

Usage:
  .\venv\Scripts\activate; python register_tags.py --port COM4
  .\venv\Scripts\activate; python register_tags.py --port COM4 --count 10
  .\venv\Scripts\activate; python register_tags.py --port COM4 --start 5
"""

import sys
import argparse
import serial
import serial.tools.list_ports
import time
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

TAG_MAP_FILE = Path(__file__).parent / "tag_map.json"

# Must match the live app (rfid_reader.py): the R16-12DB streams the card in the
# reader's "10 no. in D (four byte)" format at 9600 baud. 19200 mis-samples on CH340.
RFID_BAUD = 9600

# Frame format streamed by the reader (active/auto-output mode):
#   STX(0x02) + decimal card number + 2-char hex RSSI + CRLF(0x0D0A) + ETX(0x03)
# e.g.  02 "4187574790" "BE" 0D0A 03
STX = 0x02
ETX = 0x03
RSSI_LEN = 2


def detect_rfid_port():
    """Detect RFID reader port (CH340), skipping CP210x (stepper)."""
    rfid_keywords = ['CH340', 'CH9102', 'USB-SERIAL', 'FTDI']
    esp32_keywords = ['CP210']

    ports = serial.tools.list_ports.comports()
    candidates = []

    for p in ports:
        desc = (p.description or '').upper()
        mfr = (p.manufacturer or '').upper()
        device = p.device.upper()

        if device == 'COM1':
            continue
        if any(kw in desc for kw in esp32_keywords):
            continue

        for kw in rfid_keywords:
            if kw in desc or kw in mfr:
                candidates.insert(0, p)
                break
        else:
            candidates.append(p)

    return candidates[0].device if candidates else None


def open_rfid_port(port):
    """Open RFID serial port at the reader's native 9600 baud."""
    try:
        ser = serial.Serial(port, RFID_BAUD, timeout=0.2,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE)
        return ser
    except serial.SerialException as e:
        print(f"  ERROR: Cannot open {port}: {e}")
        return None


def extract_frames(buffer):
    """Pull complete STX..ETX frames out of the buffer.

    Returns (list of frame payloads, leftover buffer). The payload is the
    bytes between STX and ETX, e.g. b"4187574790BE\\r\\n".
    """
    frames = []
    while True:
        start = buffer.find(STX)
        if start == -1:
            return frames, bytearray()          # no frame start yet
        end = buffer.find(ETX, start + 1)
        if end == -1:
            return frames, buffer[start:]        # incomplete; keep tail
        frames.append(bytes(buffer[start + 1:end]))
        buffer = buffer[end + 1:]


def parse_frame(payload):
    """Split a frame payload into the decimal card number (the tag ID).

    Card = leading decimal digits; the trailing 2 hex chars are RSSI (dropped
    here — the ID stored in tag_map.json is the decimal card number only, so it
    matches what rfid_reader.py emits to the live app).
    """
    text = payload.split(b"\r")[0]               # drop CRLF and trailing
    if len(text) > RSSI_LEN:
        text = text[:-RSSI_LEN]                   # strip RSSI, remainder = card
    digits = bytes(b for b in text if 0x30 <= b <= 0x39)
    return digits.decode("ascii") if digits else None


def scan_tag(ser, scan_duration=3.0):
    """
    Scan for a single tag over scan_duration seconds.
    Returns (most_common_tag_id, read_count), or (None, 0).
    Collects multiple reads and picks the most frequent (stable) one.
    """
    ser.reset_input_buffer()
    buffer = bytearray()
    tag_ids = []
    start = time.time()

    while time.time() - start < scan_duration:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer.extend(data)

            frames, buffer = extract_frames(buffer)
            for payload in frames:
                tag_id = parse_frame(payload)
                if tag_id:
                    tag_ids.append(tag_id)

            # Prevent buffer overflow on a garbled stream
            if len(buffer) > 512:
                buffer = bytearray()

        time.sleep(0.02)

    if not tag_ids:
        return None, 0

    # Find most common tag ID (the stable reading)
    counter = Counter(tag_ids)
    most_common_id, count = counter.most_common(1)[0]

    return most_common_id, len(tag_ids)


def load_tag_map():
    """Load existing tag_map.json."""
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_tag_map(tag_map):
    """Save tag_map.json."""
    with open(TAG_MAP_FILE, "w") as f:
        json.dump(tag_map, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="RFID Tag Registration Tool")
    parser.add_argument('--port', type=str, default=None,
                        help='RFID reader serial port (e.g. COM4)')
    parser.add_argument('--count', type=int, default=20,
                        help='Number of tags to register (default: 20)')
    parser.add_argument('--start', type=int, default=1,
                        help='Starting tag number (default: 1)')
    parser.add_argument('--scan-time', type=float, default=3.0,
                        help='Seconds to scan each tag (default: 3.0)')
    parser.add_argument('--prefix', type=str, default='Tag',
                        help='Tag name prefix (default: Tag)')
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  RFID TAG REGISTRATION TOOL")
    print("=" * 60)
    print()

    # Detect port
    port = args.port or detect_rfid_port()
    if not port:
        print("  ERROR: No RFID reader port detected.")
        print("  Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"    {p.device} - {p.description}")
        print("  Use --port COM4 to specify manually.")
        sys.exit(1)

    print(f"  RFID port:    {port}")
    print(f"  Tags to scan: {args.count} ({args.prefix}-{args.start} to {args.prefix}-{args.start + args.count - 1})")
    print(f"  Scan time:    {args.scan_time}s per tag")
    print()

    # Open port
    ser = open_rfid_port(port)
    if not ser:
        sys.exit(1)

    time.sleep(0.5)
    ser.reset_input_buffer()
    print("  [OK] Reader connected")
    print()

    # Load existing map
    tag_map = load_tag_map()
    registered = {}

    print("-" * 60)
    print()
    print("  Hold each tag near the reader when prompted.")
    print("  Press ENTER when ready, or 'skip' to skip, 'q' to quit.")
    print()

    try:
        for i in range(args.count):
            tag_num = args.start + i
            tag_name = f"{args.prefix}-{tag_num}"

            # Check if already registered
            if tag_name in tag_map and not tag_map[tag_name].startswith("TAG-"):
                print(f"  [{tag_name}] Already registered: {tag_map[tag_name][:30]}...")
                overwrite = input(f"    Re-scan? (y/n): ").strip().lower()
                if overwrite != 'y':
                    print()
                    continue

            print(f"  --- {tag_name} ({i+1}/{args.count}) ---")
            cmd = input(f"  Hold tag near reader, then press ENTER: ").strip().lower()

            if cmd == 'q':
                print("\n  Quitting registration.")
                break
            if cmd == 'skip':
                print(f"  [SKIP] {tag_name}")
                print()
                continue

            # Scan
            print(f"  Scanning for {args.scan_time}s...", end="", flush=True)
            tag_id, read_count = scan_tag(ser, args.scan_time)

            if tag_id:
                print(f" OK! ({read_count} reads)")
                print(f"    Tag ID: {tag_id}")

                # Check for duplicates
                for existing_name, existing_id in tag_map.items():
                    if existing_id == tag_id and existing_name != tag_name:
                        print(f"    [WARNING] Same ID already registered as '{existing_name}'")

                tag_map[tag_name] = tag_id
                registered[tag_name] = tag_id

                # Save after each successful scan
                save_tag_map(tag_map)
                print(f"    [SAVED] {tag_name} -> {tag_id[:30]}...")
            else:
                print(f" NO TAG DETECTED!")
                print(f"    Make sure the tag is close to the reader.")
                retry = input(f"    Retry? (y/n): ").strip().lower()
                if retry == 'y':
                    print(f"  Scanning again for {args.scan_time}s...", end="", flush=True)
                    tag_id, read_count = scan_tag(ser, args.scan_time)
                    if tag_id:
                        print(f" OK! ({read_count} reads)")
                        print(f"    Tag ID: {tag_id}")
                        tag_map[tag_name] = tag_id
                        registered[tag_name] = tag_id
                        save_tag_map(tag_map)
                        print(f"    [SAVED] {tag_name} -> {tag_id[:30]}...")
                    else:
                        print(f" Still no tag. Skipping {tag_name}.")

            print()

    except KeyboardInterrupt:
        print("\n\n  Interrupted!")
    finally:
        ser.close()
        print()
        print("=" * 60)
        print("  REGISTRATION SUMMARY")
        print("=" * 60)
        print()
        if registered:
            print(f"  Successfully registered {len(registered)} tags:")
            print()
            print(f"  {'Name':<10} {'Tag ID'}")
            print(f"  {'-'*10} {'-'*44}")
            for name, tid in sorted(registered.items()):
                print(f"  {name:<10} {tid[:44]}")
            print()
            print(f"  Saved to: {TAG_MAP_FILE.name}")
        else:
            print("  No tags were registered.")
        print()
        print("  [OK] Port closed.")
        print()


if __name__ == "__main__":
    main()
