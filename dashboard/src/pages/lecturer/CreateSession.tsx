import { useState, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionsApi, dashboardApi } from '../../services/api';

interface Course {
  id: string;
  code: string;
  name: string;
}

interface Classroom {
  id: string;
  name: string;
  building: string | null;
  layout_rows: number;
  layout_cols: number;
}

export default function CreateSession() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [courseId, setCourseId] = useState('');
  const [classroomId, setClassroomId] = useState('');
  const [duration, setDuration] = useState(60);
  const [freshness, setFreshness] = useState(120);
  const [minPresence, setMinPresence] = useState(75);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    sessionsApi.courses().then((res) => setCourses(res.data)).catch(() => {});
    dashboardApi.classrooms().then((res) => setClassrooms(res.data)).catch(() => {});
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!courseId) { setError('Please select a course'); return; }
    if (!classroomId) { setError('Please select a classroom'); return; }
    setError('');
    setLoading(true);

    const now = new Date();
    const expiry = new Date(now.getTime() + duration * 60 * 1000);

    try {
      const res = await sessionsApi.create({
        course_id: courseId,
        classroom_id: classroomId,
        t_start: now.toISOString(),
        t_expiry: expiry.toISOString(),
        freshness_delta_sec: freshness,
        min_presence_pct: minPresence,
      });
      navigate(`/lecturer/sessions/${res.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create session');
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">New Session</h1>
        <p className="page-subtitle">Create a new attendance session</p>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            {error && (
              <div className="alert alert-danger">
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="course">Course</label>
              <select
                id="course"
                className="form-input"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                required
              >
                <option value="">Select a course</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} -- {c.name}
                  </option>
                ))}
              </select>
              {courses.length === 0 && (
                <div className="text-sm text-muted" style={{ marginTop: 'var(--space-1)' }}>
                  No courses assigned to you yet.
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="classroom">Classroom</label>
              <select
                id="classroom"
                className="form-input"
                value={classroomId}
                onChange={(e) => setClassroomId(e.target.value)}
                required
              >
                <option value="">Select a classroom</option>
                {classrooms.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.layout_rows}x{c.layout_cols} seats)
                  </option>
                ))}
              </select>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="duration">Duration (minutes)</label>
                <input
                  id="duration"
                  type="number"
                  className="form-input"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  min={5}
                  max={300}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="freshness">Freshness window (sec)</label>
                <input
                  id="freshness"
                  type="number"
                  className="form-input"
                  value={freshness}
                  onChange={(e) => setFreshness(Number(e.target.value))}
                  min={30}
                  max={600}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="minPresence">Minimum presence (%)</label>
              <input
                id="minPresence"
                type="number"
                className="form-input"
                value={minPresence}
                onChange={(e) => setMinPresence(Number(e.target.value))}
                min={0}
                max={100}
                style={{ maxWidth: 120 }}
              />
              <div className="text-sm text-muted" style={{ marginTop: 'var(--space-1)' }}>
                Students must be seated for at least this percentage of the session to retain attendance.
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create Session'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
