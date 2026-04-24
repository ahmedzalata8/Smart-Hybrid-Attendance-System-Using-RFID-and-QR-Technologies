import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { sessionsApi } from '../../services/api';

interface Student {
  id: string;
  full_name: string;
  email: string;
  student_id: string | null;
  enrolled_at: string;
}

interface Course {
  id: string;
  code: string;
  name: string;
}

export default function CourseStudentsPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!courseId) return;

    Promise.all([
      sessionsApi.courseStudents(courseId),
      sessionsApi.courses(),
    ]).then(([studentsRes, coursesRes]) => {
      setStudents(studentsRes.data);
      const found = coursesRes.data.find((c: Course) => c.id === courseId);
      setCourse(found || null);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [courseId]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  if (loading) return <div className="page"><p className="text-muted">Loading students...</p></div>;

  return (
    <div className="page">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">
            {course ? `${course.code} — All Students` : 'Course Students'}
          </h1>
          <p className="page-subtitle">
            {course ? course.name : ''} · {students.length} students enrolled
          </p>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Enrolled Students</span>
          <span className="text-sm text-muted">{students.length} total</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Student ID</th>
                <th>Email</th>
                <th>Enrolled On</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 ? (
                <tr><td colSpan={5} className="empty-state">No students enrolled in this course.</td></tr>
              ) : students.map((s, i) => (
                <tr key={s.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{s.full_name}</td>
                  <td className="font-mono">{s.student_id || '—'}</td>
                  <td className="text-muted">{s.email}</td>
                  <td>{s.enrolled_at ? formatDate(s.enrolled_at) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
