import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import LecturerLayout from './components/LecturerLayout';
import HodLayout from './components/HodLayout';
import SessionsPage from './pages/lecturer/SessionsPage';
import SessionDetail from './pages/lecturer/SessionDetail';
import CreateSession from './pages/lecturer/CreateSession';
import ReportPage from './pages/lecturer/ReportPage';
import CoursesPage from './pages/lecturer/CoursesPage';
import ClassDetailPage from './pages/lecturer/ClassDetailPage';
import CourseStudentsPage from './pages/lecturer/CourseStudentsPage';
import TwinPage from './pages/hod/TwinPage';
import HodSessionsPage from './pages/hod/HodSessionsPage';

import AdminLayout from './components/AdminLayout';
import AdminUsersPage from './pages/admin/AdminUsersPage';
import AdminCoursesPage from './pages/admin/AdminCoursesPage';
import AdminClassesPage from './pages/admin/AdminClassesPage';
import AdminSchedulesPage from './pages/admin/AdminSchedulesPage';
import AttendPage from './pages/student/AttendPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const { user, isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public attendance page (no login required) */}
      <Route path="/attend/:sessionId" element={<AttendPage />} />

      <Route path="/login" element={
        isAuthenticated
          ? <Navigate to={user?.role === 'admin' ? '/admin/users' : user?.role === 'hod' ? '/hod' : '/lecturer'} replace />
          : <Login />
      } />

      {/* Admin routes */}
      <Route path="/admin" element={
        <ProtectedRoute><AdminLayout /></ProtectedRoute>
      }>
        <Route index element={<Navigate to="users" replace />} />
        <Route path="users" element={<AdminUsersPage />} />
        <Route path="courses" element={<AdminCoursesPage />} />
        <Route path="classes" element={<AdminClassesPage />} />
        <Route path="schedules" element={<AdminSchedulesPage />} />
      </Route>

      {/* Lecturer routes */}
      <Route path="/lecturer" element={
        <ProtectedRoute><LecturerLayout /></ProtectedRoute>
      }>
        <Route index element={<SessionsPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="sessions/new" element={<CreateSession />} />
        <Route path="sessions/:id" element={<SessionDetail />} />
        <Route path="sessions/:id/report" element={<ReportPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="courses/:courseId/students" element={<CourseStudentsPage />} />
        <Route path="classes/:classId" element={<ClassDetailPage />} />
        <Route path="twin/:id" element={<TwinPage />} />
      </Route>

      {/* HoD routes */}
      <Route path="/hod" element={
        <ProtectedRoute><HodLayout /></ProtectedRoute>
      }>
        <Route index element={<HodSessionsPage />} />
        <Route path="sessions" element={<HodSessionsPage />} />
        <Route path="twin/:id" element={<TwinPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
