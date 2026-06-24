"""
RFID 360° Scanner Service — runs the stepper+RFID scan as a background task.

Ported from rfid/scan_360.py for integration into the attendance system.
Controls the stepper motor and RFID reader via serial ports to perform
a full 360-degree rotational scan, clustering noisy RFID reads into
physical tags and assigning them to seats.
"""
import asyncio
import logging
import os
import subprocess
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)

# ── Serial config ──
STEPPER_BAUD = 115200
# The R16-12DB outputs its card number at 9600 baud (confirmed by live capture and
# the vendor tool's serial settings). The previous 19200 misread the stream as noise,
# which is why the old parser had to lean on heavy similarity-clustering.
RFID_BAUD = 9600

# Reader output format is "10 no.in D (four byte)" => a 10-digit decimal card number.
# On the wire each read is framed:  STX(0x02) + <10 digits>[+ <RSSI>] + CR LF + ETX(0x03).
# When "Data followed by RSSI" is enabled on the reader, the RSSI text trails the digits.
CARD_DIGITS = 10


# ────────────────────────────────────────────────────────────────────
# CH340 PORT LIFECYCLE — avoid the "stuck port" (Windows error 31)
# ────────────────────────────────────────────────────────────────────
# The reader streams continuously, so closing the port mid-RX — or leaking it
# open when a scan errors — wedges the CH340 into error 31 and forces a
# physical USB replug. Open minimally, close gracefully, and (on Windows, if
# elevated) software-replug the device to recover without touching the cable.

def cycle_ch340_device() -> bool:
    """Disable+re-enable the CH340 via Windows PnP (software 'unplug/replug').

    Resets the chip the way a physical replug does, clearing error 31.
    Requires an elevated process; returns True only if the cycle actually ran.
    """
    if os.name != "nt":
        return False
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
    except Exception as e:
        logger.warning("CH340 device cycle failed to run: %s", e)
        return False
    out = (r.stdout or "") + (r.stderr or "")
    if "CYCLED" in out:
        logger.info("Power-cycled the CH340 via Windows PnP to clear error 31.")
        return True
    if "DENIED" in out or "denied" in out.lower():
        logger.warning("Cannot reset CH340 (need admin). Physical replug required.")
    return False


def open_rfid_port(port: str, retries: int = 4) -> serial.Serial:
    """Open the reader at 9600 (pyserial defaults to 8N1), recovering error 31.

    A short wait rarely clears a stuck CH340, so after the quick retries we
    attempt a software device-cycle (admin only) before giving up.
    """
    last_err = None
    tried_cycle = False
    for attempt in range(retries):
        try:
            return serial.Serial(port, RFID_BAUD, timeout=0.2)
        except serial.SerialException as e:
            last_err = e
            if "31" not in str(e):
                raise
            time.sleep(0.8)
            if attempt == 1 and not tried_cycle:
                tried_cycle = True
                if cycle_ch340_device():
                    time.sleep(1.5)
    raise last_err


def safe_close_serial(ser: "serial.Serial | None") -> None:
    """Close a CH340 port cleanly so it doesn't wedge into error 31.

    Drain buffers and drop DTR/RTS before closing, with brief pauses, so the
    driver releases the handle properly instead of locking up mid-RX.
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


# ────────────────────────────────────────────────────────────────────
# PORT DETECTION (ported from scan_360.py)
# ────────────────────────────────────────────────────────────────────

def detect_stepper_port() -> str | None:
    """Detect ESP32 stepper controller (CP210x)."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").upper()
        if "CP210" in desc:
            return p.device
    for p in ports:
        if p.device.upper() != "COM1":
            return p.device
    return None


def detect_rfid_port() -> str | None:
    """Detect RFID reader (CH340)."""
    rfid_kw = ["CH340", "CH9102", "USB-SERIAL", "FTDI"]
    esp32_kw = ["CP210"]

    ports = serial.tools.list_ports.comports()
    candidates = []
    for p in ports:
        desc = (p.description or "").upper()
        mfr = (p.manufacturer or "").upper()
        if p.device.upper() == "COM1":
            continue
        if any(k in desc for k in esp32_kw):
            continue
        for k in rfid_kw:
            if k in desc or k in mfr:
                candidates.insert(0, p)
                break
        else:
            candidates.append(p)
    return candidates[0].device if candidates else None


# ────────────────────────────────────────────────────────────────────
# RFID PARSING + CLUSTERING (ported from scan_360.py)
# ────────────────────────────────────────────────────────────────────

def _rssi_to_int(rssi: str | None) -> int | None:
    """Best-effort numeric RSSI. Exact format depends on reader config, so we keep
    the raw string too; here we just try decimal then hex."""
    if not rssi:
        return None
    try:
        return int(rssi)
    except ValueError:
        try:
            return int(rssi, 16)
        except ValueError:
            return None


def parse_rfid_data(buffer: bytearray) -> tuple[str | None, str | None, int]:
    """Parse one STX..ETX frame out of the rolling serial buffer.

    Returns (tag_id, rssi, consumed):
      tag_id   : 10-digit decimal card number, or None if no complete frame yet
      rssi     : trailing RSSI text when the reader appends it, else None
      consumed : number of bytes to drop from the front of the buffer
    """
    start = buffer.find(0x02)            # STX
    if start == -1:
        return None, None, len(buffer)   # no frame start in buffer: drop the junk
    end = buffer.find(0x03, start + 1)   # ETX
    if end == -1:
        # incomplete frame: drop any junk before STX, keep the partial for next read
        return None, None, start
    consumed = end + 1
    text = bytes(buffer[start + 1:end]).replace(b"\r", b"").replace(b"\n", b"").strip()
    try:
        text = text.decode("ascii")
    except UnicodeDecodeError:
        return None, None, consumed
    if len(text) < CARD_DIGITS or not text[:CARD_DIGITS].isdigit():
        return None, None, consumed      # not a valid card frame
    tag_id = text[:CARD_DIGITS]
    rssi = text[CARD_DIGITS:].strip() or None
    return tag_id, rssi, consumed


def string_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    min_len = min(len(a), len(b))
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    matches = sum(1 for i in range(min_len) if a[i] == b[i])
    return matches / max_len


def cluster_tags(
    detections: list[dict], similarity_threshold: float = 0.92
) -> tuple[dict, list[dict]]:
    """Cluster noisy RFID reads into physical tag groups."""
    freq: dict[str, int] = defaultdict(int)
    for d in detections:
        freq[d["tag_id"]] += 1

    sorted_tags = sorted(freq.keys(), key=lambda t: freq[t], reverse=True)
    clusters: list[dict] = []

    for tag_id in sorted_tags:
        best_cluster = None
        best_sim = 0.0
        for cluster in clusters:
            sim = string_similarity(tag_id, cluster["representative"])
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster
        if best_cluster and best_sim >= similarity_threshold:
            best_cluster["members"].append(tag_id)
            best_cluster["total_count"] += freq[tag_id]
        else:
            clusters.append({
                "representative": tag_id,
                "members": [tag_id],
                "total_count": freq[tag_id],
            })

    clusters.sort(key=lambda c: c["total_count"], reverse=True)
    tag_to_cluster = {}
    for idx, cluster in enumerate(clusters):
        for member in cluster["members"]:
            tag_to_cluster[member] = idx
    return tag_to_cluster, clusters


# ────────────────────────────────────────────────────────────────────
# STEPPER COMMUNICATION
# ────────────────────────────────────────────────────────────────────

def send_steps(ser: serial.Serial, direction: str, count: int, timeout: float = 15.0) -> bool:
    cmd = direction.encode()
    chunk = 64
    for i in range(0, count, chunk):
        batch = min(chunk, count - i)
        ser.write(cmd * batch)
        ser.flush()
        while ser.in_waiting:
            ser.readline()
        time.sleep(0.05)
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if "DONE" in line:
                return True
        time.sleep(0.01)
    return False


# ────────────────────────────────────────────────────────────────────
# BACKGROUND RFID SCANNER THREAD
# ────────────────────────────────────────────────────────────────────

class RFIDScannerThread:
    """Reads the RFID serial port in a background thread."""

    def __init__(self, rfid_ser: serial.Serial):
        self.ser = rfid_ser
        self.running = False
        self.thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.current_angle = 0.0
        self.current_step = 0
        self.current_position_index = 0
        self.detections: list[dict] = []
        self._last_tag: str | None = None
        self._last_tag_time = 0.0
        self._dedupe_window = 0.3

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def set_position(self, angle: float, step: int, index: int):
        with self._lock:
            self.current_angle = angle
            self.current_step = step
            self.current_position_index = index

    def get_detections(self) -> list[dict]:
        with self._lock:
            return list(self.detections)

    def _scan_loop(self):
        buffer = bytearray()
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)
                    while buffer:
                        tag_id, rssi, consumed = parse_rfid_data(buffer)
                        if consumed == 0:
                            break
                        buffer = buffer[consumed:]
                        if tag_id and self._should_record(tag_id):
                            with self._lock:
                                self.detections.append({
                                    "tag_id": tag_id,
                                    "rssi": rssi,
                                    "rssi_value": _rssi_to_int(rssi),
                                    "angle_deg": round(self.current_angle, 2),
                                    "step": self.current_step,
                                    "position_index": self.current_position_index,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "time_epoch": time.time(),
                                })
                    if len(buffer) > 512:
                        buffer.clear()
                time.sleep(0.02)
            except Exception:
                time.sleep(0.1)

    def _should_record(self, tag_id: str) -> bool:
        now = time.time()
        if tag_id == self._last_tag and now - self._last_tag_time < self._dedupe_window:
            return False
        self._last_tag = tag_id
        self._last_tag_time = now
        return True


# ────────────────────────────────────────────────────────────────────
# SCAN SERVICE (singleton managed by the FastAPI app)
# ────────────────────────────────────────────────────────────────────

class ScanStatus:
    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    ERROR = "error"


class ScannerService:
    """Manages 360° RFID scans.  One scan at a time."""

    def __init__(self):
        self._status = ScanStatus.IDLE
        self._progress: float = 0.0
        self._detections_count: int = 0
        self._scan_id: str | None = None
        self._session_id: str | None = None
        self._results: dict[str, Any] | None = None
        self._error: str | None = None
        self._lock = threading.Lock()
        self._scan_thread: threading.Thread | None = None

        # Config defaults
        self.total_steps = 2035
        self.num_positions = 16
        self.similarity = 0.92
        self.stepper_port: str | None = None
        self.rfid_port: str | None = None

    # ── Public API ──

    @property
    def status(self) -> dict:
        with self._lock:
            return {
                "status": self._status,
                "scan_id": self._scan_id,
                "session_id": self._session_id,
                "progress": round(self._progress, 1),
                "detections_count": self._detections_count,
                "error": self._error,
            }

    @property
    def results(self) -> dict | None:
        with self._lock:
            return self._results

    def start_scan(
        self,
        session_id: str,
        tag_map: dict[str, str],
        stepper_port: str | None = None,
        rfid_port: str | None = None,
    ) -> dict:
        """
        Kick off a 360° scan in a background thread.

        Args:
            session_id:   attendance session UUID
            tag_map:      {tag_hex_id: tag_label} from the seats table
            stepper_port: e.g. "COM3"  (auto-detect if None)
            rfid_port:    e.g. "COM4"  (auto-detect if None)

        Returns:
            dict with scan_id and status.
        """
        with self._lock:
            if self._status == ScanStatus.SCANNING:
                return {"error": "Scan already in progress", "status": self._status}
            self._scan_id = str(uuid.uuid4())
            self._session_id = session_id
            self._status = ScanStatus.SCANNING
            self._progress = 0.0
            self._detections_count = 0
            self._results = None
            self._error = None

        sp = stepper_port or self.stepper_port or detect_stepper_port()
        rp = rfid_port or self.rfid_port or detect_rfid_port()

        self._scan_thread = threading.Thread(
            target=self._run_scan,
            args=(self._scan_id, session_id, tag_map, sp, rp),
            daemon=True,
        )
        self._scan_thread.start()

        return {"scan_id": self._scan_id, "status": ScanStatus.SCANNING}

    # ── Background scan worker ──

    def _run_scan(
        self,
        scan_id: str,
        session_id: str,
        tag_map: dict[str, str],
        stepper_port: str | None,
        rfid_port: str | None,
    ):
        """Runs the full 360° scan (blocking, in background thread)."""
        stepper_ser: serial.Serial | None = None
        rfid_ser: serial.Serial | None = None
        scanner: RFIDScannerThread | None = None
        try:
            if not stepper_port or not rfid_port:
                raise RuntimeError(
                    f"Missing serial ports: stepper={stepper_port}, rfid={rfid_port}"
                )
            if stepper_port == rfid_port:
                raise RuntimeError(f"Both devices on same port: {stepper_port}")

            logger.info("Opening stepper port %s ...", stepper_port)
            stepper_ser = serial.Serial(stepper_port, STEPPER_BAUD, timeout=0.1)

            logger.info("Opening RFID port %s ...", rfid_port)
            rfid_ser = open_rfid_port(rfid_port)

            # Wait for ESP32 boot
            time.sleep(3)
            while stepper_ser.in_waiting:
                stepper_ser.readline()
            time.sleep(0.1)
            rfid_ser.reset_input_buffer()

            # Start RFID scanner thread
            scanner = RFIDScannerThread(rfid_ser)
            scanner.start()

            steps_per_position = self.total_steps // self.num_positions
            deg_per_position = 360.0 / self.num_positions
            scan_start = time.time()
            total_sent = 0

            logger.info("Starting 360° scan: %d positions, %d steps",
                        self.num_positions, self.total_steps)

            # Forward sweep
            for pos_idx in range(self.num_positions):
                angle = pos_idx * deg_per_position

                with self._lock:
                    self._progress = (pos_idx / self.num_positions) * 100
                    self._detections_count = len(scanner.get_detections())

                scanner.set_position(angle, total_sent, pos_idx)

                if pos_idx < self.num_positions - 1:
                    ok = send_steps(stepper_ser, "R", steps_per_position, timeout=15.0)
                    if not ok:
                        logger.warning("Timeout at position %d", pos_idx + 1)
                    total_sent += steps_per_position

            # Final position
            scanner.set_position(360.0, total_sent, self.num_positions - 1)
            time.sleep(0.5)

            # Stop scanner, gather results
            scanner.stop()
            raw_detections = scanner.get_detections()
            scan_duration = time.time() - scan_start

            logger.info("Scan complete: %d raw detections in %.1fs",
                        len(raw_detections), scan_duration)

            # Cluster tags
            tag_to_cluster, clusters = cluster_tags(raw_detections, self.similarity)

            # Assign labels from known tag map using SIMILARITY matching
            # (RFID reads are noisy — exact match rarely works)
            for idx, cluster in enumerate(clusters):
                canonical = cluster["representative"]
                known_label = None

                # Try exact match first
                for member in cluster["members"]:
                    if member in tag_map:
                        known_label = tag_map[member]
                        break

                # Fall back to similarity match against all known hex IDs
                if not known_label:
                    best_sim = 0.0
                    for known_hex, known_lbl in tag_map.items():
                        for member in cluster["members"]:
                            sim = string_similarity(member, known_hex)
                            if sim > best_sim:
                                best_sim = sim
                                if sim >= 0.75:  # similarity threshold for tag map matching
                                    known_label = known_lbl

                cluster["label"] = known_label or f"Unknown-{idx + 1}"
                cluster["canonical_id"] = canonical
                cluster["matched_known_hex"] = None
                if known_label:
                    # Store the matched known hex for apply-results mapping
                    for kh, kl in tag_map.items():
                        if kl == known_label:
                            cluster["matched_known_hex"] = kh
                            break

            # Build per-tag summary with quadrant data
            cluster_labels = {idx: c["label"] for idx, c in enumerate(clusters)}
            clustered_detections = []
            for d in raw_detections:
                if d["tag_id"] in tag_to_cluster:
                    ci = tag_to_cluster[d["tag_id"]]
                    enriched = dict(d)
                    enriched["cluster_id"] = ci
                    enriched["label"] = cluster_labels[ci]
                    enriched["canonical_tag_id"] = clusters[ci]["canonical_id"]
                    clustered_detections.append(enriched)

            tags_summary = {}
            for idx, cluster in enumerate(clusters):
                label = cluster["label"]
                cds = [d for d in clustered_detections if d["cluster_id"] == idx]
                angles = sorted(set(d["angle_deg"] for d in cds))
                qh = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
                for d in cds:
                    a = d["angle_deg"] % 360
                    if a < 90:
                        qh["Q1"] += 1
                    elif a < 180:
                        qh["Q2"] += 1
                    elif a < 270:
                        qh["Q3"] += 1
                    else:
                        qh["Q4"] += 1
                best_q = max(qh, key=qh.get)

                # RSSI stats (only populated once "Data followed by RSSI" is enabled
                # on the reader). Higher/lower-is-closer depends on the reader's scale,
                # so we expose raw samples plus avg/max for downstream seat logic.
                rssi_vals = [d["rssi_value"] for d in cds if d.get("rssi_value") is not None]
                rssi_avg = round(sum(rssi_vals) / len(rssi_vals), 1) if rssi_vals else None
                rssi_max = max(rssi_vals) if rssi_vals else None

                tags_summary[label] = {
                    "canonical_tag_id": cluster["canonical_id"],
                    "matched_known_hex": cluster.get("matched_known_hex"),
                    "detection_count": len(cds),
                    "raw_variant_count": len(cluster["members"]),
                    "angles_detected": angles,
                    "quadrant_hits": qh,
                    "best_quadrant": best_q,
                    "rssi_avg": rssi_avg,
                    "rssi_max": rssi_max,
                    "rssi_samples": rssi_vals,
                    "first_seen": cds[0]["timestamp"] if cds else None,
                    "last_seen": cds[-1]["timestamp"] if cds else None,
                }

            results = {
                "scan_id": scan_id,
                "session_id": session_id,
                "scan_info": {
                    "duration_seconds": round(scan_duration, 2),
                    "scan_mode": "single_pass",
                    "num_positions": self.num_positions,
                    "degrees_per_position": deg_per_position,
                    "steps_per_position": steps_per_position,
                    "stepper_port": stepper_port,
                    "rfid_port": rfid_port,
                    "similarity_threshold": self.similarity,
                    "raw_detection_count": len(raw_detections),
                },
                "tags_found": len(tags_summary),
                "tags_summary": tags_summary,
                "clustered_detections": clustered_detections,
            }

            with self._lock:
                self._results = results
                self._progress = 100.0
                self._detections_count = len(raw_detections)
                self._status = ScanStatus.COMPLETED

            logger.info("Scan %s completed: %d tags found", scan_id, len(tags_summary))

        except Exception as e:
            logger.error("Scan failed: %s", e, exc_info=True)
            with self._lock:
                self._status = ScanStatus.ERROR
                self._error = str(e)
        finally:
            # ALWAYS release the ports — even on error — so the CH340 doesn't
            # wedge into Windows error 31 (which forces a physical USB replug).
            if scanner is not None:
                scanner.stop()
            if stepper_ser is not None:
                try:
                    stepper_ser.write(b"0")   # stop the motor
                    stepper_ser.flush()
                    time.sleep(0.2)
                except Exception:
                    pass
                try:
                    stepper_ser.close()
                except Exception:
                    pass
            safe_close_serial(rfid_ser)        # graceful CH340 close


# Module-level singleton
scanner_service = ScannerService()
