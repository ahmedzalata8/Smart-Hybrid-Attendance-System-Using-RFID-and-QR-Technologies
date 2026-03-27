"""
Import all models so that SQLAlchemy / Alembic can discover them.
"""
from app.models.base import Base                                     # noqa: F401
from app.models.department import Department                         # noqa: F401
from app.models.user import User, UserRole                           # noqa: F401
from app.models.course import Course                                 # noqa: F401
from app.models.enrollment import Enrollment                         # noqa: F401
from app.models.classroom import Classroom                           # noqa: F401
from app.models.seat import Seat                                     # noqa: F401
from app.models.attendance_session import AttendanceSession, SessionStatus  # noqa: F401
from app.models.seat_state import SeatState                          # noqa: F401
from app.models.seat_state_history import SeatStateHistory           # noqa: F401
from app.models.attendance_record import AttendanceRecord, AttendanceStatus  # noqa: F401
from app.models.audit_log import AuditLog                            # noqa: F401
from app.models.scan_report import ScanReport                        # noqa: F401
