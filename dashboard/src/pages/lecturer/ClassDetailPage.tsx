import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { sessionsApi } from '../../services/api';

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

interface ClassInfo {
  id: string;
  course_id: string;
  course_code: string;
  course_name: string;
  classroom_name: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  group_name: string | null;
}

interface ClassSession {
  id: string;
  t_start: string;
  t_expiry: string;
  status: string;
  present_count: number;
  total_enrolled: number;
  students_present: string[];
}

interface Student {
  id: string;
  full_name: string;
  email: string;
  student_id: string | null;
  enrolled_at: string;
}

export default function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const [classInfo, setClassInfo] = useState<ClassInfo | null>(null);
  const [sessions, setSessions] = useState<ClassSession[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);

  useEffect(() => {
    if (!classId) return;

    Promise.all([
      sessionsApi.classes(),
      sessionsApi.classSessions(classId),
      sessionsApi.classStudents(classId),
    ]).then(([classesRes, sessionsRes, studentsRes]) => {
      const found = classesRes.data.find((c: ClassInfo) => c.id === classId);
      setClassInfo(found || null);
      setSessions(sessionsRes.data);
      setStudents(studentsRes.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [classId]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) return <div className="page"><p className="text-muted">Loading class details...</p></div>;
  if (!classInfo) return <div className="page"><p className="text-muted">Class not found</p></div>;

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">
            {classInfo.course_code} — {classInfo.group_name || 'Default'}
          </h1>
          <p className="page-subtitle">
            {classInfo.course_name} · {DAY_NAMES[classInfo.day_of_week]} {classInfo.start_time}–{classInfo.end_time} · {classInfo.classroom_name || 'TBA'}
          </p>
        </div>
        <div className="flex gap-4">
          <Link
            to={`/lecturer/courses/${classInfo.course_id}/students`}
            className="btn btn-secondary"
          >
            All Course Students
          </Link>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Enrolled Students</div>
          <div className="stat-value">{students.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Sessions</div>
          <div className="stat-value">{sessions.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Schedule</div>
          <div className="stat-value" style={{ fontSize: 'var(--font-size-base)' }}>
            {DAY_NAMES[classInfo.day_of_week]} {classInfo.start_time}
          </div>
        </div>
      </div>

      {/* Students in this class */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Students in this Class</span>
          <span className="text-sm text-muted">{students.length} students</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Student ID</th>
                <th>Email</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr><td colSpan={3} className="empty-state">No students enrolled in this class.</td></tr>
              ) : students.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{s.full_name}</td>
                  <td className="font-mono">{s.student_id || '—'}</td>
                  <td className="text-muted">{s.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Session History / Schedule */}
      <div className="card mt-6">
        <div className="card-header">
          <span className="card-title">Session History</span>
          <span className="text-sm text-muted">{sessions.length} sessions</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th>Attendance</th>
                <th style={{ width: 140 }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr><td colSpan={5} className="empty-state">No sessions held yet for this class.</td></tr>
              ) : sessions.map((s) => (
                <>
                  <tr key={s.id}>
                    <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{formatDate(s.t_start)}</td>
                    <td>{formatTime(s.t_start)} – {formatTime(s.t_expiry)}</td>
                    <td>
                      <span className={`badge badge-${s.status}`}>{s.status}</span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 500 }}>{s.present_count}</span>
                      <span className="text-muted"> / {s.total_enrolled > 0 ? s.total_enrolled : students.length}</span>
                      <span className="text-muted text-sm"> present</span>
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => setExpandedSession(expandedSession === s.id ? null : s.id)}
                        >
                          {expandedSession === s.id ? 'Hide' : 'Students'}
                        </button>
                        <Link to={`/lecturer/sessions/${s.id}/report`} className="btn btn-sm btn-secondary">
                          Report
                        </Link>
                      </div>
                    </td>
                  </tr>
                  {expandedSession === s.id && (
                    <tr key={`${s.id}-detail`}>
                      <td colSpan={5} style={{ background: 'var(--color-surface)', padding: 'var(--space-4)' }}>
                        {s.students_present.length === 0 ? (
                          <span className="text-muted text-sm">No students marked present in this session.</span>
                        ) : (
                          <div>
                            <div className="text-sm text-muted" style={{ marginBottom: 'var(--space-2)' }}>
                              Students present:
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                              {s.students_present.map((name, i) => (
                                <span key={i} className="badge badge-present" style={{ fontSize: 'var(--font-size-sm)' }}>
                                  {name}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
