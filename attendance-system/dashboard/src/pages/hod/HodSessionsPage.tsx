import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { sessionsApi } from '../../services/api';

interface Session {
  id: string;
  course_id: string;
  status: string;
  t_start: string;
  t_expiry: string;
  course_name: string | null;
  course_code: string | null;
  lecturer_name: string | null;
}

export default function HodSessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterLecturer, setFilterLecturer] = useState('');
  const [filterCourse, setFilterCourse] = useState('');

  useEffect(() => {
    sessionsApi.list().then((res) => {
      setSessions(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Build unique lecturer and course lists for filter dropdowns
  const lecturers = useMemo(() => {
    const names = new Set<string>();
    sessions.forEach((s) => { if (s.lecturer_name) names.add(s.lecturer_name); });
    return Array.from(names).sort();
  }, [sessions]);

  const courses = useMemo(() => {
    const items = new Map<string, string>();
    sessions.forEach((s) => {
      if (s.course_id && s.course_name) {
        items.set(s.course_id, `${s.course_code} — ${s.course_name}`);
      }
    });
    return Array.from(items.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [sessions]);

  // Apply filters
  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      if (filterLecturer && s.lecturer_name !== filterLecturer) return false;
      if (filterCourse && s.course_id !== filterCourse) return false;
      return true;
    });
  }, [sessions, filterLecturer, filterCourse]);

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
      <div className="page-header">
        <h1 className="page-title">Department Sessions</h1>
        <p className="page-subtitle">Monitor attendance across all sessions in your department</p>
      </div>

      {/* Filter bar */}
      <div className="card" style={{ marginBottom: 'var(--space-5)' }}>
        <div className="card-body" style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ margin: 0, minWidth: 200 }}>
            <label className="form-label" htmlFor="filter-lecturer">Filter by Lecturer</label>
            <select
              id="filter-lecturer"
              className="form-input"
              value={filterLecturer}
              onChange={(e) => setFilterLecturer(e.target.value)}
            >
              <option value="">All Lecturers</option>
              {lecturers.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0, minWidth: 200 }}>
            <label className="form-label" htmlFor="filter-course">Filter by Course</label>
            <select
              id="filter-course"
              className="form-input"
              value={filterCourse}
              onChange={(e) => setFilterCourse(e.target.value)}
            >
              <option value="">All Courses</option>
              {courses.map(([id, label]) => (
                <option key={id} value={id}>{label}</option>
              ))}
            </select>
          </div>
          {(filterLecturer || filterCourse) && (
            <button
              className="btn btn-secondary btn-sm"
              style={{ marginBottom: 2 }}
              onClick={() => { setFilterLecturer(''); setFilterCourse(''); }}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lecturer</th>
                <th>Course</th>
                <th>Date</th>
                <th>Time</th>
                <th>Expires</th>
                <th>Status</th>
                <th style={{ width: 120 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center text-muted" style={{ padding: '2rem' }}>Loading...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7}>
                  <div className="empty-state">
                    <p>{sessions.length === 0 ? 'No sessions found in your department.' : 'No sessions match the selected filters.'}</p>
                  </div>
                </td></tr>
              ) : filtered.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{s.lecturer_name || '—'}</td>
                  <td>
                    <span style={{ fontWeight: 500 }}>{s.course_code || ''}</span>
                    {s.course_name && (
                      <span className="text-muted" style={{ marginLeft: 'var(--space-1)', fontSize: 'var(--font-size-sm)' }}>
                        {s.course_name}
                      </span>
                    )}
                  </td>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{formatDate(s.t_start)}</td>
                  <td>{formatTime(s.t_start)}</td>
                  <td>{formatTime(s.t_expiry)}</td>
                  <td>
                    <span className={`badge badge-${s.status}`}>{s.status}</span>
                  </td>
                  <td>
                    <Link to={`/hod/twin/${s.id}`} className="btn btn-sm btn-primary">
                      Digital Twin
                    </Link>
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
