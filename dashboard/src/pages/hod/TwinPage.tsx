import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { dashboardApi } from '../../services/api';

interface SeatData {
  seat_id: string;
  label: string;
  row: number;
  col: number;
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
  session_status: string;
  seats: SeatData[];
}

export default function TwinPage() {
  const { id } = useParams<{ id: string }>();
  const [twin, setTwin] = useState<TwinData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SeatData | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const navigate = useNavigate();

  const fetchTwin = () => {
    if (id) {
      dashboardApi.twin(id).then((res) => {
        setTwin(res.data);
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  };

  useEffect(() => {
    fetchTwin();
    // Poll every 3 seconds for live updates
    intervalRef.current = setInterval(fetchTwin, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [id]);

  if (loading) return <div className="page"><p className="text-muted">Loading digital twin...</p></div>;
  if (!twin) return <div className="page"><p className="text-muted">Session not found</p></div>;

  const getSeatClass = (seat: SeatData) => {
    if (seat.attendance_status === 'present') return 'seat-present';
    if (seat.attendance_status === 'rejected') return 'seat-rejected';
    if (seat.attendance_status === 'revoked') return 'seat-revoked';
    if (seat.is_occupied) return 'seat-occupied';
    return 'seat-empty';
  };

  const getSeatStatusText = (seat: SeatData) => {
    if (seat.attendance_status) return seat.attendance_status;
    if (seat.is_occupied) return 'occupied';
    return '';
  };

  // Build grid
  const grid: (SeatData | null)[][] = [];
  for (let r = 0; r < twin.layout_rows; r++) {
    grid[r] = [];
    for (let c = 0; c < twin.layout_cols; c++) {
      grid[r][c] = twin.seats.find((s) => s.row === r && s.col === c) || null;
    }
  }

  const occupied = twin.seats.filter(s => s.is_occupied).length;
  const present = twin.seats.filter(s => s.attendance_status === 'present').length;
  const rejected = twin.seats.filter(s => s.attendance_status === 'rejected').length;
  const revoked = twin.seats.filter(s => s.attendance_status === 'revoked').length;

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">{twin.classroom_name}</h1>
          <p className="page-subtitle">
            Digital Twin -- {twin.session_status === 'active' ? 'Live' : 'Closed'}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Total Seats</div>
          <div className="stat-value">{twin.seats.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Occupied</div>
          <div className="stat-value">{occupied}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Present</div>
          <div className="stat-value success">{present}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Rejected</div>
          <div className="stat-value danger">{rejected}</div>
        </div>
        {revoked > 0 && (
          <div className="stat-card">
            <div className="stat-label">Revoked</div>
            <div className="stat-value warning">{revoked}</div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Seat Map</span>
          {twin.session_status === 'active' && (
            <span className="text-sm text-muted">Auto-refreshing every 3s</span>
          )}
        </div>
        <div className="card-body">
          <div
            className="seat-grid"
            style={{ gridTemplateColumns: `repeat(${twin.layout_cols}, 56px)` }}
          >
            {grid.map((row, ri) =>
              row.map((seat, ci) =>
                seat ? (
                  <div
                    key={seat.seat_id}
                    className={`seat-cell ${getSeatClass(seat)}`}
                    onClick={() => setSelected(seat)}
                    style={{ cursor: 'pointer' }}
                    title={`${seat.label} - ${getSeatStatusText(seat) || 'empty'}`}
                  >
                    <span className="seat-label">{seat.label}</span>
                    {getSeatStatusText(seat) && (
                      <span className="seat-status">{getSeatStatusText(seat)}</span>
                    )}
                  </div>
                ) : (
                  <div key={`empty-${ri}-${ci}`} style={{ width: 56, height: 56 }} />
                )
              )
            )}
          </div>

          <div className="seat-legend">
            <div className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: 'var(--seat-empty)' }} />
              <span>Empty</span>
            </div>
            <div className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: 'var(--seat-occupied)' }} />
              <span>Occupied</span>
            </div>
            <div className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: 'var(--seat-present)' }} />
              <span>Present</span>
            </div>
            <div className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: 'var(--seat-rejected)' }} />
              <span>Rejected</span>
            </div>
            <div className="seat-legend-item">
              <div className="seat-legend-dot" style={{ background: 'var(--seat-revoked)' }} />
              <span>Revoked</span>
            </div>
          </div>
        </div>
      </div>

      {/* Seat detail popup */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Seat {selected.label}</span>
              <button className="modal-close" onClick={() => setSelected(null)}>x</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
                <div className="flex-between">
                  <span className="text-muted text-sm">Occupied</span>
                  <span>{selected.is_occupied ? 'Yes' : 'No'}</span>
                </div>
                <div className="flex-between">
                  <span className="text-muted text-sm">Attendance</span>
                  <span>
                    {selected.attendance_status
                      ? <span className={`badge badge-${selected.attendance_status}`}>{selected.attendance_status}</span>
                      : '--'
                    }
                  </span>
                </div>
                {selected.last_seen_at && (
                  <div className="flex-between">
                    <span className="text-muted text-sm">Last Seen</span>
                    <span>{new Date(selected.last_seen_at).toLocaleTimeString('en-GB')}</span>
                  </div>
                )}
                <div className="flex-between">
                  <span className="text-muted text-sm">Seat ID</span>
                  <span className="font-mono text-sm">{selected.seat_id.slice(0, 12)}...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
