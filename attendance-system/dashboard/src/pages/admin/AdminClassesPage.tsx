import { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

interface CourseClass {
  id: string;
  course_id: string;
  course_code: string | null;
  classroom_id: string;
  classroom_name: string | null;
  lecturer_id: string;
  lecturer_name: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  group_name: string | null;
}

export default function AdminClassesPage() {
  const [classes, setClasses] = useState<CourseClass[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [lecturers, setLecturers] = useState<any[]>([]);
  
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    course_id: '',
    classroom_id: '',
    lecturer_id: '',
    day_of_week: 0,
    start_time: '08:00',
    end_time: '10:00',
    group_name: ''
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.courses.list().then((res: any) => setCourses(res.data)).catch(console.error);
    adminApi.classrooms.list().then((res: any) => setClassrooms(res.data)).catch(console.error);
    adminApi.users.list({ role: 'lecturer' }).then((res: any) => setLecturers(res.data)).catch(console.error);
  }, []);

  const fetchClasses = () => {
    setLoading(true);
    adminApi.classes.list({ search: search || undefined })
      .then((res: any) => setClasses(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchClasses();
  }, []);

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Delete this class schedule? All student enrollments for this class will also be cleared.`)) return;
    setDeleting(id);
    try {
      await adminApi.classes.delete(id);
      setClasses(classes.filter(c => c.id !== id));
    } catch (err) {
      alert('Failed to delete class.');
    } finally {
      setDeleting(null);
    }
  };

  const openModal = () => {
    setFormData({
      course_id: courses[0]?.id || '',
      classroom_id: classrooms[0]?.id || '',
      lecturer_id: lecturers[0]?.id || '',
      day_of_week: 0,
      start_time: '08:00',
      end_time: '10:00',
      group_name: ''
    });
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...formData, day_of_week: Number(formData.day_of_week) };
      const res = await adminApi.classes.create(payload);
      setClasses([...classes, res.data]);
      setShowModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save class schedule');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header flex-between" style={{ alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Manage Class Schedules</h1>
          <p className="page-subtitle">Schedule class time slots for courses</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          Add Class Schedule
        </button>
      </div>

      <div className="card">
        <div className="card-header" style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input 
            type="text" 
            className="form-input" 
            placeholder="Search by course..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchClasses()}
            style={{ maxWidth: '300px' }}
          />
          <button className="btn btn-secondary" onClick={fetchClasses}>Search</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Group</th>
                <th>Schedule</th>
                <th>Lecturer</th>
                <th>Classroom</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted text-center">Loading schedules...</td></tr>
              ) : classes.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">No class schedules match your criteria</td></tr>
              ) : classes.map(c => (
                <tr key={c.id}>
                  <td className="font-mono" style={{ fontWeight: 600 }}>{c.course_code}</td>
                  <td>{c.group_name || '—'}</td>
                  <td>{DAY_NAMES[c.day_of_week]} {c.start_time} - {c.end_time}</td>
                  <td className="text-muted">{c.lecturer_name || '—'}</td>
                  <td className="text-muted">{c.classroom_name || '—'}</td>
                  <td>
                    <div className="flex gap-2">
                       <button 
                         className="btn btn-sm" 
                         style={{ color: 'var(--color-danger)' }}
                         onClick={() => handleDelete(c.id)}
                         disabled={deleting === c.id}
                       >
                         {deleting === c.id ? '...' : 'Delete'}
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
              <h2 className="modal-title">Schedule New Class</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Course</label>
                    <select required className="form-input" value={formData.course_id} onChange={e => setFormData({...formData, course_id: e.target.value})}>
                      <option value="">Select a course...</option>
                      {courses.map(c => <option key={c.id} value={c.id}>{c.code} - {c.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Group Name (Optional)</label>
                    <input type="text" className="form-input" value={formData.group_name} onChange={e => setFormData({...formData, group_name: e.target.value})} placeholder="e.g. Section 1" />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Lecturer</label>
                  <select required className="form-input" value={formData.lecturer_id} onChange={e => setFormData({...formData, lecturer_id: e.target.value})}>
                    <option value="">Select a lecturer...</option>
                    {lecturers.map(l => <option key={l.id} value={l.id}>{l.full_name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Classroom</label>
                  <select required className="form-input" value={formData.classroom_id} onChange={e => setFormData({...formData, classroom_id: e.target.value})}>
                    <option value="">Select a classroom...</option>
                    {classrooms.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Day</label>
                    <select required className="form-input" value={formData.day_of_week} onChange={e => setFormData({...formData, day_of_week: parseInt(e.target.value)})}>
                      {DAY_NAMES.map((name, i) => <option key={i} value={i}>{name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Start Time</label>
                    <input type="time" required className="form-input" value={formData.start_time} onChange={e => setFormData({...formData, start_time: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">End Time</label>
                    <input type="time" required className="form-input" value={formData.end_time} onChange={e => setFormData({...formData, end_time: e.target.value})} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Scheduling...' : 'Schedule Class'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
