import { useEffect, useState } from 'react';
import { attendanceApi } from '../../../services/api';

interface Record {
  id: string;
  student_id: string;
  student_name: string | null;
  student_number: string | null;
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

interface ReportViewProps {
  sessionId: string;
}

export default function ReportView({ sessionId }: ReportViewProps) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [revoking, setRevoking] = useState<string | null>(null);

  const loadReport = () => {
    if (!sessionId) return;
    attendanceApi.report(sessionId).then((res) => {
      setReport(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    loadReport();
    // Poll so the report stays in sync with the live seat-map stats above.
    const t = setInterval(loadReport, 3000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleRevoke = async (recordId: string) => {
    if (!confirm('Revoke this student\'s attendance? This marks the claim as revoked.')) return;
    setRevoking(recordId);
    try {
      await attendanceApi.revoke(recordId);
      loadReport();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to revoke attendance');
    }
    setRevoking(null);
  };

  if (loading) return <p className="text-muted">Loading report...</p>;
  if (!report) return <p className="text-muted">Report not found</p>;

  return (
    <>
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
                <th>Student</th>
                <th>Claimed At</th>
                <th>Status</th>
                <th>Presence</th>
                <th>Reason</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {report.records.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">No records</td></tr>
              ) : report.records.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div style={{ fontWeight: 700 }}>{r.student_name || 'Unknown'}</div>
                    <div className="font-mono text-muted" style={{ fontSize: 'var(--font-size-xs)' }}>
                      {r.student_number || `${r.student_id.slice(0, 8)}…`}
                    </div>
                  </td>
                  <td>{new Date(r.claimed_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                  <td>
                    <span className={`badge badge-${r.status}`}>{r.status}</span>
                  </td>
                  <td>{r.presence_pct !== null ? `${r.presence_pct}%` : '--'}</td>
                  <td className="text-sm">
                    {r.rejection_reason || r.revocation_reason || '--'}
                  </td>
                  <td>
                    {r.status === 'revoked' ? (
                      <span className="text-sm text-muted">Revoked</span>
                    ) : (
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleRevoke(r.id)}
                        disabled={revoking === r.id}
                      >
                        {revoking === r.id ? 'Revoking...' : 'Revoke'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
