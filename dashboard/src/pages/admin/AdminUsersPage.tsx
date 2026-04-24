import { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  student_id: string | null;
  department_id: string;
  is_active: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'student',
    student_id: '',
    department_id: '',
    is_active: true
  });
  const [saving, setSaving] = useState(false);

  const fetchUsers = () => {
    setLoading(true);
    adminApi.users.list({ role: roleFilter || undefined, search: search || undefined })
      .then((res: any) => setUsers(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    adminApi.departments.list().then((res: any) => setDepartments(res.data)).catch(console.error);
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete ${name}?`)) return;
    setDeleting(id);
    try {
      await adminApi.users.delete(id);
      setUsers(users.filter(u => u.id !== id));
    } catch (err) {
      alert('Failed to delete user. They might be referenced elsewhere.');
    } finally {
      setDeleting(null);
    }
  };

  const openModal = (user?: User) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        email: user.email,
        password: '', // blank on edit means unchanged
        full_name: user.full_name,
        role: user.role,
        student_id: user.student_id || '',
        department_id: user.department_id,
        is_active: user.is_active
      });
    } else {
      setEditingUser(null);
      setFormData({
        email: '', password: '', full_name: '', role: 'student', student_id: '',
        department_id: departments[0]?.id || '', is_active: true
      });
    }
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: any = { ...formData };
      if (!payload.student_id) payload.student_id = null;
      if (!payload.password && editingUser) delete payload.password; // Do not update password if blank

      if (editingUser) {
        const res = await adminApi.users.update(editingUser.id, payload);
        setUsers(users.map(u => u.id === editingUser.id ? res.data : u));
      } else {
        const res = await adminApi.users.create(payload);
        setUsers([res.data, ...users]);
      }
      setShowModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save user');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header flex-between" style={{ alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Manage Users</h1>
          <p className="page-subtitle">Add, edit, or remove system users</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          Add User
        </button>
      </div>

      <div className="card">
        <div className="card-header" style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          <select 
            value={roleFilter} 
            onChange={(e) => setRoleFilter(e.target.value)}
            className="form-input" 
            style={{ width: '200px' }}
          >
            <option value="">All Roles</option>
            <option value="student">Students</option>
            <option value="lecturer">Lecturers</option>
            <option value="hod">Head of Department</option>
            <option value="admin">Administrators</option>
          </select>

          <div style={{ display: 'flex', gap: 'var(--space-2)', flex: 1, minWidth: '250px' }}>
            <input 
              type="text" 
              className="form-input" 
              placeholder="Search name, email, ID..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
            />
            <button className="btn btn-secondary" onClick={fetchUsers}>Search</button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Email</th>
                <th>Student ID</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted text-center">Loading users...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">No users match your criteria</td></tr>
              ) : users.map(u => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{u.full_name}</td>
                  <td>
                    <span className={`badge`} style={{ 
                      background: u.role === 'admin' ? 'var(--color-danger)' : 'var(--color-surface-alt)',
                      color: '#000'
                    }}>
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="text-muted">{u.email}</td>
                  <td className="font-mono">{u.student_id || '—'}</td>
                  <td>
                    {u.is_active ? 
                      <span className="badge badge-active">Active</span> : 
                      <span className="badge badge-closed">Inactive</span>}
                  </td>
                  <td>
                    <div className="flex gap-2">
                       <button className="btn btn-sm btn-secondary" onClick={() => openModal(u)}>Edit</button>
                       <button 
                         className="btn btn-sm" 
                         style={{ color: 'var(--color-danger)' }}
                         onClick={() => handleDelete(u.id, u.full_name)}
                         disabled={deleting === u.id || u.role === 'admin'}
                       >
                         {deleting === u.id ? '...' : 'Delete'}
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
              <h2 className="modal-title">{editingUser ? 'Edit User' : 'Add New User'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input type="text" required className="form-input" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Email</label>
                    <input type="email" required className="form-input" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Password {editingUser && '(Leave blank to keep current)'}</label>
                    <input type="password" required={!editingUser} className="form-input" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Role</label>
                    <select className="form-input" value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})}>
                      <option value="student">Student</option>
                      <option value="lecturer">Lecturer</option>
                      <option value="hod">Head of Department</option>
                      <option value="admin">Administrator</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Department</label>
                    <select required className="form-input" value={formData.department_id} onChange={e => setFormData({...formData, department_id: e.target.value})}>
                      <option value="">Select a department...</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                </div>
                {formData.role === 'student' && (
                  <div className="form-group">
                    <label className="form-label">Student ID (Optional)</label>
                    <input type="text" className="form-input" value={formData.student_id} onChange={e => setFormData({...formData, student_id: e.target.value})} />
                  </div>
                )}
                {editingUser && (
                  <div className="form-group flex gap-2" style={{ alignItems: 'center' }}>
                    <input type="checkbox" id="is_active" checked={formData.is_active} onChange={e => setFormData({...formData, is_active: e.target.checked})} />
                    <label htmlFor="is_active">User is Active</label>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save User'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
