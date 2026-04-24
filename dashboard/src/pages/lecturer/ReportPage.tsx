import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { attendanceApi } from '../../services/api';

interface Record {
  id: string;
  student_id: string;
  seat_id: string;
  status: string;
  rejection_reason: string | null;
  revocation_reason: string | null;
  presence_pct: number | null;
  claimed_at: string;
}

interface Report {
  session_id: string;
  course_id: string;
  total_claims: number;
  present_count: number;
  rejected_count: number;
  revoked_count: number;
  records: Record[];
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      attendanceApi.report(id).then((res) => {
        setReport(res.data);
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [id]);

  if (loading) return <div className="page"><p className="text-muted">Loading report...</p></div>;
  if (!report) return <div className="page"><p className="text-muted">Report not found</p></div>;

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Attendance Report</h1>
          <p className="page-subtitle">Session {report.session_id.slice(0, 8)}...</p>
        </div>
        <Link to={`/lecturer/sessions/${id}`} className="btn btn-secondary">Back to Session</Link>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Total Claims</div>
          <div className="stat-value">{report.total_claims}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Present</div>
          <div className="stat-value success">{report.present_count}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Rejected</div>
          <div className="stat-value danger">{report.rejected_count}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Revoked</div>
          <div className="stat-value warning">{report.revoked_count}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Records</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Claimed At</th>
                <th>Status</th>
                <th>Presence</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {report.records.length === 0 ? (
                <tr><td colSpan={5} className="empty-state">No records</td></tr>
              ) : report.records.map((r) => (
                <tr key={r.id}>
                  <td className="font-mono" style={{ fontSize: 'var(--font-size-xs)' }}>
                    {r.student_id.slice(0, 12)}...
                  </td>
                  <td>{new Date(r.claimed_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                  <td>
                    <span className={`badge badge-${r.status}`}>{r.status}</span>
                  </td>
                  <td>{r.presence_pct !== null ? `${r.presence_pct}%` : '--'}</td>
                  <td className="text-sm">
                    {r.rejection_reason || r.revocation_reason || '--'}
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
