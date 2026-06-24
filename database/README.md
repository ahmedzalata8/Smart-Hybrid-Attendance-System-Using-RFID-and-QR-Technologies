# Database Snapshots

This folder contains the data needed to continue the project on another machine.

| File | Belongs to | Engine | How to restore |
|------|-----------|--------|----------------|
| `attendance_db.sql` | `attendance-system/server` | PostgreSQL 17 | `psql` (see below) |
| *(SQLite file)* `../rfid/rfid_scans.db` | `rfid` | SQLite | Already a file — nothing to restore, the app opens it directly |

---

## Restore the PostgreSQL database (`attendance_db`)

The attendance server stores everything (users, courses, sessions, attendance
records, audit log, etc.) in PostgreSQL. The dump below is a **full snapshot
including all data**, taken with `pg_dump --create --clean`.

### Prerequisites
- PostgreSQL 17 installed and running
- A superuser named `postgres` with password `attend`
  (this matches `server/.env`; change both if you use different credentials)

### One command

The dump recreates the database from scratch (it drops `attendance_db` if it
already exists, then recreates it and loads all data):

```bash
# From this database/ folder
psql -h localhost -U postgres -f attendance_db.sql
```

On Windows, if `psql` is not on your PATH, use the full path:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -f attendance_db.sql
```

You'll be prompted for the `postgres` password (`attend`). To avoid the prompt:

```powershell
$env:PGPASSWORD = "attend"; & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -f attendance_db.sql
```

### Verify
```bash
psql -h localhost -U postgres -d attendance_db -c "\dt"
```
You should see 15 tables (roles, departments, users, courses, enrollments,
classrooms, seats, attendance_sessions, seat_states, seat_state_history,
attendance_records, audit_logs, course_classes, rfid_readings, alembic_version).

---

## Re-creating the dump (on the source machine)

If you change data and want to refresh this snapshot:

```powershell
$env:PGPASSWORD = "attend"
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -h localhost -U postgres -d attendance_db `
    --clean --if-exists --create --no-owner --no-privileges `
    -f attendance_db.sql
```

---

## The RFID SQLite database

`../rfid/rfid_scans.db` is a plain SQLite file and is committed as-is. The RFID
scripts open it directly (default path `rfid_scans.db`), so no restore step is
needed — just keep the file in the `rfid/` folder.
