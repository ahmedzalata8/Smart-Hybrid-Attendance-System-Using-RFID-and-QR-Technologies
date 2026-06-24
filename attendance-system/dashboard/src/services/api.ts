import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
};

// ── Sessions ──
export const sessionsApi = {
  list: () => api.get('/sessions/'),
  get: (id: string) => api.get(`/sessions/${id}`),
  courses: () => api.get('/sessions/courses'),
  courseStudents: (courseId: string) => api.get(`/sessions/courses/${courseId}/students`),
  classes: () => api.get('/sessions/classes'),
  classStudents: (classId: string) => api.get(`/sessions/classes/${classId}/students`),
  classSessions: (classId: string) => api.get(`/sessions/classes/${classId}/sessions`),
  create: (data: {
    course_id: string;
    classroom_id: string;
    class_id?: string;
    t_start: string;
    t_expiry: string;
    freshness_delta_sec?: number;
    min_presence_pct?: number;
  }) => api.post('/sessions/', data),
  close: (id: string) => api.post(`/sessions/${id}/close`),
};

// ── Attendance ──
export const attendanceApi = {
  report: (sessionId: string) => api.get(`/attendance/report/${sessionId}`),
  revoke: (recordId: string, reason?: string) =>
    api.post(`/attendance/records/${recordId}/revoke`, { reason: reason ?? null }),
};

// ── Dashboard ──
export const dashboardApi = {
  twin: (sessionId: string) => api.get(`/dashboard/twin/${sessionId}`),
  classrooms: () => api.get('/dashboard/classrooms'),
};

// ── Admin ──
export const adminApi = {
  users: {
    list: (params?: { role?: string, search?: string }) => api.get('/admin/users', { params }),
    create: (data: any) => api.post('/admin/users', data),
    update: (id: string, data: any) => api.put(`/admin/users/${id}`, data),
    delete: (id: string) => api.delete(`/admin/users/${id}`)
  },
  courses: {
    list: (params?: { search?: string }) => api.get('/admin/courses', { params }),
    create: (data: any) => api.post('/admin/courses', data),
    update: (id: string, data: any) => api.put(`/admin/courses/${id}`, data),
    delete: (id: string) => api.delete(`/admin/courses/${id}`)
  },
  classes: {
    list: (params?: { course_id?: string, search?: string }) => api.get('/admin/classes', { params }),
    create: (data: any) => api.post('/admin/classes', data),
    delete: (id: string) => api.delete(`/admin/classes/${id}`)
  },
  enrollments: {
    list: (params?: { student_id?: string, course_id?: string, class_id?: string }) => api.get('/admin/enrollments', { params }),
    create: (data: any) => api.post('/admin/enrollments', data),
    delete: (id: string) => api.delete(`/admin/enrollments/${id}`)
  },
  departments: {
    list: () => api.get('/admin/departments')
  },
  classrooms: {
    list: () => api.get('/admin/classrooms')
  }
};

// ── RFID 360° Scan ──
export const rfidScanApi = {
  start: (sessionId: string, stepperPort?: string, rfidPort?: string) =>
    api.post('/rfid-scan/start', {
      session_id: sessionId,
      stepper_port: stepperPort || null,
      rfid_port: rfidPort || null,
    }),
  status: () => api.get('/rfid-scan/status'),
  results: () => api.get('/rfid-scan/results'),
  applyResults: () => api.post('/rfid-scan/apply-results'),
  applyUpdate: () => api.post('/rfid-scan/apply-update'),
};

export default api;

