# 🎓 University Attendance System: Presentation & Architecture Guide

This document is designed to help you understand and present exactly how the system works under the hood, how the components interact, and what every directory in the project does.

---

## 1. System Architecture Overview

The system is built on a modern **three-tier architecture**. 

### A. The Database (PostgreSQL 17)
The foundational layer and absolute source of truth. It is a highly-relational database consisting of **12 interconnected tables**.
*   **Structural Data:** `users`, `roles`, `departments`, `courses`, `enrollments`, `classrooms`, `seats`.
*   **Live Data:** `attendance_sessions` (active classes), `seat_states` (current IoT sensor data), `seat_state_history` (append-only ledger of sensor changes).
*   **Result Data:** `attendance_claims` (student requests), `attendance_records` (verified results), `audit_logs` (tamper-evident crypto hashes of finalized sessions).

### B. The Backend (Python + FastAPI)
This is "The Brain." It listens for requests, applies complex business logic, and talks to the database.
*   **Stateless Security:** It uses JWT (JSON Web Tokens). When a user logs in, they get a cryptographically signed token. Every subsequent request must include this token.
*   **Background Jobs:** It uses `APScheduler` to run a loop constantly in the background, looking for expired sessions to auto-finalize without requiring user input.
*   **Async Performance:** It uses asynchronous Python (`async`/`await`) and SQLAlchemy 2.0 to handle hundreds of concurrent requests (like an entire lecture hall of students scanning a QR code at the exact same moment) without blocking.

### C. The Frontend Dashboard (React + Vite + TypeScript)
This is the "Presentation Layer" for Lecturers and Heads of Departments (HoDs).
*   **Role-Based Access Control (RBAC):** The frontend checks the JWT token to see if the user is a Lecturer or HoD, and totally changes the UI routing and available pages based on that role.
*   **Reactive UI:** It uses React state to instantly update the UI (like the Digital Twin seat map updating every 3 seconds) without forcing the user to refresh the page.

---

## 2. The Core Concept to Present: "Dual-Factor Verification"

When presenting the system, this is the most critical workflow to explain. Traditional attendance systems fail because students can easily fake their location (GPS spoofing) or send a link to a friend at home. 

This system solves that by demanding **two independent factors of proof** simultaneously:

1.  **Logical Factor (The QR Code):** The QR code is cryptographically signed (HMAC-SHA256), contains a timestamp, and rotates. The student scanning this proves they have the current, valid token.
2.  **Physical Factor (The Seat Sensor):** The physical classroom seats have hardware (simulated by IoT readers) that continuously ping the Backend with `is_occupied = True/False`. 

**The Verification Engine:** When a student claims they are in seat "A3", the Backend instantly checks the *Live Data* (`seat_states`). If the physical sensor for A3 says `is_occupied = False`, the backend instantly rejects the claim with the reason: `"Seat not occupied (dual-factor mismatch)"`.

---

## 3. Complete Directory Breakdown

If you are asked to explain what the codebase contains, here is the exact breakdown:

### 📂 `server/` (The FastAPI Backend)
*   **`app/`** — *The core application code.*
    *   **`core/`**: Security mechanisms (JWT generation, password hashing), database connection engines, and dependency injection guards (e.g., `require_role`).
    *   **`models/`**: SQLAlchemy Definitions. These Python classes map directly to the 12 underlying PostgreSQL tables.
    *   **`schemas/`**: Pydantic Models. These strictly define and validate the exact JSON structure of data coming *in* from clients, and going *out* from the server.
    *   **`routers/`**: The URL Endpoints (e.g., `/api/auth`, `/api/sessions`, `/api/dashboard`). They receive requests and route them to the right service.
    *   **`services/`**: The heavy lifting.
        *   `qr_service.py`: Generates the crypto HMAC tokens.
        *   `scan_service.py`: Processes continuous IoT data streams.
        *   `finalization_service.py`: Calculates final presence percentages, revokes attendance if below the threshold, and generates the immutable `audit_logs` SHA-256 hash-chain.
        *   `scheduler.py`: The background clock that triggers auto-finalizations.
    *   **`websockets/`**: Manages persistent full-duplex connections (ready for future real-time pushes).
    *   **`main.py`**: The entry point that boots up the server, attaches all routers, and starts the scheduler.
*   **`alembic/` & `alembic.ini`** — The database migration system. It tracks changes to Python models and translates them into SQL `ALTER TABLE` commands.
*   **`seed_test.py`** — An automated script that simulates a full end-to-end flow of the system to ensure nothing is broken.
*   **`venv/` & `requirements.txt`** — The isolated Python environment and exact list of required libraries.

### 📂 `dashboard/` (The React Frontend)
*   **`src/`** — *The core user interface code.*
    *   **`components/`**: Reusable structural pieces, like the `LecturerLayout` and `HodLayout` sidebars.
    *   **`context/`**: `AuthContext.tsx`. This holds the global state of the application. It remembers who is logged in across all pages by storing and decoding the JWT.
    *   **`pages/`**: The actual viewing screens:
        *   `Login.tsx`: The authentication gate.
        *   `lecturer/`: Pages for creating sessions, viewing the QR code, and reading post-class reports.
        *   `hod/`: Pages for monitoring department-wide sessions and the live Digital Twin.
    *   **`services/`**: `api.ts`. This uses a library called `Axios` to actually build the HTTP requests. It acts as a middleman, automatically intercepting every outbound request to attach the `Authorization: Bearer <token>` header before it hits the backend.
    *   **`index.css`**: The central design system establishing all spacing, typography, colors, and layout rules to ensure a professional, cohesive look.
    *   **`App.tsx`**: The Application Router. It looks at the browser URL and decides which Page component to render on the screen.
    *   **`main.tsx`**: The exact spot where the React application attaches itself to the raw HTML document.
*   **`vite.config.ts`** — The compiler configuration. Notably, it contains a "Proxy", meaning any API request the frontend makes to `/api` is secretly forwarded to the Python server running on port 8000.
*   **`package.json`** — The Node.js ecosystem file defining exact versions of React, Axios, Vite, and other libraries used.

---

## 4. Suggested Presentation Demo Flow

If you are demoing the software live, follow this script to show off all features:

1.  **Start at the Login Page:** Explain that the system handles auth securely. Log in as Lecturer (`dr.smith@university.edu` / `lecture123`).
2.  **Create a New Session:** Explain that the system pulls available courses and smart-maps physical classrooms (like Room 101, instantly knowing it has a 5x5 grid of 25 seats). Mention the customizable variables: *Duration*, *Freshness Window*, and *Minimum Presence %*.
3.  **Show the Session Detail / QR Code:** Explain that this is what the students see on the projector. The QR data is cryptographically signed to prevent forgery.
4.  **Show the Digital Twin (Seat Map):** Click into the Seat Map. Explain that as students scan their mobile app (Mobile App Phase) and sit down (IoT Phase), this map lights up in real-time. 
5.  **Explain the Audit Trail:** Navigate back and hit "Close Session". Explain that the background engine just did the math on how long everyone sat in their seat. Point out the **"Integrity Hash"** that appears at the bottom — explain that this is a SHA-256 hash chained to previous sessions, meaning no database administrator or clever student can retroactively alter an attendance record without breaking the entire mathematical chain.
