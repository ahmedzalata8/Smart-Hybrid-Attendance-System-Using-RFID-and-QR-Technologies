import { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';

interface Enrollment {
  id: string;
  student_id: string;
  student_name: string | null;
  student_identifier: string | null;
  course_id: string;
  course_code: string | null;
  class_id: string | null;
  class_group: string | null;
  enrolled_at: string;
}

export default function AdminSchedulesPage() {
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    student_id: '',
    course_id: '',
    class_id: ''
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.users.list({ role: 'student' }).then((res: any) => setStudents(res.data)).catch(console.error);
    adminApi.courses.list().then((res: any) => setCourses(res.data)).catch(console.error);
  }, []);

  useEffect(() => {
    if (formData.course_id) {
      adminApi.classes.list({ course_id: formData.course_id }).then((res: any) => setClasses(res.data)).catch(console.error);
    } else {
      setClasses([]);
    }
  }, [formData.course_id]);

  const fetchEnrollments = () => {
    setLoading(true);
    adminApi.enrollments.list()
      .then((res: any) => setEnrollments(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEnrollments();
  }, []);

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Remove this student's enrollment?`)) return;
    setDeleting(id);
    try {
      await adminApi.enrollments.delete(id);
      setEnrollments(enrollments.filter(e => e.id !== id));
    } catch (err) {
      alert('Failed to remove enrollment.');
    } finally {
      setDeleting(null);
    }
  };

  const openModal = () => {
    setFormData({
      student_id: students[0]?.id || '',
      course_id: '',
      class_id: ''
    });
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: any = { ...formData };
      if (!payload.class_id) payload.class_id = null;
      
      const res = await adminApi.enrollments.create(payload);
      setEnrollments([res.data, ...enrollments]);
      setShowModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to enroll student');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header flex-between" style={{ alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Student Enrollments</h1>
          <p className="page-subtitle">Manage student schedules (enrollments to courses/classes)</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          Enroll Student
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student Name</th>
                <th>Student ID</th>
                <th>Course</th>
                <th>Class Group</th>
                <th>Enrolled Date</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted text-center">Loading enrollments...</td></tr>
              ) : enrollments.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">No enrollments found</td></tr>
              ) : enrollments.map(e => (
                <tr key={e.id}>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{e.student_name}</td>
                  <td className="font-mono text-muted">{e.student_identifier || '—'}</td>
                  <td className="font-mono">{e.course_code}</td>
                  <td>{e.class_group || '—'}</td>
                  <td className="text-muted">
                    {new Date(e.enrolled_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="flex gap-2">
                       <button 
                         className="btn btn-sm" 
                         style={{ color: 'var(--color-danger)' }}
                         onClick={() => handleDelete(e.id)}
                         disabled={deleting === e.id}
                       >
                         {deleting === e.id ? '...' : 'Remove'}
                       </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2 className="modal-title">Enroll Student</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Student</label>
                  <select required className="form-input" value={formData.student_id} onChange={e => setFormData({...formData, student_id: e.target.value})}>
                    <option value="">Select a student...</option>
                    {students.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.student_id})</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Course</label>
                  <select required className="form-input" value={formData.course_id} onChange={e => setFormData({...formData, course_id: e.target.value, class_id: ''})}>
                    <option value="">Select a course...</option>
                    {courses.map(c => <option key={c.id} value={c.id}>{c.code} - {c.name}</option>)}
                  </select>
                </div>
                {formData.course_id && (
                  <div className="form-group">
                    <label className="form-label">Class Schedule / Group (Optional)</label>
                    <select className="form-input" value={formData.class_id} onChange={e => setFormData({...formData, class_id: e.target.value})}>
                      <option value="">No specific group</option>
                      {classes.map(c => (
                        <option key={c.id} value={c.id}>
                          {c.group_name || 'Group'} — {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][c.day_of_week]} {c.start_time} to {c.end_time}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Enrolling...' : 'Enroll'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
