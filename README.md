# 🎓 University Attendance System (Dual-Factor Verification)

A full-stack, enterprise-grade attendance tracking solution built with modern web technologies. This system prevents attendance fraud by using **Dual-Factor Verification**: requiring students to logically claim a cryptographic QR code via a mobile app, while simultaneously verifying their physical presence using IoT seat sensors.

---

## 🛠️ Prerequisites

Before you can run the application, you must download and install the following software:

1.  **[Node.js (v18 or higher)](https://nodejs.org/en/download/)** - Required to run the React frontend.
2.  **[Python (v3.12 or higher)](https://www.python.org/downloads/)** - Required to run the FastAPI backend.
3.  **[PostgreSQL (v17 or higher)](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)** - The core database used for storing all highly-relational data and audit logs.

---

## 🚀 How to Download & Install

### 1. Download the Project
Open your terminal (Command Prompt, PowerShell, or bash) and clone the repository to your local machine:
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/attendance-system.git
cd attendance-system
```
*(Note: Replace `YOUR_GITHUB_USERNAME` with the actual link to your repository if someone else is cloning it).*

### 2. Set Up the Database
Open PostgreSQL (using `pgAdmin` or `psql`) and ensure you have created a blank database. By default, the application looks for:
*   **Database Name:** `attendance_db`
*   **Username:** `postgres`
*   **Password:** `attend`

### 3. Install Backend Dependencies (FastAPI)
Open a terminal and navigate to the backend directory:
```bash
cd server
```

Create an isolated virtual environment to hold your Python packages:
```bash
# Create the virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
# Activate it (Mac/Linux)
source venv/bin/activate
```

Install the required Python modules:
```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies (React)
Open a **new, separate terminal** and navigate to the frontend directory:
```bash
cd dashboard
```

Install the required Node modules:
```bash
npm install
```

---

## 💻 How to Open and Run the App

Whenever you want to use the app, you need to start both the Python backend and the React frontend. You will need two command line terminals open at the same time.

### Terminal 1: Run the Backend
Ensure your virtual environment is activated (`.\venv\Scripts\activate`), then run:
```bash
cd server
uvicorn app.main:app --reload --port 8000
```
*The API is now running at `http://127.0.0.1:8000`.*

### Terminal 2: Run the Frontend
```bash
cd dashboard
npm run dev
```

The frontend will automatically start. Open your web browser and go to:
**👉 `http://localhost:5173`**

---

## 👥 Demo Credentials
If you seeded the database using the provided Python scripts (e.g., `python add_demo_users.py`), you can test the system using these pre-made roles:
*   **Lecturer (Session Creator):** `dr.shawky@aast.edu` / Password: `lecture123`
*   **Head of Department (Digital Twin Viewer):** `hod@aast.edu` / Password: `hod123`
