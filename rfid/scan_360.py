#!/usr/bin/env python3
"""
RFID 360-Degree Scanner (v2)
==============================
Rotates the X-axis stepper motor through a single 360-degree revolution
while scanning for RFID tags. Clusters noisy reads into physical tags
and assigns labels.

Outputs:
  scan_360_results.json  -- structured results with clustered tags
  scan_360_results.csv   -- spreadsheet-friendly detection log
  tag_map.json           -- updated with any newly discovered tags

Usage:
  python scan_360.py                           # Auto-detect, fast defaults
  python scan_360.py --positions 24 --dwell 1.5
  python scan_360.py --max-tags 6              # Expect 6 physical tags
  python scan_360.py --stepper COM3 --rfid COM4
"""

import sys
import os
import argparse
import serial
import serial.tools.list_ports
import time
import json
import csv
import threading
from pathlib import Path
import webbrowser
from datetime import datetime
from collections import defaultdict

# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "room_config.json"
TAG_MAP_FILE = SCRIPT_DIR / "tag_map.json"
RESULTS_JSON = SCRIPT_DIR / "scan_360_results.json"
RESULTS_CSV = SCRIPT_DIR / "scan_360_results.csv"
SCAN_DATA_JS = SCRIPT_DIR / "scan_data.js"

# ============================================================================
# CONFIG
# ============================================================================

STEPPER_BAUD = 115200
RFID_BAUD = 19200


def load_config() -> dict:
    """Load room/motor configuration."""
    defaults = {
        "steps_per_revolution": 1600,
        "steps_per_press": 1,
        "motor1_cm_per_revolution": 8.0,
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
            defaults.update({k: v for k, v in loaded.items() if not k.startswith("_")})
        except Exception:
            pass
    return defaults


def load_tag_map() -> dict:
    """Load tag_map.json as {tag_id: seat_label}."""
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE, "r") as f:
                data = json.load(f)
            # tag_map.json is {seat_label: tag_id} -- invert it
            return {v: k for k, v in data.items() if not v.startswith("TAG-")}
        except Exception:
            pass
    return {}


def save_tag_map_updates(new_tags: dict):
    """Add newly discovered tags to tag_map.json.

    Args:
        new_tags: {label: canonical_tag_id} for tags not already in the map.
    """
    if not new_tags:
        return

    existing = {}
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE, "r") as f:
                existing = json.load(f)
        except Exception:
            pass

    existing.update(new_tags)

    try:
        with open(TAG_MAP_FILE, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"  [SAVED] {TAG_MAP_FILE.name} (added {len(new_tags)} new tags)")
    except Exception as e:
        print(f"  [ERROR] Could not update tag map: {e}")


# ============================================================================
# PORT DETECTION
# ============================================================================

def detect_stepper_port() -> str | None:
    """Detect ESP32 stepper controller (CP210x on Windows)."""
    if os.name != 'nt':
        return None

    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or '').upper()
        if 'CP210' in desc:
            return p.device
    for p in ports:
        if p.device.upper() != 'COM1':
            return p.device
    return None


def detect_rfid_port() -> str | None:
    """Detect RFID reader (CH340 on Windows, /dev/ttyUSB0 on Linux)."""
    if os.name != 'nt':
        if os.path.exists('/dev/ttyUSB0'):
            return '/dev/ttyUSB0'
        return None

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
        if any(kw.upper() in desc for kw in esp32_keywords):
            continue

        for kw in rfid_keywords:
            if kw.upper() in desc or kw.upper() in mfr:
                candidates.insert(0, p)
                break
        else:
            candidates.append(p)

    return candidates[0].device if candidates else None


# ============================================================================
# RFID TAG PARSER
# ============================================================================

def parse_rfid_data(buffer: bytearray) -> tuple[str | None, int]:
    """
    Parse tag ID from RFID reader byte buffer.

    Returns:
        (tag_id or None, bytes_consumed)
    """
    if len(buffer) < 16:
        return None, 0

    chunk_size = min(24, len(buffer))
    chunk = bytes(buffer[:chunk_size])

    # Remove null bytes
    cleaned = bytes(b for b in chunk if b != 0x00)

    if len(cleaned) >= 12:
        tag_id = cleaned.hex().upper()
        return tag_id, chunk_size

    return None, chunk_size


# ============================================================================
# TAG CLUSTERING
# ============================================================================

def string_similarity(a: str, b: str) -> float:
    """
    Compute similarity between two hex tag ID strings.
    Returns 0.0 to 1.0 (1.0 = identical).

    Uses character-level overlap at matching positions.
    """
    if not a or not b:
        return 0.0

    min_len = min(len(a), len(b))
    max_len = max(len(a), len(b))

    if max_len == 0:
        return 1.0

    matches = sum(1 for i in range(min_len) if a[i] == b[i])
    return matches / max_len


def cluster_tags(detections: list[dict],
                 similarity_threshold: float = 0.75) -> dict:
    """
    Cluster noisy RFID tag reads into physical tag groups.

    The RFID reader outputs a continuous byte stream without delimiters,
    so the same physical tag can produce slightly different hex strings.
    This clusters them by string similarity.

    All clusters are kept (even single-hit tags).

    Args:
        detections: list of detection dicts with 'tag_id' key
        similarity_threshold: min similarity (0-1) to merge into same cluster

    Returns:
        (tag_to_cluster, clusters)
    """
    # Count frequency of each raw tag ID
    freq = defaultdict(int)
    for d in detections:
        freq[d["tag_id"]] += 1

    # Sort by frequency (most common first)
    sorted_tags = sorted(freq.keys(), key=lambda t: freq[t], reverse=True)

    # Greedy clustering: assign each tag to most similar existing cluster,
    # or create a new cluster
    clusters: list[dict] = []  # Each: {representative, members, total_count}

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

    # Sort clusters by total count (most detections first)
    clusters.sort(key=lambda c: c["total_count"], reverse=True)

    # Keep ALL clusters (no max_tags cap)

    # Build mapping: raw_tag_id -> cluster_index
    tag_to_cluster = {}
    for idx, cluster in enumerate(clusters):
        for member in cluster["members"]:
            tag_to_cluster[member] = idx

    return tag_to_cluster, clusters


# ============================================================================
# STEPPER COMMUNICATION
# ============================================================================

def send_steps(ser: serial.Serial, direction: str, count: int,
               timeout: float = 30.0) -> bool:
    """
    Send step commands to ESP32 and wait for DONE.

    Sends in small paced chunks to prevent ESP32 serial buffer overflow,
    which causes missed steps and positional drift.

    Args:
        ser: Serial connection to ESP32
        direction: 'R' (CW) or 'L' (CCW)
        count: Number of single-step commands to send
        timeout: Max seconds to wait for completion

    Returns:
        True if movement completed
    """
    cmd = direction.encode()
    chunk = 64  # Small chunks to avoid ESP32 RX buffer overflow
    for i in range(0, count, chunk):
        batch = min(chunk, count - i)
        ser.write(cmd * batch)
        ser.flush()
        # Drain any responses between chunks
        while ser.in_waiting:
            ser.readline()
        # Pace the sends so the ESP32 can process them
        time.sleep(0.05)

    # Wait for DONE response
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if 'DONE' in line:
                return True
        time.sleep(0.01)

    return False  # Timeout


# ============================================================================
# RFID SCANNER THREAD
# ============================================================================

class RFIDScanner:
    """Background RFID scanner that records detections with position info."""

    def __init__(self, rfid_ser: serial.Serial):
        self.ser = rfid_ser
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

        # Current scan position (set by main thread)
        self.current_angle = 0.0
        self.current_step = 0
        self.current_position_index = 0

        # All raw detections
        self.detections: list[dict] = []

        # Deduplication
        self._last_tag = None
        self._last_tag_time = 0.0
        self._dedupe_window = 0.3  # seconds (faster for quick scan)

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

                    while len(buffer) >= 16:
                        tag_id, consumed = parse_rfid_data(buffer)
                        if consumed == 0:
                            break
                        buffer = buffer[consumed:]

                        if tag_id and self._should_record(tag_id):
                            with self._lock:
                                detection = {
                                    "tag_id": tag_id,
                                    "angle_deg": round(self.current_angle, 2),
                                    "step": self.current_step,
                                    "position_index": self.current_position_index,
                                    "timestamp": datetime.now().astimezone().isoformat(),
                                    "time_epoch": time.time(),
                                }
                                self.detections.append(detection)

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


# ============================================================================
# RESULTS
# ============================================================================

def save_results(detections: list[dict], scan_info: dict,
                 tag_map: dict, clusters: list[dict],
                 tag_to_cluster: dict):
    """Save clustered scan results to JSON and CSV."""

    # Assign cluster labels
    cluster_labels = {}
    new_tags_for_map = {}

    for idx, cluster in enumerate(clusters):
        canonical_id = cluster["representative"]

        # Check if any member matches known tag map
        known_label = None
        for member in cluster["members"]:
            if member in tag_map:
                known_label = tag_map[member]
                break

        if known_label:
            label = known_label
        else:
            label = f"Tag-{idx + 1}"
            # Add to tag map for future scans
            new_tags_for_map[label] = canonical_id

        cluster_labels[idx] = label
        cluster["label"] = label
        cluster["canonical_id"] = canonical_id

    # Enrich detections with cluster info
    clustered_detections = []
    for d in detections:
        tid = d["tag_id"]
        if tid in tag_to_cluster:
            cluster_idx = tag_to_cluster[tid]
            d_enriched = dict(d)
            d_enriched["cluster_id"] = cluster_idx
            d_enriched["label"] = cluster_labels[cluster_idx]
            d_enriched["canonical_tag_id"] = clusters[cluster_idx]["canonical_id"]
            clustered_detections.append(d_enriched)
        # Skip detections not in top clusters (noise)

    # Build per-tag summary with quadrant hit counts
    tags_summary = {}
    for idx, cluster in enumerate(clusters):
        label = cluster["label"]
        canonical = cluster["canonical_id"]

        # Gather all angles for this cluster
        cluster_detections = [d for d in clustered_detections
                              if d["cluster_id"] == idx]
        angles = sorted(set(d["angle_deg"] for d in cluster_detections))

        # Count hits per quadrant
        quadrant_hits = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
        for d in cluster_detections:
            a = d["angle_deg"] % 360
            if a < 90:
                quadrant_hits["Q1"] += 1
            elif a < 180:
                quadrant_hits["Q2"] += 1
            elif a < 270:
                quadrant_hits["Q3"] += 1
            else:
                quadrant_hits["Q4"] += 1

        # Assign to strongest quadrant
        best_quadrant = max(quadrant_hits, key=quadrant_hits.get)

        tags_summary[label] = {
            "canonical_tag_id": canonical,
            "all_raw_ids": cluster["members"],
            "detection_count": len(cluster_detections),
            "raw_variant_count": len(cluster["members"]),
            "angles_detected": angles,
            "quadrant_hits": quadrant_hits,
            "best_quadrant": best_quadrant,
            "first_seen": cluster_detections[0]["timestamp"] if cluster_detections else None,
            "last_seen": cluster_detections[-1]["timestamp"] if cluster_detections else None,
        }

    # Full results
    results = {
        "scan_info": scan_info,
        "tags_found": len(tags_summary),
        "tags_summary": tags_summary,
        "clustered_detections": clustered_detections,
    }

    # Save JSON
    try:
        with open(RESULTS_JSON, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  [SAVED] {RESULTS_JSON.name}")
    except Exception as e:
        print(f"  [ERROR] JSON save failed: {e}")

    # Save CSV (clustered)
    try:
        with open(RESULTS_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "label", "canonical_tag_id", "raw_tag_id",
                "angle_deg", "step", "position_index"
            ])
            for d in clustered_detections:
                writer.writerow([
                    d["timestamp"], d["label"], d["canonical_tag_id"],
                    d["tag_id"], d["angle_deg"], d["step"],
                    d["position_index"]
                ])
        print(f"  [SAVED] {RESULTS_CSV.name}")
    except Exception as e:
        print(f"  [ERROR] CSV save failed: {e}")

    # Update tag map with new discoveries
    save_tag_map_updates(new_tags_for_map)

    # Write scan_data.js for digital twin (avoids file:// CORS issues)
    try:
        tag_map_raw = {}
        if TAG_MAP_FILE.exists():
            with open(TAG_MAP_FILE, "r") as f:
                tag_map_raw = json.load(f)
        js_content = (
            f"// Auto-generated by scan_360.py\n"
            f"const SCAN_DATA = {json.dumps(results, indent=2)};\n"
            f"const TAG_MAP_DATA = {json.dumps(tag_map_raw, indent=2)};\n"
        )
        with open(SCAN_DATA_JS, "w") as f:
            f.write(js_content)
        print(f"  [SAVED] {SCAN_DATA_JS.name}")
    except Exception as e:
        print(f"  [ERROR] scan_data.js write failed: {e}")

    return results


def print_summary(results: dict, num_positions: int):
    """Print a visual summary of the clustered scan."""
    clustered_detections = results["clustered_detections"]
    tags_summary = results["tags_summary"]
    scan_info = results["scan_info"]

    print()
    print("=" * 64)
    print("  360-DEGREE SCAN RESULTS")
    print("=" * 64)
    print()
    print(f"  Duration:       {scan_info.get('duration_seconds', 0):.1f}s")
    print(f"  Positions:      {num_positions}")
    print(f"  Raw detections: {scan_info.get('raw_detection_count', '?')}")
    print(f"  Physical tags:  {len(tags_summary)}")
    print()

    if not tags_summary:
        print("  No tags detected during scan.")
        return

    # Tag summary table
    print(f"  {'Label':<10} {'Canonical Tag ID':<44} {'Hits':<6} {'Variants'}")
    print(f"  {'-'*10} {'-'*44} {'-'*6} {'-'*8}")

    for label, info in sorted(tags_summary.items()):
        canonical = info["canonical_tag_id"]
        count = info["detection_count"]
        variants = info["raw_variant_count"]
        print(f"  {label:<10} {canonical:<44} {count:<6} {variants}")

    # Angle detail per tag
    print()
    print("  Detection angles per tag:")
    print()

    for label, info in sorted(tags_summary.items()):
        angles = info["angles_detected"]
        if len(angles) <= 8:
            angle_str = ", ".join(f"{a:.0f}" for a in angles)
        else:
            angle_str = (
                ", ".join(f"{a:.0f}" for a in angles[:4])
                + " ... "
                + ", ".join(f"{a:.0f}" for a in angles[-4:])
            )
        print(f"    {label:<10} [{angle_str}] deg")

    # Angular heatmap
    print()
    print("  Angular Detection Heatmap:")
    print()

    deg_per_pos = 360.0 / num_positions

    # Build per-position, per-tag detection count
    pos_tags = defaultdict(lambda: defaultdict(int))
    all_labels = sorted(tags_summary.keys())

    for d in clustered_detections:
        pos_tags[d["position_index"]][d["label"]] += 1

    # Header
    label_headers = "  ".join(f"{l:<6}" for l in all_labels)
    print(f"  {'Angle':<12} {label_headers}")
    print(f"  {'-'*12} {'  '.join('-'*6 for _ in all_labels)}")

    for i in range(num_positions):
        angle = i * deg_per_pos
        counts = []
        for label in all_labels:
            c = pos_tags[i].get(label, 0)
            if c > 0:
                counts.append(f"{'#'*min(c,6):<6}")
            else:
                counts.append(f"{'.':<6}")
        row = "  ".join(counts)
        print(f"  {angle:6.1f} deg   {row}")

    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RFID 360-Degree Scanner (v2) — Single-pass 360-degree scan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scan_360.py                          # Auto-detect, scan all tags
  python scan_360.py --total-steps 2035       # Custom step count for 360
  python scan_360.py --stepper COM3 --rfid COM4
  python scan_360.py --similarity 0.85        # Looser tag clustering
        """,
    )
    parser.add_argument("--stepper", type=str, default=None,
                        help="Serial port for ESP32 stepper (e.g. COM3)")
    parser.add_argument("--rfid", type=str, default=None,
                        help="Serial port for RFID reader (e.g. COM4)")
    parser.add_argument("--total-steps", type=int, default=2035,
                        help="Total motor steps for full 360 platform rotation (default: 2035)")
    parser.add_argument("--positions", type=int, default=16,
                        help="Number of scan positions per full rotation (default: 16)")
    parser.add_argument("--dwell", type=float, default=0.0,
                        help="Seconds to scan at each position (default: 0.0)")
    parser.add_argument("--similarity", type=float, default=0.92,
                        help="Tag clustering similarity threshold 0-1 (default: 0.92)")
    args = parser.parse_args()

    print()
    print("=" * 64)
    print("  RFID 360-DEGREE SCANNER v2")
    print("=" * 64)
    print()

    # ---- Load configuration ----
    config = load_config()
    tag_map = load_tag_map()

    steps_per_rev = config["steps_per_revolution"]
    num_positions = args.positions

    # Total steps for a full 360-degree platform rotation
    total_scan_steps = args.total_steps
    steps_per_position = total_scan_steps // num_positions
    deg_per_position = 360.0 / num_positions

    print(f"  Total scan steps:   {total_scan_steps} (360 deg)")
    print(f"  Scan mode:          Single-pass (FWD)")
    print(f"  Scan positions:     {num_positions} ({deg_per_position:.1f} deg each)")
    print(f"  Steps/position:     {steps_per_position}")
    print(f"  Dwell time:         {args.dwell}s")
    print(f"  Cluster threshold:  {args.similarity}")
    print(f"  Known tags:         {len(tag_map)}")
    print()

    # ---- Detect ports ----
    stepper_port = args.stepper or detect_stepper_port()
    rfid_port = args.rfid or detect_rfid_port()

    if not stepper_port:
        print("  ERROR: Could not detect stepper ESP32 port.")
        print("  Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"    {p.device} - {p.description}")
        print("  Use --stepper COM3 to specify manually.")
        sys.exit(1)

    if not rfid_port:
        print("  ERROR: Could not detect RFID reader port.")
        print("  Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"    {p.device} - {p.description}")
        print("  Use --rfid COM4 to specify manually.")
        sys.exit(1)

    if stepper_port == rfid_port:
        print(f"  ERROR: Both on same port ({stepper_port})!")
        sys.exit(1)

    print(f"  Stepper:  {stepper_port}")
    print(f"  RFID:     {rfid_port}")
    print()

    # ---- Connect ----
    try:
        stepper_ser = serial.Serial(stepper_port, STEPPER_BAUD, timeout=0.1)
    except serial.SerialException as e:
        print(f"  ERROR: Cannot open stepper port {stepper_port}: {e}")
        sys.exit(1)

    try:
        rfid_ser = serial.Serial(rfid_port, RFID_BAUD, timeout=0.2,
                                 bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE)
    except serial.SerialException:
        # CH340 workaround: some drivers fail to configure all params at once.
        # Open at 9600 first, then switch to target baud rate.
        try:
            rfid_ser = serial.Serial(rfid_port, 9600, timeout=0.2)
            rfid_ser.baudrate = RFID_BAUD
            print(f"  [NOTE] Used CH340 workaround for {rfid_port}")
        except serial.SerialException as e2:
            print(f"  ERROR: Cannot open RFID port {rfid_port}: {e2}")
            stepper_ser.close()
            sys.exit(1)

    print("  Waiting for ESP32 boot...")
    time.sleep(3)

    # Drain boot messages
    while stepper_ser.in_waiting:
        stepper_ser.readline()

    # Clear RFID buffer
    time.sleep(0.1)
    rfid_ser.reset_input_buffer()

    print("  [OK] Both devices connected")
    print()

    # ---- Start RFID scanner ----
    scanner = RFIDScanner(rfid_ser)
    scanner.start()

    # ---- Perform double 360-degree sweep (forward + reverse) ----
    scan_start_time = time.time()
    scan_start_iso = datetime.now().astimezone().isoformat()

    print(f"  Starting 360-degree scan ({total_scan_steps} steps)...")
    print(f"  Ctrl+C to abort")
    print()

    try:
        def run_sweep(direction, label):
            """Run one full rotation with dwell at every 90 degrees."""
            total_sent = 0
            # Positions where we dwell (every 90 degrees)
            dwell_interval = 90.0

            for pos_idx in range(num_positions):
                angle = pos_idx * deg_per_position

                # Progress
                pct = (pos_idx / num_positions) * 100
                bar_len = 30
                filled = int(bar_len * pos_idx / num_positions)
                bar = "=" * filled + "-" * (bar_len - filled)
                n_det = len(scanner.get_detections())
                sys.stdout.write(
                    f"\r  {label} [{bar}] {pct:5.1f}% "
                    f"| pos {pos_idx+1}/{num_positions} "
                    f"| {n_det} reads   "
                )
                sys.stdout.flush()

                # Update scanner position
                scanner.set_position(angle, total_sent, pos_idx)

                # Dwell only at 90-degree intervals (0°, 90°, 180°, 270°) if dwell time is set
                if args.dwell > 0.0 and (angle % dwell_interval < 0.01):
                    time.sleep(args.dwell)

                # Move to next position
                if pos_idx < num_positions - 1:
                    ok = send_steps(stepper_ser, direction, steps_per_position, timeout=15.0)
                    if not ok:
                        print(f"\n  [WARN] Timeout at position {pos_idx+1}")
                    total_sent += steps_per_position

            # Final dwell at 360° (same as 0°) if dwell time is set
            scanner.set_position(360.0, total_sent, num_positions - 1)
            if args.dwell > 0.0:
                time.sleep(args.dwell)

            n_det = len(scanner.get_detections())
            sys.stdout.write(
                f"\r  {label} [{'=' * 30}] 100.0% "
                f"| COMPLETE "
                f"| {n_det} reads              \n"
            )
            sys.stdout.flush()

        # Run single sweep: Forward (CW)
        run_sweep('R', 'FWD ')

        print()
        scan_duration = time.time() - scan_start_time

        # ---- Stop scanner ----
        scanner.stop()
        raw_detections = scanner.get_detections()

        print()
        print(f"  Raw detections: {len(raw_detections)}")

        # ---- Cluster tags (all clusters kept) ----
        print(f"  Clustering all tags (similarity >= {args.similarity})...")

        tag_to_cluster, clusters = cluster_tags(
            raw_detections, args.similarity
        )

        print(f"  Found {len(clusters)} tag clusters")

        # ---- Build scan info ----
        scan_info = {
            "scan_start": scan_start_iso,
            "scan_end": datetime.now().astimezone().isoformat(),
            "duration_seconds": round(scan_duration, 2),
            "scan_mode": "single_pass",
            "num_positions": num_positions,
            "degrees_per_position": deg_per_position,
            "steps_per_position": steps_per_position,
            "steps_per_revolution": steps_per_rev,
            "stepper_port": stepper_port,
            "rfid_port": rfid_port,
            "similarity_threshold": args.similarity,
            "raw_detection_count": len(raw_detections),
        }

        # ---- Save and display ----
        results = save_results(
            raw_detections, scan_info, tag_map,
            clusters, tag_to_cluster
        )
        print_summary(results, num_positions)

    except KeyboardInterrupt:
        print("\n\n  [ABORT] Scan interrupted!")
        stepper_ser.write(b'0')
        stepper_ser.flush()

        scanner.stop()
        raw_detections = scanner.get_detections()

        if raw_detections:
            scan_duration = time.time() - scan_start_time
            tag_to_cluster, clusters = cluster_tags(
                raw_detections, args.similarity
            )
            scan_info = {
                "scan_start": scan_start_iso,
                "scan_end": datetime.now().astimezone().isoformat(),
                "duration_seconds": round(scan_duration, 2),
                "num_positions": num_positions,
                "status": "INTERRUPTED",
                "raw_detection_count": len(raw_detections),
            }
            results = save_results(
                raw_detections, scan_info, tag_map,
                clusters, tag_to_cluster
            )
            print_summary(results, num_positions)
        else:
            print("  No detections to save.")

    finally:
        stepper_ser.write(b'0')
        stepper_ser.flush()
        time.sleep(0.2)
        stepper_ser.close()
        rfid_ser.close()
        print("  [OK] Ports closed. Done.")
        print()

        # Open digital twin visualization
        twin_path = SCRIPT_DIR / "digital_twin.html"
        if twin_path.exists():
            print("  Opening Digital Twin visualization...")
            webbrowser.open(twin_path.as_uri())
        print()


if __name__ == "__main__":
    main()
