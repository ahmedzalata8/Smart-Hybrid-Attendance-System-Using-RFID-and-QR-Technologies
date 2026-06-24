# 🎓 Smart Hybrid Attendance System — RFID + QR

A full-stack, dual-factor classroom attendance platform. It prevents attendance
fraud by combining two independent signals:

- **Factor 1 — Logical claim:** the student scans an expiring, cryptographically
  signed **QR code** and claims a seat.
- **Factor 2 — Physical presence:** **UHF RFID** readers detect the student's tag
  at that seat in real time.

A claim is only accepted when both factors agree. Sessions are continuously
monitored, finalized against a minimum-presence threshold, and written to a
SHA-256 **chained audit log** that can't be tampered with after the fact.

> This repository is a **complete snapshot for moving the project between
> machines** — it includes the source for both subsystems **and the databases**
> so you can clone it on another PC and pick up exactly where you left off.

---

## 📦 Repository structure

```
Smart-Hybrid-Attendance-System/
├── README.md                ← you are here (start here)
├── .gitignore
│
├── attendance-system/       ← the web platform
│   ├── server/              FastAPI + SQLAlchemy (async) + Alembic backend
│   │   ├── app/             routers, models, schemas, services, websockets
│   │   ├── alembic/         database migrations
│   │   ├── .env             dev config (committed on purpose — see "Credentials")
│   │   └── requirements.txt
│   └── dashboard/           React 18 + Vite + TypeScript frontend
│       ├── src/             admin / lecturer / hod / student pages
│       └── package.json
│
├── rfid/                    ← the hardware / scanner side
│   ├── *.py                 RFID capture, QR service, stepper-motor control
│   ├── rfid_scans.db        SQLite scan history (committed)
│   ├── Datasheets/          R16-12DB reader datasheet + photos
│   ├── CH341SER_driver/     CH340 USB-serial driver (for the RFID reader)
│   ├── CP210x_driver_extracted/  CP210x USB-serial driver (for the ESP32)
│   └── requirements.txt
│
└── database/
    ├── attendance_db.sql    full PostgreSQL dump (all data)
    └── README.md            how to restore the databases
```

The two subsystems are independent and can be developed/run separately. The web
platform (`attendance-system`) is the main deliverable; `rfid` is the
hardware-facing scanning side that feeds it.

---

## 🧱 Tech stack

| Layer | Technology |
|------|------------|
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), APScheduler |
| Database | **PostgreSQL 17** (via asyncpg), Alembic migrations |
| Frontend | React 18, Vite, TypeScript, React Router, Axios |
| RFID side | Python 3, Flask, pyserial, qrcode; R16-12DB UHF reader + ESP32 |

---

## 🛠️ Prerequisites (install these first on the new PC)

1. **[Git](https://git-scm.com/downloads)**
2. **[Python 3.12+](https://www.python.org/downloads/)** — backend + RFID scripts
3. **[Node.js 18+](https://nodejs.org/en/download/)** — frontend dashboard
4. **[PostgreSQL 17](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)**
   — install with superuser `postgres` and remember the password
   (this project's dev config uses password `attend`)

*(Redis is referenced in config but is optional for local development — the app
runs without it.)*

---

## 🚀 Full setup on another PC (start to finish)

### 0. Clone
```bash
git clone https://github.com/ahmedzalata8/Smart-Hybrid-Attendance-System-Using-RFID-and-QR-Technologies.git
cd Smart-Hybrid-Attendance-System-Using-RFID-and-QR-Technologies
```

### 1. Restore the database
The full PostgreSQL data is in `database/attendance_db.sql`. Make sure
PostgreSQL is running, then:
```bash
cd database
psql -h localhost -U postgres -f attendance_db.sql      # password: attend
cd ..
```
This drops/recreates `attendance_db` and loads **all data** (users, courses,
sessions, attendance records, audit log). Full details and a Windows
(`psql.exe` full-path) variant are in [database/README.md](database/README.md).

### 2. Run the backend (FastAPI)
```bash
cd attendance-system/server
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API runs at **http://127.0.0.1:8000** (interactive docs at `/docs`).

> The backend reads its config from `server/.env`, which is included. If your
> PostgreSQL password is **not** `attend`, edit `DATABASE_URL` in
> `server/.env` accordingly.

### 3. Run the frontend (React dashboard)
In a **second terminal**:
```bash
cd attendance-system/dashboard
npm install
npm run dev
```
Open **http://localhost:5173**.

### 4. (Optional) Run the RFID / hardware side
Only needed when working with the physical reader.
```bash
cd rfid
python -m venv venv
.\venv\Scripts\activate          # or: source venv/bin/activate
pip install -r requirements.txt
python reader_capture_multi.py   # auto-detects the serial port
```
See [rfid/README.md](rfid/README.md) for hardware wiring, the RFID/QR flow, and
the Flask API. USB-serial drivers for the reader (CH340) and ESP32 (CP210x) are
bundled under `rfid/CH341SER_driver/` and `rfid/CP210x_driver_extracted/`.

---

## 👥 Demo credentials

These accounts already exist in the restored database:

| Role | Email | Password |
|------|-------|----------|
| Lecturer | `dr.shawky@aast.edu` | `lecture123` |
| Head of Department | `hod@aast.edu` | `hod123` |

If you ever start from an empty database instead of the dump, the seed scripts
in `attendance-system/server/` (e.g. `add_demo_users.py`, `seed_5x5_shawky.py`)
recreate demo data.

---

## 🔑 Credentials & the committed `.env`

For a frictionless machine-to-machine transfer, this repo **intentionally
commits**:

- `attendance-system/server/.env` — backend config
- `database/attendance_db.sql` and `rfid/rfid_scans.db` — the actual data

The `.env` contains **local/dev placeholders only** (DB password `attend`, a
literal `dev-insecure-...` JWT key, sample reader API keys) and the repository is
**private**, so there is no real secret exposure.

⚠️ **If you ever make this repository public or deploy it:** rotate `SECRET_KEY`,
change the PostgreSQL password, and move `server/.env` out of git (a
`server/.env.example` template is already included for that purpose).

---

## 🔄 Keeping the snapshot fresh

When you make progress on one machine and want to carry it to another:

```bash
# refresh the DB snapshot (from the database/ folder)
pg_dump -h localhost -U postgres -d attendance_db --clean --if-exists --create \
        --no-owner --no-privileges -f attendance_db.sql

git add -A
git commit -m "Sync: code + database snapshot"
git push
```
Then `git pull` + re-run the **Restore the database** step on the other machine.

---

## 📚 More documentation

- `attendance-system/PROJECT_CONTEXT.txt` — full architecture, 12+ table schema,
  business logic, and current project status
- `attendance-system/IMPLEMENTATION_PLAN.md`, `WALKTHROUGH.md`,
  `PRESENTATION_GUIDE.md`
- `rfid/ARCHITECTURE.md`, `rfid/ESP32_SETUP.md`, `rfid/DIGITAL_TWIN_GUIDE.md`
