#!/usr/bin/env python3
"""
RFID Reader (Cross-platform)
Reads RFID tags from R16-12DB reader.
Auto-detects serial port on Windows and Linux.

Usage:
  python rfid_reader.py              # Auto-detect port
  python rfid_reader.py --port COM4  # Specify port manually
"""

import sys
import os
import argparse
import serial
import serial.tools.list_ports
import time
import threading
import logging
from typing import Optional, Callable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Frame format streamed by the reader (active/auto-output mode):
#   STX(0x02) + decimal card number + 2-char hex RSSI + CRLF(0x0D0A) + ETX(0x03)
# e.g.  02 "4187574790" "BE" 0D0A 03
STX = 0x02
ETX = 0x03
RSSI_LEN = 2


class RFIDReader:
    """
    Simple RFID reader for R16-12DB.
    Reads the STX..ETX decimal+RSSI frame stream at 9600 baud.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 9600):
        """
        Initialize RFID reader

        Args:
            port: Serial port (default /dev/ttyUSB0 on Raspberry Pi)
            baud: Baud rate (9600 for R16-12DB; 19200 mis-samples on CH340)
        """
        self.port = port
        self.baud = baud
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.read_thread: Optional[threading.Thread] = None
        
        # Callback for tag detection: called as callback(tag_id, rssi_hex)
        self.on_tag_callback: Optional[Callable[[str, str], None]] = None
        
        # Tag deduplication
        self.last_tag_id: Optional[str] = None
        self.last_tag_time: float = 0
        self.dedupe_window: float = 1.0  # Ignore same tag within 1 second
        
    def register_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register callback function for tag detection
        
        Args:
            callback: Function that receives tag_id when detected
        """
        self.on_tag_callback = callback
        logging.info("Tag detection callback registered")
    
    def connect(self) -> bool:
        """
        Connect to RFID reader serial port
        
        Returns:
            bool: True if connected successfully
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=0.2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Clear any buffered data
            time.sleep(0.1)
            self.serial_conn.reset_input_buffer()
            
            logging.info(f"Connected to RFID reader: {self.port} at {self.baud} baud")
            return True
            
        except serial.SerialException as e:
            logging.error(f"Failed to connect to {self.port}: {e}")
            logging.error("Make sure:")
            logging.error("  1. Reader is connected via USB")
            logging.error("  2. Port exists: ls /dev/ttyUSB*")
            logging.error("  3. User has permission: sudo usermod -a -G dialout $USER")
            return False
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from serial port"""
        self.stop()
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logging.info("Disconnected from RFID reader")
    
    def _extract_frames(self, buffer: bytearray) -> tuple[list[bytes], bytearray]:
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

    def _parse_frame(self, payload: bytes) -> tuple[Optional[str], str]:
        """Split a frame payload into (card_number, rssi_hex).

        Card = leading decimal digits; RSSI = the 2 hex chars before CRLF.
        """
        text = payload.split(b"\r")[0]               # drop CRLF and trailing
        rssi = ""
        if len(text) > RSSI_LEN:
            rssi = text[-RSSI_LEN:].decode("ascii", "ignore").upper()
            text = text[:-RSSI_LEN]                  # remainder = card number
        digits = bytes(b for b in text if 0x30 <= b <= 0x39)
        card = digits.decode("ascii") if digits else None
        return card, rssi
    
    def _should_process_tag(self, tag_id: str) -> bool:
        """
        Check if tag should be processed (deduplication)
        
        Args:
            tag_id: Detected tag ID
            
        Returns:
            bool: True if should process, False if duplicate
        """
        current_time = time.time()
        
        # Check if same tag within dedupe window
        if (tag_id == self.last_tag_id and 
            current_time - self.last_tag_time < self.dedupe_window):
            return False
        
        # Update last seen
        self.last_tag_id = tag_id
        self.last_tag_time = current_time
        
        return True
    
    def _read_loop(self) -> None:
        """Main reading loop (runs in separate thread)"""
        buffer = bytearray()
        
        logging.info("RFID reader loop started")
        
        while self.running:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    logging.warning("Serial connection lost, attempting reconnect...")
                    time.sleep(2)
                    if not self.connect():
                        continue
                
                # Read available data
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    buffer.extend(data)

                    # Pull out every complete frame and process it
                    frames, buffer = self._extract_frames(buffer)
                    for payload in frames:
                        tag_id, rssi = self._parse_frame(payload)

                        if tag_id and self._should_process_tag(tag_id):
                            logging.info(f"Tag detected: {tag_id}  RSSI={rssi}")

                            # Call callback if registered
                            if self.on_tag_callback:
                                try:
                                    self.on_tag_callback(tag_id, rssi)
                                except Exception as e:
                                    logging.error(f"Error in tag callback: {e}")

                    # Prevent buffer overflow on a garbled stream
                    if len(buffer) > 512:
                        buffer.clear()
                
                time.sleep(0.05)  # 50ms poll interval
                
            except serial.SerialException as e:
                if "returned no data" not in str(e):  # Ignore transient errors
                    logging.warning(f"Serial error: {e}")
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Error in read loop: {e}", exc_info=True)
                time.sleep(1)
        
        logging.info("RFID reader loop stopped")
    
    def start(self) -> bool:
        """
        Start reading tags in background thread
        
        Returns:
            bool: True if started successfully
        """
        if self.running:
            logging.warning("Reader already running")
            return True
        
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return False
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        
        logging.info("RFID reader started")
        return True
    
    def stop(self) -> None:
        """Stop reading tags"""
        if not self.running:
            return
        
        self.running = False
        
        if self.read_thread:
            self.read_thread.join(timeout=2.0)
        
        logging.info("RFID reader stopped")


def detect_rfid_port() -> Optional[str]:
    """Auto-detect the RFID reader serial port.
    
    On Windows: looks for CH340/CH9102 (common for RFID readers),
    skipping CP210x (usually the ESP32 stepper controller).
    On Linux: defaults to /dev/ttyUSB0.
    """
    if os.name != 'nt':
        # Linux/macOS — use traditional path
        if os.path.exists('/dev/ttyUSB0'):
            return '/dev/ttyUSB0'
        # Try to find any ttyUSB device
        import glob
        usb_ports = glob.glob('/dev/ttyUSB*')
        return usb_ports[0] if usb_ports else None

    # Windows — scan COM ports
    rfid_keywords = ['CH340', 'CH9102', 'USB-SERIAL', 'FTDI']
    esp32_keywords = ['CP210']  # Skip these — likely the stepper ESP32

    ports = serial.tools.list_ports.comports()
    candidates = []

    for port in ports:
        desc = (port.description or '').upper()
        mfr = (port.manufacturer or '').upper()
        device = port.device.upper()

        # Skip COM1 (built-in) and CP210x (ESP32)
        if device == 'COM1':
            continue
        if any(kw.upper() in desc for kw in esp32_keywords):
            continue

        # Prefer known RFID reader chips
        for kw in rfid_keywords:
            if kw.upper() in desc or kw.upper() in mfr:
                candidates.insert(0, port)  # High priority
                break
        else:
            candidates.append(port)  # Low priority fallback

    return candidates[0].device if candidates else None


def main():
    """Test the RFID reader"""
    parser = argparse.ArgumentParser(description="RFID Reader")
    parser.add_argument('--port', type=str, default=None,
                        help='Serial port for RFID reader (e.g. COM4 on Windows, /dev/ttyUSB0 on Linux)')
    args = parser.parse_args()

    print("="*60)
    print("RFID Reader Test")
    print("="*60)
    
    # Determine port
    port = args.port
    if not port:
        print("\n  Auto-detecting RFID reader port...")
        port = detect_rfid_port()
        if port:
            print(f"  Found RFID reader on: {port}")
        else:
            print("  ERROR: No RFID reader serial port detected.")
            print("  Available ports:")
            for p in serial.tools.list_ports.comports():
                print(f"    {p.device} — {p.description}")
            print("  Use --port to specify manually, e.g.: python rfid_reader.py --port COM4")
            sys.exit(1)
    else:
        print(f"\n  Using specified port: {port}")

    # Tag detection callback
    def on_tag_detected(tag_id: str, rssi: str = ""):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        rssi_dec = int(rssi, 16) if rssi else None
        rssi_str = f"{rssi} ({rssi_dec})" if rssi else "--"
        print(f"[{timestamp}] Tag: {tag_id:<12} RSSI: {rssi_str}")

    # Create reader
    reader = RFIDReader(port=port, baud=9600)
    reader.register_callback(on_tag_detected)
    
    # Connect
    if not reader.connect():
        print("\nERROR: Failed to connect to RFID reader")
        print("\nTroubleshooting:")
        if os.name == 'nt':
            print("  1. Check that the RFID reader is connected via USB")
            print("  2. Check Device Manager for available COM ports")
            print("  3. Reconnect the USB cable")
            print(f"  4. Try specifying the port: python rfid_reader.py --port COM4")
        else:
            print("  1. Check connection: ls /dev/ttyUSB*")
            print("  2. Check permissions: sudo usermod -a -G dialout $USER")
            print("  3. Reconnect USB cable")
            print("  4. Try: sudo chmod 666 /dev/ttyUSB0")
        return
    
    # Start reading
    if not reader.start():
        print("\nERROR: Failed to start reader")
        return
    
    print("\n[OK] RFID reader running")
    print("\nScan tags now... (Press Ctrl+C to stop)\n")
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        reader.disconnect()
        print("[OK] Reader stopped")


if __name__ == '__main__':
    main()
