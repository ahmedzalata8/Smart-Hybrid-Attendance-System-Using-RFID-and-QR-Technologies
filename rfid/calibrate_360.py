#!/usr/bin/env python3
"""
Stepper 360 Calibration Tool
==============================
Manually type a number of steps to send each time.
Helps you figure out exactly how many steps = one full 360 platform rotation.

Usage:
  python calibrate_360.py --port COM3
"""

import sys
import argparse
import serial
import serial.tools.list_ports
import time
import json
from pathlib import Path

BAUD = 115200
CONFIG_FILE = Path(__file__).parent / "room_config.json"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"steps_per_revolution": 1600, "steps_per_press": 1}


def detect_stepper_port():
    for p in serial.tools.list_ports.comports():
        if 'CP210' in (p.description or '').upper():
            return p.device
    return None


def send_steps(ser, direction, count, timeout=30.0):
    """Send step commands and wait for DONE.

    Sends in small paced chunks to prevent ESP32 serial buffer overflow,
    which causes missed steps and positional drift.
    """
    cmd = direction.encode()
    chunk = 64  # Small chunks to avoid ESP32 RX buffer overflow (128 bytes)
    for i in range(0, count, chunk):
        batch = min(chunk, count - i)
        ser.write(cmd * batch)
        ser.flush()
        # Drain any responses from ESP32 between chunks
        while ser.in_waiting:
            ser.readline()
        # Pace the sends so the ESP32 can process them
        time.sleep(0.05)

    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if 'DONE' in line:
                return True
        time.sleep(0.01)
    return False


def main():
    parser = argparse.ArgumentParser(description="Stepper 360 Calibration Tool")
    parser.add_argument('--port', type=str, default=None, help='ESP32 serial port (e.g. COM3)')
    args = parser.parse_args()

    config = load_config()
    steps_per_rev = config["steps_per_revolution"]

    print()
    print("=" * 60)
    print("  STEPPER 360 CALIBRATION TOOL")
    print("=" * 60)
    print()
    print(f"  Steps per motor revolution:  {steps_per_rev}")
    print(f"  Current motor1_revolutions_per_360 = {config.get('motor1_revolutions_per_360', 'not set')}")
    print()
    print("  Type a number of STEPS to send (e.g. 400, 1600, 3200)")
    print("  The motor will turn that many steps each time.")
    print("  Use negative numbers to reverse (e.g. -1600)")
    print()
    print("  Commands:")
    print("    <number>  = send that many steps (negative = reverse)")
    print("    r         = reset step counter to 0")
    print("    s         = save current total as 360 value")
    print("    q         = quit")
    print()

    port = args.port or detect_stepper_port()
    if not port:
        print("  ERROR: No stepper port found. Use --port COM3")
        for p in serial.tools.list_ports.comports():
            print(f"    {p.device} - {p.description}")
        sys.exit(1)

    print(f"  Stepper port: {port}")

    try:
        ser = serial.Serial(port, BAUD, timeout=0.1)
    except serial.SerialException as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print("  Waiting for ESP32 boot...")
    time.sleep(3)
    while ser.in_waiting:
        ser.readline()
    print("  [OK] Connected")
    print()
    print("-" * 60)

    total_steps = 0

    try:
        while True:
            cmd = input(f"\n  [{total_steps} total steps] Enter steps (or r/s/q): ").strip()

            if not cmd:
                continue

            if cmd.lower() == 'q':
                print("\n  Quitting...")
                break

            if cmd.lower() == 'r':
                total_steps = 0
                print("  [RESET] Step counter = 0")
                continue

            if cmd.lower() == 's':
                if total_steps <= 0:
                    print("  ERROR: Total steps must be > 0 to save")
                    continue
                revs = total_steps / steps_per_rev
                print()
                print("=" * 60)
                print(f"  RESULT:")
                print(f"    Total steps for 360:       {total_steps}")
                print(f"    Motor revolutions:         {revs:.2f}")
                print(f"    Rounded revolutions:       {round(revs)}")
                print("=" * 60)
                print()

                save = input(f"  Save motor1_revolutions_per_360 = {round(revs)} to config? (y/n): ").strip().lower()
                if save == 'y':
                    config["motor1_revolutions_per_360"] = round(revs)
                    config["_comment"] = (
                        f"motor1_revolutions_per_360={round(revs)} means "
                        f"{round(revs)} motor shaft revolutions = 1 full platform rotation. "
                        f"Total steps for 360 = {round(revs) * steps_per_rev}."
                    )
                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config, f, indent=2)
                    print(f"  [SAVED] {CONFIG_FILE.name}")
                    print(f"\n  Use in scan_360.py:")
                    print(f"    python scan_360.py --revolutions {round(revs)} --stepper {port} --rfid COM4")
                continue

            try:
                steps = int(cmd)
            except ValueError:
                print("  ERROR: Enter a number, 'r', 's', or 'q'")
                continue

            if steps == 0:
                ser.write(b'0')
                ser.flush()
                print("  [STOP] Motors halted")
                continue

            direction = 'R' if steps > 0 else 'L'
            abs_steps = abs(steps)

            print(f"  Sending {abs_steps} steps ({direction})...", end="", flush=True)
            ok = send_steps(ser, direction, abs_steps, timeout=30.0)
            total_steps += steps

            if ok:
                print(f" done.")
            else:
                print(f" (timeout - motor may still be moving)")

            revs_so_far = total_steps / steps_per_rev
            print(f"  Total steps: {total_steps}  ({revs_so_far:.2f} motor revolutions)")

    except KeyboardInterrupt:
        print("\n\n  Interrupted!")
        ser.write(b'0')
        ser.flush()
    finally:
        ser.write(b'0')
        ser.flush()
        time.sleep(0.2)
        ser.close()
        print("  [OK] Port closed.")
        print()


if __name__ == "__main__":
    main()
