import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { dashboardApi, rfidScanApi } from '../../../services/api';

/* ── Types ── */
interface SeatData {
  seat_id: string;
  label: string;
  row: number;
  col: number;
  x_pct: number;
  y_pct: number;
  is_occupied: boolean;
  last_seen_at: string | null;
  student_name: string | null;
  attendance_status: string | null;
}

interface TwinData {
  session_id: string;
  classroom_name: string;
  layout_rows: number;
  layout_cols: number;
  room_width_px: number;
  room_height_px: number;
  session_status: string;
  seats: SeatData[];
}

interface TagSummary {
  canonical_tag_id: string;
  matched_known_hex: string | null;
  detection_count: number;
  raw_variant_count: number;
  angles_detected: number[];
  quadrant_hits: Record<string, number>;
  best_quadrant: string;
  x_pct: number | null;
  y_pct: number | null;
  undetermined?: boolean;
  first_seen: string | null;
  last_seen: string | null;
}

interface ScanResults {
  scan_id: string;
  session_id: string;
  tags_found: number;
  scan_info: Record<string, any>;
  tags_summary: Record<string, TagSummary>;
  clustered_detections: Array<Record<string, any>>;
  status: string;
}

/** A tag as drawn on the radar/roster: merged from scan results + the twin. */
interface DisplayTag {
  label: string;
  occupied: boolean;
  x_pct: number;
  y_pct: number;
  info: TagSummary | null; // scan detail (quadrant hits) if seen this scan
  status: string | null;       // attendance_status from the twin ('present'…)
  studentName: string | null;  // claimant name, when known
  undetermined: boolean;       // 4-way quadrant tie → cannot be placed
}

interface SeatMapViewProps {
  sessionId: string;
  /** Render a title/subtitle header inside the view (used by the standalone page). */
  showHeader?: boolean;
  /** Extra buttons rendered next to the scan button (e.g. a Back button). */
  actions?: React.ReactNode;
}

/* ── Component ── */
export default function SeatMapView({ sessionId, showHeader = false, actions }: SeatMapViewProps) {
  const id = sessionId;

  // Twin data
  const [twin, setTwin] = useState<TwinData | null>(null);
  const [loading, setLoading] = useState(true);

  // Scan state
  const [scanMode, setScanMode] = useState<'initial' | 'update'>('initial');
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanDetections, setScanDetections] = useState(0);
  const [scanResults, setScanResults] = useState<ScanResults | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<Record<string, any> | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const radarRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number>(0);

  /* ── Fetch twin data ── */
  const fetchTwin = useCallback(() => {
    if (!id) return;
    dashboardApi.twin(id).then((res) => {
      setTwin(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    fetchTwin();
    intervalRef.current = setInterval(fetchTwin, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchTwin]);

  /* ── Restore last scan results on mount ──
     scanResults only lives in component state, so the radar/tag table would
     vanish on every remount (Back button, refresh, route change) even after
     "Apply to Session". The server keeps the most recent completed scan until
     the next scan overwrites it, so re-read it here and repopulate — but only
     when it belongs to THIS session. */
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    rfidScanApi.results()
      .then((res) => {
        const data = res.data as ScanResults;
        if (
          !cancelled &&
          data?.session_id === id &&
          data.tags_summary &&
          Object.keys(data.tags_summary).length > 0
        ) {
          setScanResults(data);
        }
      })
      .catch(() => { /* no prior scan for this session — leave empty */ });
    return () => { cancelled = true; };
  }, [id]);

  /* ── Start 360° scan ── */
  const handleStartScan = async (mode: 'initial' | 'update' = 'initial') => {
    if (!id) return;
    setScanMode(mode);
    setScanError(null);
    setScanResults(null);
    setApplyResult(null);
    setScanning(true);
    setScanProgress(0);
    setScanDetections(0);

    try {
      await rfidScanApi.start(id);
      pollRef.current = setInterval(async () => {
        try {
          const res = await rfidScanApi.status();
          const data = res.data;
          setScanProgress(data.progress);
          setScanDetections(data.detections_count);

          if (data.status === 'completed') {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            const resultsRes = await rfidScanApi.results();
            setScanResults(resultsRes.data);
            setScanning(false);
          } else if (data.status === 'error') {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setScanError(data.error || 'Scan failed');
            setScanning(false);
          }
        } catch { /* ignore transient */ }
      }, 500);
    } catch (err: any) {
      setScanError(err.response?.data?.detail || 'Failed to start scan');
      setScanning(false);
    }
  };

  /* ── Apply results to session ── */
  const handleApplyResults = async () => {
    setApplying(true);
    setScanError(null);
    try {
      const res = scanMode === 'update'
        ? await rfidScanApi.applyUpdate()
        : await rfidScanApi.applyResults();
      setApplyResult(res.data);
      fetchTwin(); // refresh seat states
    } catch (err: any) {
      setScanError(err.response?.data?.detail || 'Failed to apply results');
    }
    setApplying(false);
  };

  /* ── Cleanup ── */
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  /* ── Merged tag list driving the radar + roster ──
     Combines the latest scan (detected = vacant, with quadrant hits) with the
     persistent OCCUPIED tags from the twin that weren't seen this scan (they
     stay drawn at their original position). Stale empty twin seats are dropped
     once a scan is active, so re-scans always show the current reading. */
  const displayTags = useMemo<DisplayTag[]>(() => {
    const twinByLabel = new Map((twin?.seats ?? []).map((s) => [s.label, s]));
    const out: DisplayTag[] = [];
    const seen = new Set<string>();

    if (scanResults?.tags_summary) {
      for (const [label, info] of Object.entries(scanResults.tags_summary)) {
        const seat = twinByLabel.get(label);
        out.push({
          label,
          occupied: false, // detected this scan => tag visible => seat vacant
          // Initial scan owns placement: keep the seat's stored position if it
          // already exists; only brand-new tags fall back to the scan position.
          x_pct: seat?.x_pct ?? info.x_pct ?? 50,
          y_pct: seat?.y_pct ?? info.y_pct ?? 50,
          info,
          status: seat?.attendance_status ?? null,
          studentName: seat?.student_name ?? null,
          // Only a brand-new tag (no seat yet) is subject to placement failure;
          // an already-placed seat keeps its initial-scan position.
          undetermined: !seat && (info.undetermined ?? false),
        });
        seen.add(label);
      }
    }

    for (const seat of twin?.seats ?? []) {
      if (seen.has(seat.label)) continue;
      if (scanResults && !seat.is_occupied) continue; // drop stale empties mid-scan
      out.push({
        label: seat.label,
        occupied: seat.is_occupied,
        x_pct: seat.x_pct,
        y_pct: seat.y_pct,
        info: null,
        status: seat.attendance_status,
        studentName: seat.student_name,
        undetermined: false, // already placed by the initial scan
      });
      seen.add(seat.label);
    }

    return out;
  }, [scanResults, twin]);

  /* ── Radar canvas ── */
  useEffect(() => {
    if (!radarRef.current) return;
    const canvas = radarRef.current;
    const ctx = canvas.getContext('2d')!;
    const size = canvas.width;
    const cx = size / 2;
    const cy = size / 2;
    const maxR = size / 2 - 30;
    let sweepAngle = 0;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);

      // Dark background
      ctx.fillStyle = '#1a1a1a';
      ctx.beginPath();
      ctx.arc(cx, cy, maxR + 10, 0, Math.PI * 2);
      ctx.fill();

      // Grid rings
      for (let i = 1; i <= 4; i++) {
        ctx.strokeStyle = `rgba(136, 170, 238, ${0.15 + i * 0.05})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, (maxR / 4) * i, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Cross + diagonals
      ctx.strokeStyle = 'rgba(136, 170, 238, 0.2)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy);
      ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR);
      const d = maxR * Math.cos(Math.PI / 4);
      ctx.moveTo(cx - d, cy - d); ctx.lineTo(cx + d, cy + d);
      ctx.moveTo(cx + d, cy - d); ctx.lineTo(cx - d, cy + d);
      ctx.stroke();

      // Angle labels
      ctx.fillStyle = 'rgba(136, 170, 238, 0.5)';
      ctx.font = 'bold 12px "DM Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('0°', cx, cy - maxR - 12);
      ctx.fillText('90°', cx + maxR + 16, cy + 4);
      ctx.fillText('180°', cx, cy + maxR + 18);
      ctx.fillText('270°', cx - maxR - 16, cy + 4);

      // Quadrant labels
      ctx.font = 'bold 11px "DM Sans", sans-serif';
      ctx.fillStyle = 'rgba(255,255,255,0.25)';
      const qOff = maxR * 0.55;
      ctx.fillText('Q1', cx + qOff * 0.7, cy - qOff * 0.7);
      ctx.fillText('Q2', cx + qOff * 0.7, cy + qOff * 0.7);
      ctx.fillText('Q3', cx - qOff * 0.7, cy + qOff * 0.7);
      ctx.fillText('Q4', cx - qOff * 0.7, cy - qOff * 0.7);

      // Sweep animation (only while scanning)
      if (scanning) {
        sweepAngle = (sweepAngle + 2) % 360;
        const rad = (sweepAngle - 90) * (Math.PI / 180);

        const gradient = ctx.createConicGradient(rad - 0.5, cx, cy);
        gradient.addColorStop(0, 'rgba(136, 170, 238, 0.0)');
        gradient.addColorStop(0.08, 'rgba(136, 170, 238, 0.25)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, maxR, rad - 0.5, rad);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = '#88aaee';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + maxR * Math.cos(rad), cy + maxR * Math.sin(rad));
        ctx.stroke();
      }

      // Plot the merged tag list. Colour signals state:
      //   GREEN  = claimed & present (occupied) — labelled with the student name
      //   BLUE   = occupied but not (yet) a present claim
      //   WHITE  = vacant (tag detected this scan)
      // Occupied tags keep their original position even though their RFID tag
      // is no longer detected.
      displayTags.forEach((t) => {
        if (t.undetermined) return; // 4-way tie → not placed on the radar
        // Stored position is a 0..100 percentage centred at (50,50).
        const tx = cx + ((t.x_pct - 50) / 50) * maxR;
        const ty = cy + ((t.y_pct - 50) / 50) * maxR;
        const isPresent = t.occupied && t.status === 'present';
        const fill = isPresent ? '#22c55e' : t.occupied ? '#4f7cff' : '#ffffff';
        const r = t.occupied ? 11 : 9;
        const labelText = isPresent && t.studentName ? t.studentName : t.label;

        // Glow + circle
        ctx.shadowColor = isPresent ? '#22c55e' : t.occupied ? '#4f7cff' : 'rgba(255,255,255,0.6)';
        ctx.shadowBlur = t.occupied ? 16 : 8;
        ctx.fillStyle = fill;
        ctx.beginPath();
        ctx.arc(tx, ty, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label text below the dot (student name when present)
        ctx.fillStyle = isPresent ? '#86efac' : t.occupied ? '#9fb8ff' : '#fff';
        ctx.font = 'bold 9px "DM Sans", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(labelText, tx, ty + r + 9);
      });

      // Center dot
      ctx.fillStyle = '#88aaee';
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.stroke();

      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
  }, [scanning, displayTags]);

  /* ── Render ── */
  if (loading) return <p className="text-muted">Loading digital twin...</p>;
  if (!twin) return <p className="text-muted">Session not found</p>;

  const occupied = twin.seats.filter(s => s.is_occupied).length;
  const present = twin.seats.filter(s => s.attendance_status === 'present').length;
  const rejected = twin.seats.filter(s => s.attendance_status === 'rejected').length;
  const occupiedCount = displayTags.filter(t => t.occupied).length;
  const failedCount = displayTags.filter(t => t.undetermined).length;

  return (
    <>
      {/* Header / toolbar */}
      <div className="flex-between" style={{ marginBottom: 'var(--space-6)' }}>
        <div>
          {showHeader ? (
            <>
              <h1 className="page-title">{twin.classroom_name}</h1>
              <p className="page-subtitle">
                Digital Twin — {twin.session_status === 'active' ? 'Live' : 'Closed'}
              </p>
            </>
          ) : (
            <p className="page-subtitle" style={{ margin: 0 }}>
              {twin.classroom_name} — {twin.session_status === 'active' ? 'Live' : 'Closed'}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <button
            className="btn btn-scan"
            onClick={() => handleStartScan('initial')}
            disabled={scanning || twin.session_status !== 'active'}
          >
            {scanning && scanMode === 'initial' ? (
              <>
                <span className="scan-spinner" />
                Scanning {scanProgress.toFixed(0)}%
              </>
            ) : (
              <>📡 Initial Scan</>
            )}
          </button>
          <button
            className="btn btn-scan"
            onClick={() => handleStartScan('update')}
            disabled={scanning || twin.session_status !== 'active' || twin.seats.length === 0}
            title={twin.seats.length === 0 ? 'Run an Initial Scan first' : 'Re-scan and update occupancy'}
          >
            {scanning && scanMode === 'update' ? (
              <>
                <span className="scan-spinner" />
                Updating {scanProgress.toFixed(0)}%
              </>
            ) : (
              <>🔄 Update Scan</>
            )}
          </button>
          {actions}
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Total Seats</div>
          <div className="stat-value">{twin.seats.length}</div>
        </div>
        <div className="stat-card stat-card--occupied">
          <div className="stat-label">Occupied</div>
          <div className="stat-value">{occupied}</div>
        </div>
        <div className="stat-card stat-card--present">
          <div className="stat-label">Present</div>
          <div className="stat-value">{present}</div>
        </div>
        <div className="stat-card stat-card--rejected">
          <div className="stat-label">Rejected</div>
          <div className="stat-value">{rejected}</div>
        </div>
        {scanResults && (
          <div className="stat-card" style={{ borderTop: '4px solid #c4a1ff' }}>
            <div className="stat-label">Tags Detected</div>
            <div className="stat-value" style={{ color: '#7b5ea7' }}>
              {scanResults.tags_found}
            </div>
          </div>
        )}
      </div>

      {/* Scan error */}
      {scanError && (
        <div className="alert alert-danger" style={{ marginBottom: 'var(--space-6)' }}>
          ⚠ {scanError}
          <button
            style={{ marginLeft: 12, background: 'none', border: 'none', fontWeight: 800, cursor: 'pointer' }}
            onClick={() => setScanError(null)}
          >✕</button>
        </div>
      )}

      {/* Apply success message */}
      {applyResult && (
        <div className="alert alert-success" style={{ marginBottom: 'var(--space-6)' }}>
          {applyResult.seats_added !== undefined ? (
            <>
              ✓ Update applied: {applyResult.seats_occupied}/{applyResult.total_seats} seats occupied,{' '}
              {applyResult.seats_added} new seat{applyResult.seats_added === 1 ? '' : 's'} added
            </>
          ) : (
            <>
              ✓ Applied: {applyResult.total_seats} seats created,{' '}
              {applyResult.readings_saved} readings saved
            </>
          )}
          <button
            style={{ marginLeft: 12, background: 'none', border: 'none', fontWeight: 800, cursor: 'pointer' }}
            onClick={() => setApplyResult(null)}
          >✕</button>
        </div>
      )}

      {/* Scanning progress */}
      {scanning && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="card-header">
            <span className="card-title">🔄 360° Scan In Progress</span>
            <span className="text-sm">{scanDetections} detections</span>
          </div>
          <div className="card-body">
            <div className="scan-progress-bar">
              <div className="scan-progress-fill" style={{ width: `${scanProgress}%` }} />
            </div>
            <p className="text-sm text-muted" style={{ marginTop: 'var(--space-2)', textAlign: 'center' }}>
              Rotating reader... {scanProgress.toFixed(0)}% complete
            </p>
          </div>
        </div>
      )}

      {/* Radar + Tag Table */}
      <div className="twin-radar-layout">
        {/* Radar canvas */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📡 Radar — Tag Positions</span>
            {scanResults && (
              <button
                className="btn btn-sm btn-primary"
                onClick={handleApplyResults}
                disabled={applying}
              >
                {applying
                  ? 'Applying...'
                  : scanMode === 'update'
                    ? '✓ Apply Update'
                    : '✓ Apply to Session'}
              </button>
            )}
          </div>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'center', background: '#111' }}>
            <canvas
              ref={radarRef}
              width={420}
              height={420}
              style={{ borderRadius: 'var(--radius-lg)' }}
            />
          </div>
        </div>

        {/* Tag roster — merged scan + twin. Row colour = occupancy
            (blue = occupied, white = vacant); columns show quadrant hits. */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Tags ({displayTags.length})</span>
            <span className="text-sm text-muted">
              <span style={{ color: '#4f7cff', fontWeight: 800 }}>{occupiedCount} occupied</span>
              {' • '}{displayTags.length - occupiedCount - failedCount} vacant
              {failedCount > 0 && (
                <>{' • '}<span style={{ color: '#dc2626', fontWeight: 800 }}>{failedCount} failed</span></>
              )}
            </span>
          </div>
          <div className="card-body" style={{ maxHeight: 420, overflowY: 'auto', padding: 0 }}>
            {displayTags.length === 0 ? (
              <div className="empty-state">
                <p style={{ fontSize: '2rem' }}>📡</p>
                <p>No tags detected yet</p>
                <p>Click <strong>Initial Scan</strong> to detect RFID tags</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>Tag</th>
                    <th>Hits</th>
                    <th>Quadrant</th>
                    <th>Q1</th>
                    <th>Q2</th>
                    <th>Q3</th>
                    <th>Q4</th>
                  </tr>
                </thead>
                <tbody>
                  {displayTags.map((t) => {
                    const isPresent = t.occupied && t.status === 'present';
                    return (
                    <tr
                      key={t.label}
                      style={{ background: isPresent ? 'rgba(34, 197, 94, 0.18)' : t.occupied ? 'rgba(79, 124, 255, 0.18)' : '#fff' }}
                    >
                      <td>
                        <div style={{
                          width: 14, height: 14,
                          borderRadius: 3,
                          background: isPresent ? '#22c55e' : t.occupied ? '#4f7cff' : '#fff',
                          border: '2px solid #000',
                        }} />
                      </td>
                      <td style={{ fontWeight: 800 }}>
                        {isPresent && t.studentName ? t.studentName : t.label}
                        {isPresent && t.studentName && (
                          <span className="text-muted" style={{ fontWeight: 400, fontSize: 'var(--font-size-xs)' }}> ({t.label})</span>
                        )}
                      </td>
                      <td>{t.info ? t.info.detection_count : '—'}</td>
                      <td>
                        {t.undetermined
                          ? <span className="badge badge-rejected" title="Equal hits in all 4 quadrants — cannot place">Failed to determine</span>
                          : t.info
                            ? <span className="badge badge-active">{t.info.best_quadrant}</span>
                            : '—'}
                      </td>
                      <td>{t.info?.quadrant_hits.Q1 || '—'}</td>
                      <td>{t.info?.quadrant_hits.Q2 || '—'}</td>
                      <td>{t.info?.quadrant_hits.Q3 || '—'}</td>
                      <td>{t.info?.quadrant_hits.Q4 || '—'}</td>
                    </tr>
                  );})}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
