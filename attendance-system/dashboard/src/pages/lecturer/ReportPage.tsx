import { useParams, Link } from 'react-router-dom';
import ReportView from './views/ReportView';

/* Standalone report page — kept for backward-compatible deep links. */
export default function ReportPage() {
  const { id } = useParams<{ id: string }>();

  if (!id) return <div className="page"><p className="text-muted">Report not found</p></div>;

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Attendance Report</h1>
          <p className="page-subtitle">Session {id.slice(0, 8)}...</p>
        </div>
        <Link to={`/lecturer/sessions/${id}`} className="btn btn-secondary">Back to Session</Link>
      </div>
      <ReportView sessionId={id} />
    </div>
  );
}
