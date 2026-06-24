import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { sessionsApi } from '../../services/api';

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

interface CourseClass {
  id: string;
  course_id: string;
  course_code: string;
  course_name: string;
  lecturer_name: string | null;
  classroom_name: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  group_name: string | null;
}

interface CourseGroup {
  course_id: string;
  code: string;
  name: string;
  classes: CourseClass[];
}

export default function CoursesPage() {
  const [classes, setClasses] = useState<CourseClass[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    sessionsApi.classes().then((res) => {
      setClasses(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Group classes by course
  const courseGroups: CourseGroup[] = [];
  const courseMap = new Map<string, CourseGroup>();
  for (const c of classes) {
    if (!courseMap.has(c.course_id)) {
      const group: CourseGroup = { course_id: c.course_id, code: c.course_code, name: c.course_name, classes: [] };
      courseMap.set(c.course_id, group);
      courseGroups.push(group);
    }
    courseMap.get(c.course_id)!.classes.push(c);
  }

  if (loading) return <div className="page"><p className="text-muted">Loading courses...</p></div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">My Courses</h1>
        <p className="page-subtitle">Your assigned courses and scheduled classes</p>
      </div>

      {courseGroups.length === 0 ? (
        <div className="card">
          <div className="card-body">
            <div className="empty-state">
              <p>No courses assigned to you yet.</p>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
          {courseGroups.map((course) => (
            <div className="card" key={course.course_id}>
              <div className="card-header">
                <div>
                  <span className="card-title" style={{ fontSize: 'var(--font-size-lg)' }}>
                    {course.code}
                  </span>
                  <span className="text-muted" style={{ marginLeft: 'var(--space-2)' }}>
                    {course.name}
                  </span>
                </div>
                <Link
                  to={`/lecturer/courses/${course.course_id}/students`}
                  className="btn btn-sm btn-secondary"
                >
                  All Enrolled Students
                </Link>
              </div>
              <div className="card-body">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Group</th>
                        <th>Day</th>
                        <th>Time</th>
                        <th>Classroom</th>
                        <th style={{ width: 200 }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {course.classes.map((cls) => (
                        <tr key={cls.id}>
                          <td style={{ fontWeight: 500, color: 'var(--color-text)' }}>
                            {cls.group_name || 'Default'}
                          </td>
                          <td>{DAY_NAMES[cls.day_of_week]}</td>
                          <td>{cls.start_time} – {cls.end_time}</td>
                          <td>{cls.classroom_name || '—'}</td>
                          <td>
                            <div className="flex gap-2">
                              <Link
                                to={`/lecturer/classes/${cls.id}`}
                                className="btn btn-sm btn-primary"
                              >
                                Schedule & Students
                              </Link>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
