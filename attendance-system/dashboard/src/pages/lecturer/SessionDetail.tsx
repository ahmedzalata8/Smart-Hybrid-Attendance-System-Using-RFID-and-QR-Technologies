import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { QRCodeCanvas } from 'qrcode.react';
import { sessionsApi } from '../../services/api';
import SeatMapView from './views/SeatMapView';
import ReportView from './views/ReportView';

interface SessionData {
  id: string;
  course_id: string;
  classroom_id: string;
  status: string;
  t_start: string;
  t_expiry: string;
  qr_token: string;
  freshness_delta_sec: number;
  min_presence_pct: number;
  integrity_hash: string | null;
  finalized_at: string | null;
}

type Tab = 'overview' | 'seatmap';

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'seatmap', label: 'Seat Map' },
];

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionData | null>(null);
  const [closing, setClosing] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = searchParams.get('tab') as Tab | null;
  const activeTab: Tab = tabParam && TABS.some(t => t.key === tabParam) ? tabParam : 'overview';

  const setActiveTab = (tab: Tab) => {
    setSearchParams(tab === 'overview' ? {} : { tab }, { replace: true });
  };

  useEffect(() => {
    if (id) {
      sessionsApi.get(id).then((res) => setSession(res.data));
    }
  }, [id]);

  const handleClose = async () => {
    if (!id || !confirm('Close this session? This will finalize attendance and cannot be undone.')) return;
    setClosing(true);
    try {
      const res = await sessionsApi.close(id);
      setSession(res.data);
    } catch {
      alert('Failed to close session');
    }
    setClosing(false);
  };

  if (!session || !id) return <div className="page"><p className="text-muted">Loading...</p></div>;

  const isActive = session.status === 'active';
  const expiry = new Date(session.t_expiry);
  const start = new Date(session.t_start);

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Session Detail</h1>
          <p className="page-subtitle">
            {start.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
            {' -- '}
            {start.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
            {' to '}
            {expiry.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        <div className="flex gap-4">
          {isActive && (
            <button className="btn btn-danger" onClick={handleClose} disabled={closing}>
              {closing ? 'Closing...' : 'Close Session'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={activeTab === t.key}
            className={`tab ${activeTab === t.key ? 'tab--active' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Overview tab ── */}
      {activeTab === 'overview' && (
        <>
          <div className="stats-row">
            <div className="stat-card">
              <div className="stat-label">Status</div>
              <div className="mt-4">
                <span className={`badge badge-${session.status}`} style={{ fontSize: 'var(--font-size-sm)' }}>
                  {session.status}
                </span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Min. Presence</div>
              <div className="stat-value">{session.min_presence_pct}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Freshness Window</div>
              <div className="stat-value">{session.freshness_delta_sec}s</div>
            </div>
          </div>

          {isActive && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">QR Code</span>
                <span className="text-sm text-muted">Display this in the classroom for students to scan</span>
              </div>
              <div className="card-body">
                <div className="qr-container">
                  <QRCodeCanvas
                    value={`${window.location.origin}/attend/${session.id}`}
                    size={280}
                    level="M"
                    includeMargin={false}
                  />
                  <div className="qr-info">
                    <p>Session expires at {expiry.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</p>
                    <p className="font-mono text-muted" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--font-size-xs)' }}>
                      ID: {session.id.slice(0, 8)}...
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {session.integrity_hash && (
            <div className="card mt-6">
              <div className="card-header">
                <span className="card-title">Integrity</span>
              </div>
              <div className="card-body">
                <div className="text-sm">
                  <span className="text-muted">Hash: </span>
                  <span className="font-mono">{session.integrity_hash}</span>
                </div>
                {session.finalized_at && (
                  <div className="text-sm mt-4">
                    <span className="text-muted">Finalized: </span>
                    {new Date(session.finalized_at).toLocaleString('en-GB')}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Seat Map tab (seat map with the report stacked below it) ── */}
      {activeTab === 'seatmap' && (
        <>
          <SeatMapView sessionId={id} />
          <div
            style={{
              marginTop: 'var(--space-8)',
              paddingTop: 'var(--space-6)',
              borderTop: '1px solid var(--color-border)',
            }}
          >
            <h2 className="page-title" style={{ fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-4)' }}>
              Report
            </h2>
            <ReportView sessionId={id} />
          </div>
        </>
      )}
    </div>
  );
}
