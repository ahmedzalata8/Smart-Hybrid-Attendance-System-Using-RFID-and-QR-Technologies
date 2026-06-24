#!/usr/bin/env python3
"""
RFID Reader Live Input Scanner
==============================
Probes COM4, COM5, COM3 for the R16-12DB UHF reader, opens the first one
that produces data at 9600 baud, and prints each decoded tag read live.

The reader is in active/auto-output mode and streams each tag as:
    STX(0x02) + ASCII-decimal-card-number + RSSI bytes + CRLF(0x0D0A) + ETX(0x03)

Usage:
  python scan_input.py                  # auto-probe COM4, COM5, COM3
  python scan_input.py --port COM4      # force a specific port
  python scan_input.py --raw            # also show raw hex of each frame
  python scan_input.py --ports COM4 COM6
"""

import sys
import time
import argparse
import subprocess

import serial
import serial.tools.list_ports

RFID_BAUD = 9600          # reader actually streams at 9600 (NOT 19200)
DEFAULT_PORTS = ["COM4", "COM5", "COM3"]

STX = 0x02
ETX = 0x03
RSSI_LEN = 2              # frame ends with a 2-char hex RSSI before CRLF


def cycle_ch340_device() -> bool:
    """Software 'unplug/replug': disable then re-enable the CH340 in Windows.

    This resets the chip the same way a physical replug does, which is what
    clears the stuck error-31 state. Requires an *elevated* (admin) shell --
    Disable/Enable-PnpDevice need it. Returns True if the cycle ran.
    """
    ps = (
        "$ErrorActionPreference='Stop';"
        "$d = Get-PnpDevice -Class Ports -PresentOnly | "
        "  Where-Object { $_.FriendlyName -match 'CH340' };"
        "if (-not $d) { Write-Output 'NODEV'; exit 0 }"
        "foreach ($dev in $d) {"
        "  try {"
        "    Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false;"
        "    Start-Sleep -Milliseconds 700;"
        "    Enable-PnpDevice  -InstanceId $dev.InstanceId -Confirm:$false;"
        "  } catch { Write-Output 'DENIED'; exit 1 }"
        "}"
        "Write-Output 'CYCLED'"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:
        return False
    out = (r.stdout or "") + (r.stderr or "")
    if "CYCLED" in out:
        print("  [recover] Power-cycled the CH340 via Windows. Retrying...")
        return True
    if "DENIED" in out or "AccessDenied" in out or "denied" in out.lower():
        print("  [recover] Can't reset device -- need an ADMIN terminal "
              "(or just unplug/replug the USB).")
    elif "NODEV" in out:
        print("  [recover] No CH340 device found to reset.")
    return False


def open_port(port: str, retries: int = 4) -> serial.Serial:
    """Open a port at the reader's 9600 baud (pyserial defaults to 8N1).

    On Windows error 31 ("device is not functioning") the CH340 is stuck.
    A short wait rarely clears it, so after a couple of quick retries we try a
    software device-cycle (admin only) before giving up.
    """
    last_err = None
    tried_cycle = False
    for attempt in range(retries):
        try:
            # Minimal constructor: same form that opens reliably for this CH340.
            return serial.Serial(port, RFID_BAUD, timeout=0.2)
        except serial.SerialException as e:
            last_err = e
            if "31" not in str(e):
                raise
            time.sleep(0.8)            # transient case: let the driver settle
            # After the quick retries fail, attempt a software replug once.
            if attempt == 1 and not tried_cycle:
                tried_cycle = True
                if cycle_ch340_device():
                    time.sleep(1.5)
    raise last_err


def safe_close(ser: serial.Serial):
    """Close a CH340 port cleanly so it doesn't wedge (Windows error 31).

    The reader streams continuously, so a plain close() often happens mid-RX
    and locks up the CH340. Drain buffers and drop the control lines first,
    with a brief pause, so the driver releases the port properly.
    """
    if ser is None:
        return
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    try:
        ser.dtr = False
        ser.rts = False
    except Exception:
        pass
    time.sleep(0.15)
    try:
        ser.close()
    except Exception:
        pass
    time.sleep(0.15)


def probe(ports: list[str], listen: float = 1.5) -> serial.Serial | None:
    """Try each port; return the first that opens AND emits bytes."""
    available = {p.device.upper() for p in serial.tools.list_ports.comports()}
    for port in ports:
        if port.upper() not in available:
            print(f"  [skip] {port}  (not present)")
            continue
        try:
            ser = open_port(port)
        except serial.SerialException as e:
            print(f"  [fail] {port}  ({e})")
            continue

        ser.reset_input_buffer()
        time.sleep(listen)
        n = ser.in_waiting
        if n > 0:
            print(f"  [OK]   {port}  ({n} bytes waiting) -> using this port")
            return ser
        print(f"  [open] {port}  (no data in {listen}s) "
              f"-- present a tag, or it may be the wrong port")
        ser.close()
    return None


def extract_frames(buffer: bytearray) -> tuple[list[bytes], bytearray]:
    """Split the buffer into complete STX..ETX frames; keep the remainder."""
    frames = []
    while True:
        start = buffer.find(STX)
        if start == -1:
            # No STX: drop everything except a trailing partial CRLF.
            return frames, bytearray()
        end = buffer.find(ETX, start + 1)
        if end == -1:
            # Incomplete frame; keep from STX onward.
            return frames, buffer[start:]
        frames.append(bytes(buffer[start + 1:end]))
        buffer = buffer[end + 1:]


def decode_frame(payload: bytes) -> tuple[str, str]:
    """Split a frame payload into (card_number, rssi_hex).

    Frame payload (between STX and ETX) looks like:  4187574790BE\\r\\n
    i.e. the decimal card number, a 2-char hex RSSI, then CRLF.
    Returns ("", "") if no card digits are found.
    """
    text = payload.split(b"\r")[0]          # drop CRLF (and anything after)
    rssi = ""
    if len(text) > RSSI_LEN:
        rssi = text[-RSSI_LEN:].decode("ascii", "ignore").upper()
        text = text[:-RSSI_LEN]             # remaining = card number
    digits = bytes(b for b in text if 0x30 <= b <= 0x39)  # keep '0'-'9'
    card = digits.decode("ascii") if digits else ""
    return card, rssi


def rssi_dbm(rssi_hex: str) -> int | None:
    """Convert the 2-char hex RSSI byte to signed dBm (two's complement).

    e.g. 'BE' -> 0xBE = 190 -> 190-256 = -66 dBm.  Higher (closer to 0) is
    a stronger signal. NOTE: UHF RFID RSSI is non-linear and noisy, so it is
    only a rough proximity hint, not a real distance measurement.
    """
    if not rssi_hex:
        return None
    try:
        v = int(rssi_hex, 16)
    except ValueError:
        return None
    return v - 256 if v > 127 else v


def main():
    parser = argparse.ArgumentParser(description="Live RFID reader input scanner")
    parser.add_argument("port_pos", nargs="?", metavar="PORT",
                        help="Force a specific port positionally (e.g. COM5)")
    parser.add_argument("--port", help="Force a specific port (e.g. COM4)")
    parser.add_argument("--ports", nargs="+", default=DEFAULT_PORTS,
                        help="Ports to probe in order (default: COM4 COM5 COM3)")
    parser.add_argument("--raw", action="store_true",
                        help="Also print raw hex for each frame")
    args = parser.parse_args()

    print()
    print("=" * 56)
    print("  RFID READER LIVE INPUT SCANNER")
    print("=" * 56)
    print()
    print("  Available COM ports:")
    for p in serial.tools.list_ports.comports():
        print(f"    {p.device:<6} {p.description}")
    print()

    forced = args.port or args.port_pos
    if forced:
        try:
            ser = open_port(forced)
            ser.reset_input_buffer()
            print(f"  Forced port {forced} open.")
        except serial.SerialException as e:
            print(f"  ERROR: cannot open {forced}: {e}")
            if "31" in str(e):
                print("  -> CH340 is stuck (error 31). Unplug & replug the "
                      "reader's USB, then retry.")
            sys.exit(1)
    else:
        print(f"  Probing {', '.join(args.ports)} ...")
        ser = probe(args.ports)
        if ser is None:
            print()
            print("  No reader found emitting data.")
            print("  Tip: keep a tag in front of the reader and re-run,")
            print("       or force it with: python scan_input.py COM5")
            print("  If a port reported error 31, the CH340 is stuck --")
            print("  unplug & replug the reader's USB, then retry.")
            sys.exit(1)

    print()
    print(f"  Listening on {ser.port} @ {ser.baudrate} baud. Ctrl+C to stop.")
    print("  " + "-" * 52)

    buffer = bytearray()
    seen = {}          # card -> count
    last_print = {}    # card -> last time printed (simple dedupe)
    rssi_log = {}      # card -> list of dBm values (for min/avg/max)
    total = 0

    try:
        while True:
            n = ser.in_waiting
            if n:
                buffer.extend(ser.read(n))
                frames, buffer = extract_frames(buffer)
                for payload in frames:
                    card, rssi = decode_frame(payload)
                    if not card:
                        continue
                    total += 1
                    seen[card] = seen.get(card, 0) + 1
                    dbm = rssi_dbm(rssi)
                    if dbm is not None:
                        rssi_log.setdefault(card, []).append(dbm)
                    now = time.time()
                    # Dedupe rapid repeats of the same card within 0.4s.
                    if now - last_print.get(card, 0) < 0.4:
                        continue
                    last_print[card] = now
                    stamp = time.strftime("%H:%M:%S")
                    rssi_str = f"{dbm:>4} dBm" if dbm is not None else "  -- "
                    line = (f"  {stamp}  CARD {card:<12} "
                            f"RSSI {rssi_str}  (x{seen[card]})")
                    if args.raw:
                        line += f"   raw={rssi}={payload.hex().upper()}"
                    print(line)
            else:
                time.sleep(0.02)
    except KeyboardInterrupt:
        print()
        print("  " + "-" * 52)
        print(f"  Stopped. {total} reads, {len(seen)} unique cards:")
        print(f"    {'card':<16} {'reads':>6}   {'RSSI min/avg/max (dBm)':<24}")
        for card, count in sorted(seen.items(), key=lambda kv: -kv[1]):
            vals = rssi_log.get(card, [])
            if vals:
                stats = f"{min(vals):>4} / {sum(vals)/len(vals):>5.1f} / {max(vals):>4}"
            else:
                stats = "--"
            print(f"    {card:<16} {count:>6}   {stats}")
        print()
        print("  Note: RFID RSSI is noisy & non-linear -- use avg over many")
        print("  reads to compare distances, not single samples.")
        print()
    finally:
        safe_close(ser)
        print("  Port closed cleanly.")


if __name__ == "__main__":
    main()
