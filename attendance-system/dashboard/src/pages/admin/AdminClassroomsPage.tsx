// @ts-nocheck
import { useEffect, useState } from 'react';
import { adminApi } from '../../services/api';
import { Canvas } from '@react-three/fiber';
import { PerspectiveCamera } from '@react-three/drei';

interface Classroom {
  id: string;
  name: string;
  department_id: string;
  department_name: string | null;
  building: string | null;
  floor: number | null;
  layout_rows: number;
  layout_cols: number;
  seat_count: number;
}

export default function AdminClassroomsPage() {
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Classroom | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    department_id: '',
    building: '',
    floor: 1,
    layout_rows: 5,
    layout_cols: 5
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.departments.list().then((res: any) => setDepartments(res.data)).catch(console.error);
    fetchClassrooms();
  }, []);

  const fetchClassrooms = () => {
    setLoading(true);
    adminApi.classrooms.list()
      .then((res: any) => setClassrooms(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete classroom ${name}? All seats will be removed!`)) return;
    setDeleting(id);
    try {
      await adminApi.classrooms.delete(id);
      setClassrooms(classrooms.filter(c => c.id !== id));
    } catch (err) {
      alert('Failed to delete classroom. It is likely referenced somewhere.');
    } finally {
      setDeleting(null);
    }
  };

  const openModal = (room?: Classroom) => {
    if (room) {
      setEditingRoom(room);
      setFormData({
        name: room.name,
        department_id: room.department_id,
        building: room.building || '',
        floor: room.floor || 1,
        layout_rows: room.layout_rows,
        layout_cols: room.layout_cols
      });
    } else {
      setEditingRoom(null);
      setFormData({
        name: '', 
        department_id: departments[0]?.id || '', 
        building: '',
        floor: 1,
        layout_rows: 5,
        layout_cols: 5
      });
    }
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        floor: Number(formData.floor) || null,
        layout_rows: Number(formData.layout_rows),
        layout_cols: Number(formData.layout_cols)
      };
      
      if (editingRoom) {
        const res = await adminApi.classrooms.update(editingRoom.id, payload);
        setClassrooms(classrooms.map(c => c.id === editingRoom.id ? res.data : c));
      } else {
        const res = await adminApi.classrooms.create(payload);
        setClassrooms([res.data, ...classrooms]);
      }
      setShowModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save classroom');
    } finally {
      setSaving(false);
    }
  };

  const previewWidth = 400;
  const previewHeight = 300;

  return (
    <div className="page">
      <div className="page-header flex-between" style={{ alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Manage Classrooms</h1>
          <p className="page-subtitle">Configure physical rooms and 2.5D layouts</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          Add Classroom
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Room Name</th>
                <th>Department</th>
                <th>Building/Floor</th>
                <th>Grid Layout</th>
                <th>Total Seats</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted text-center">Loading classrooms...</td></tr>
              ) : classrooms.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">No classrooms found</td></tr>
              ) : classrooms.map(c => (
                <tr key={c.id}>
                  <td className="font-mono" style={{ fontWeight: 600 }}>{c.name}</td>
                  <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>{c.department_name}</td>
                  <td className="text-muted">{c.building ? `${c.building} (Fl ${c.floor})` : '—'}</td>
                  <td>{c.layout_rows} &times; {c.layout_cols}</td>
                  <td>{c.seat_count}</td>
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
          <div className="modal" style={{ maxWidth: '800px', width: '100%' }}>
            <div className="modal-header">
              <h2 className="modal-title">{editingRoom ? 'Edit Classroom' : 'Add New Classroom'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <div className="modal-body" style={{ display: 'flex', gap: 'var(--space-6)' }}>
              
              {/* Form Side */}
              <div style={{ flex: 1 }}>
                <form id="classroom-form" onSubmit={handleSave}>
                  <div className="form-group">
                    <label className="form-label">Room Name</label>
                    <input type="text" required className="form-input" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g. Lab 101" />
                  </div>
                  {!editingRoom && (
                    <div className="form-group">
                      <label className="form-label">Department</label>
                      <select required className="form-input" value={formData.department_id} onChange={e => setFormData({...formData, department_id: e.target.value})}>
                        <option value="">Select a department...</option>
                        {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                      </select>
                    </div>
                  )}
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Building (Optional)</label>
                      <input type="text" className="form-input" value={formData.building} onChange={e => setFormData({...formData, building: e.target.value})} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Floor</label>
                      <input type="number" className="form-input" value={formData.floor} onChange={e => setFormData({...formData, floor: parseInt(e.target.value)})} />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Layout Rows</label>
                      <input type="number" required min="1" max="20" className="form-input" value={formData.layout_rows} onChange={e => setFormData({...formData, layout_rows: parseInt(e.target.value) || 1})} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Layout Cols</label>
                      <input type="number" required min="1" max="20" className="form-input" value={formData.layout_cols} onChange={e => setFormData({...formData, layout_cols: parseInt(e.target.value) || 1})} />
                    </div>
                  </div>
                </form>
              </div>

              {/* Preview Side */}
              <div style={{ flex: 1 }}>
                <label className="form-label" style={{ marginBottom: 'var(--space-2)' }}>2.5D Isometric Preview</label>
                <div style={{ width: previewWidth, height: previewHeight, background: '#e0e7ff', border: '2px solid #000', borderRadius: '6px', overflow: 'hidden' }}>
                  <Canvas shadows>
                    {(() => {
                      const rows = formData.layout_rows;
                      const cols = formData.layout_cols;
                      const spacingX = 1.4;
                      const spacingZ = 1.4;
                      const offsetX = ((cols - 1) * spacingX) / 2;
                      const offsetZ = ((rows - 1) * spacingZ) / 2;
                      const maxDim = Math.max(rows, cols);
                      const camDist = maxDim * 1.5 + 5;

                      return (
                        <>
                          <PerspectiveCamera makeDefault position={[camDist, camDist * 0.8, camDist]} fov={35} onUpdate={c => c.lookAt(0, 0, 0)} />
                          <ambientLight intensity={0.6} />
                          <directionalLight castShadow position={[10, 15, 10]} intensity={1.2} />
                          
                          <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]}>
                            <planeGeometry args={[cols * spacingX + 4, rows * spacingZ + 4]} />
                            <meshStandardMaterial color="#fcd34d" roughness={1} />
                          </mesh>

                          {Array.from({ length: rows }).map((_, r) => 
                            Array.from({ length: cols }).map((_, c) => (
                              <group key={`preview-${r}-${c}`} position={[(c * spacingX) - offsetX, 0, (r * spacingZ) - offsetZ]}>
                                <mesh castShadow receiveShadow position={[0, 0.4, 0]}>
                                  <boxGeometry args={[1, 0.05, 0.8]} />
                                  <meshStandardMaterial color="#ffffff" roughness={0.8} />
                                </mesh>
                                <mesh castShadow position={[-0.45, 0.2, -0.35]}>
                                  <boxGeometry args={[0.05, 0.4, 0.05]} />
                                  <meshStandardMaterial color="#374151" />
                                </mesh>
                                <mesh castShadow position={[0.45, 0.2, -0.35]}>
                                  <boxGeometry args={[0.05, 0.4, 0.05]} />
                                  <meshStandardMaterial color="#374151" />
                                </mesh>
                                <mesh castShadow position={[-0.45, 0.2, 0.35]}>
                                  <boxGeometry args={[0.05, 0.4, 0.05]} />
                                  <meshStandardMaterial color="#374151" />
                                </mesh>
                                <mesh castShadow position={[0.45, 0.2, 0.35]}>
                                  <boxGeometry args={[0.05, 0.4, 0.05]} />
                                  <meshStandardMaterial color="#374151" />
                                </mesh>
                              </group>
                            ))
                          )}
                        </>
                      );
                    })()}
                  </Canvas>
                </div>
                <p className="text-muted text-sm mt-2">
                  Total capacity: {formData.layout_rows * formData.layout_cols} seats. Desks will be auto-generated.
                </p>
              </div>

            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              <button type="submit" form="classroom-form" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Classroom'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
