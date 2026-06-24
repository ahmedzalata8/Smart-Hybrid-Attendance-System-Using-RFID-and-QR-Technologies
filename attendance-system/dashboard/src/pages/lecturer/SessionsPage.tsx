import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { sessionsApi } from '../../services/api';

interface Session {
  id: string;
  course_id: string;
  status: string;
  t_start: string;
  t_expiry: string;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    sessionsApi.list().then((res) => {
      setSessions(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Sessions</h1>
          <p className="page-subtitle">Manage your attendance sessions</p>
        </div>
        <Link to="/lecturer/sessions/new" className="btn btn-primary">
          New Session
        </Link>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Expires</th>
                <th>Status</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center text-muted" style={{ padding: '2rem' }}>Loading...</td></tr>
              ) : sessions.length === 0 ? (
                <tr><td colSpan={5}>
                  <div className="empty-state">
                    <p>No sessions yet. Create your first attendance session.</p>
                  </div>
                </td></tr>
              ) : sessions.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{formatDate(s.t_start)}</td>
                  <td>{formatTime(s.t_start)}</td>
                  <td>{formatTime(s.t_expiry)}</td>
                  <td>
                    <span className={`badge badge-${s.status}`}>{s.status}</span>
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <Link to={`/lecturer/sessions/${s.id}`} className="btn btn-sm btn-secondary">View</Link>
                      <Link to={`/lecturer/sessions/${s.id}?tab=report`} className="btn btn-sm btn-secondary">Report</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
