import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../services/api';

interface SeatOption {
  seat_id: string;
  label: string;
  is_occupied: boolean;
}

export default function AttendPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [studentName, setStudentName] = useState('');
  const [tagNumber, setTagNumber] = useState('');
  const [seats, setSeats] = useState<SeatOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
  const [sessionInfo, setSessionInfo] = useState<{ classroom_name: string; expires_at: string } | null>(null);
  const [expired, setExpired] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<Date | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    api.get(`/attendance/public/session-info/${sessionId}`)
      .then((res) => {
        setSessionInfo(res.data);
        setSeats(res.data.seats || []);
        setExpired(new Date(res.data.expires_at) < new Date());
        setLoading(false);
      })
      .catch(() => {
        setResult({ success: false, message: 'Session not found or expired' });
        setLoading(false);
      });
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !studentName.trim() || !tagNumber.trim()) return;

    setSubmitting(true);
    setResult(null);

    try {
      const res = await api.post('/attendance/public/claim', {
        session_id: sessionId,
        student_name: studentName.trim(),
        tag_number: tagNumber.trim(),
      });
      setVerifiedAt(new Date());
      setResult({ success: true, message: res.data.message || 'Attendance recorded!' });
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to submit attendance';
      setResult({ success: false, message: detail });
    }
    setSubmitting(false);
  };

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="attend-page">
        <div className="attend-phone">
          <div className="attend-loading">
            <div className="scan-spinner" style={{ width: 32, height: 32 }} />
            <p className="text-muted">Loading session...</p>
          </div>
        </div>
      </div>
    );
  }

  /* ── Expired ── */
  if (expired) {
    return (
      <div className="attend-page">
        <div className="attend-phone">
          <div className="attend-topbar">
            <h1>Attendance</h1>
            <span className="badge badge-rejected">Ended</span>
          </div>
          <div className="attend-body" style={{ alignItems: 'center', textAlign: 'center' }}>
            <div className="attend-check" style={{ background: 'var(--color-warning)' }}>⏰</div>
            <h2 style={{ fontWeight: 800 }}>Session Expired</h2>
            <p className="text-muted">This attendance session has ended.</p>
          </div>
        </div>
      </div>
    );
  }

  /* ── Success receipt ── */
  if (result?.success) {
    return (
      <div className="attend-page">
        <div className="attend-phone">
          <div className="attend-topbar">
            <h1>Attendance</h1>
            <span className="badge badge-present">Verified</span>
          </div>
          <div className="attend-body">
            <div className="attend-verified">
              <div className="attend-check">✓</div>
              <h2 style={{ fontWeight: 800 }}>Attendance Verified!</h2>
              <p className="text-muted">{result.message}</p>
            </div>

            <div className="attend-receipt">
              <div className="attend-receipt-title">Verification Receipt</div>
              <div className="attend-receipt-row"><span>Name</span><strong>{studentName}</strong></div>
              <div className="attend-receipt-row"><span>Seat</span><strong>{tagNumber}</strong></div>
              {sessionInfo && (
                <div className="attend-receipt-row"><span>Room</span><strong>{sessionInfo.classroom_name}</strong></div>
              )}
              {sessionId && (
                <div className="attend-receipt-row"><span>Session</span><strong className="font-mono">{sessionId.slice(0, 8)}…</strong></div>
              )}
              {verifiedAt && (
                <div className="attend-receipt-row">
                  <span>Time</span>
                  <strong>{verifiedAt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</strong>
                </div>
              )}
              <div className="attend-receipt-row">
                <span>Status</span>
                <span className="badge badge-present">Present</span>
              </div>
            </div>

            <button className="btn btn-primary attend-submit" onClick={() => setResult(null)}>
              Done →
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Stats from available data ── */
  const total = seats.length;
  const occupied = seats.filter((s) => s.is_occupied).length;
  const available = total - occupied;

  /* ── Form / seat selection ── */
  return (
    <div className="attend-page">
      <div className="attend-phone">
        <div className="attend-topbar">
          <h1>Mark Attendance</h1>
          <span className="badge badge-present">Active</span>
        </div>

        <div className="attend-body">
          {sessionInfo && (
            <div className="attend-desk">▲ {sessionInfo.classroom_name} — front ▲</div>
          )}

          <div className="stats-row">
            <div className="stat-card">
              <div className="stat-label">Total</div>
              <div className="stat-value">{total}</div>
            </div>
            <div className="stat-card stat-card--present">
              <div className="stat-label">Available</div>
              <div className="stat-value">{available}</div>
            </div>
            <div className="stat-card stat-card--occupied">
              <div className="stat-label">Occupied</div>
              <div className="stat-value">{occupied}</div>
            </div>
          </div>

          {result && !result.success && (
            <div className="attend-error">⚠ {result.message}</div>
          )}

          <form onSubmit={handleSubmit} className="attend-body" style={{ padding: 0, gap: 'var(--space-5)' }}>
            <div className="attend-field">
              <label htmlFor="studentName">Your Name</label>
              <input
                id="studentName"
                type="text"
                placeholder="Enter your full name"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                required
                autoFocus
                autoComplete="name"
              />
            </div>

            {seats.length > 0 && (
              <div className="attend-field">
                <label>Select Your Seat</label>
                <div className="attend-seatgrid">
                  {seats.map((seat) => (
                    <button
                      key={seat.seat_id}
                      type="button"
                      className={`attend-seat ${seat.is_occupied ? 'occupied' : ''} ${tagNumber === seat.label ? 'selected' : ''}`}
                      onClick={() => setTagNumber(seat.label)}
                    >
                      {seat.label}
                    </button>
                  ))}
                </div>
                <div className="seat-legend">
                  <div className="seat-legend-item">
                    <span className="seat-legend-dot" style={{ background: 'var(--seat-empty)' }} /> Available
                  </div>
                  <div className="seat-legend-item">
                    <span className="seat-legend-dot" style={{ background: 'var(--color-warning)' }} /> Selected
                  </div>
                  <div className="seat-legend-item">
                    <span className="seat-legend-dot" style={{ background: 'var(--seat-occupied)' }} /> Occupied
                  </div>
                </div>
              </div>
            )}

            <div className="attend-field">
              <label htmlFor="tagNumber">Tag Number</label>
              <input
                id="tagNumber"
                type="text"
                placeholder="e.g. Tag-1, Tag-2..."
                value={tagNumber}
                onChange={(e) => setTagNumber(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary attend-submit"
              disabled={submitting || !studentName.trim() || !tagNumber.trim()}
            >
              {submitting ? (
                <>
                  <span className="scan-spinner" />
                  Scanning the room to confirm your seat...
                </>
              ) : (
                'Submit Attendance'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
