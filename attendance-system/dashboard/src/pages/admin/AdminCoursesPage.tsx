import { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';

interface Course {
  id: string;
  code: string;
  name: string;
  department_id: string;
  lecturer_id: string;
  lecturer_name: string | null;
}

export default function AdminCoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [lecturers, setLecturers] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    department_id: '',
    lecturer_id: ''
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.departments.list().then((res: any) => setDepartments(res.data)).catch(console.error);
    adminApi.users.list({ role: 'lecturer' }).then((res: any) => setLecturers(res.data)).catch(console.error);
  }, []);

  const fetchCourses = () => {
    setLoading(true);
    adminApi.courses.list({ search: search || undefined })
      .then((res: any) => setCourses(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete course ${name}? This will remove all associated classes and enrollments!`)) return;
    setDeleting(id);
    try {
      await adminApi.courses.delete(id);
      setCourses(courses.filter(c => c.id !== id));
    } catch (err) {
      alert('Failed to delete course. It is likely referenced somewhere.');
    } finally {
      setDeleting(null);
    }
  };

  const openModal = (course?: Course) => {
    if (course) {
      setEditingCourse(course);
      setFormData({
        code: course.code,
        name: course.name,
        department_id: course.department_id,
        lecturer_id: course.lecturer_id
      });
    } else {
      setEditingCourse(null);
      setFormData({
        code: '', name: '', 
        department_id: departments[0]?.id || '', 
        lecturer_id: lecturers[0]?.id || ''
      });
    }
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingCourse) {
        const res = await adminApi.courses.update(editingCourse.id, formData);
        setCourses(courses.map(c => c.id === editingCourse.id ? res.data : c));
      } else {
        const res = await adminApi.courses.create(formData);
        setCourses([res.data, ...courses]);
      }
      setShowModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save course');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header flex-between" style={{ alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Manage Courses</h1>
          <p className="page-subtitle">Add or edit system courses</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          Add Course
        </button>
      </div>

      <div className="card">
        <div className="card-header" style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <input 
            type="text" 
            className="form-input" 
            placeholder="Search code or name..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchCourses()}
            style={{ maxWidth: '300px' }}
          />
          <button className="btn btn-secondary" onClick={fetchCourses}>Search</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Course Name</th>
                <th>Assigned Lecturer</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="text-muted text-center">Loading courses...</td></tr>
              ) : courses.length === 0 ? (
                <tr><td colSpan={4} className="empty-state">No courses match your criteria</td></tr>
              ) : courses.map(c => (
                <tr key={c.id}>
                  <td className="font-mono" style={{ fontWeight: 600 }}>{c.code}</td>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{c.name}</td>
                  <td className="text-muted">{c.lecturer_name || '—'}</td>
                  <td>
                    <div className="flex gap-2">
                       <button className="btn btn-sm btn-secondary" onClick={() => openModal(c)}>Edit</button>
                       <button 
                         className="btn btn-sm" 
                         style={{ color: 'var(--color-danger)' }}
                         onClick={() => handleDelete(c.id, c.name)}
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
              <h2 className="modal-title">{editingCourse ? 'Edit Course' : 'Add New Course'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Course Code</label>
                    <input type="text" required className="form-input" value={formData.code} onChange={e => setFormData({...formData, code: e.target.value})} placeholder="e.g. CS101" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Course Name</label>
                    <input type="text" required className="form-input" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
                  </div>
                </div>
                {!editingCourse && (
                  <div className="form-group">
                    <label className="form-label">Department</label>
                    <select required className="form-input" value={formData.department_id} onChange={e => setFormData({...formData, department_id: e.target.value})}>
                      <option value="">Select a department...</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Primary Lecturer</label>
                  <select required className="form-input" value={formData.lecturer_id} onChange={e => setFormData({...formData, lecturer_id: e.target.value})}>
                    <option value="">Select a lecturer...</option>
                    {lecturers.map(l => <option key={l.id} value={l.id}>{l.full_name}</option>)}
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Course'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
