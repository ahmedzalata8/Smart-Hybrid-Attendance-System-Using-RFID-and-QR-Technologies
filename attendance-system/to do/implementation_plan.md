# Admin Classrooms Page with Digital Twin & Schedule Management

Create a new **Admin Classrooms** page in the admin panel that allows creating/editing classrooms with an interactive digital twin seat-map preview, plus enhanced schedule management capabilities for dynamically adding courses and schedule timings to lecturers and students.

## Proposed Changes

### Backend — API & Schemas

#### [MODIFY] [admin.py](file:///c:/Users/pc/Desktop/attendance-system/server/app/schemas/admin.py)

Add Pydantic schemas for CRUD operations on classrooms:
- `AdminClassroomCreate` — name, department_id, building, floor, layout_rows, layout_cols
- `AdminClassroomUpdate` — all fields optional
- `AdminClassroomOut` — includes id, department_name, seat count, full details

#### [MODIFY] [admin.py](file:///c:/Users/pc/Desktop/attendance-system/server/app/routers/admin.py)

Add full CRUD endpoints for classrooms (replacing the existing read-only list):
- `GET /admin/classrooms` — list all classrooms with department names, seat count, and building/floor info
- `POST /admin/classrooms` — create a new classroom + auto-generate its seat grid (rows × cols seats with labels A1, A2, etc.)
- `PUT /admin/classrooms/{id}` — update classroom info (name, building, floor). If layout_rows/cols change, regenerate the seat grid.
- `DELETE /admin/classrooms/{id}` — delete classroom and cascade seats
- `GET /admin/classrooms/{id}/seats` — return the full seat grid for digital twin preview
- `PUT /admin/classes/{class_id}` — update an existing class schedule (currently missing)

---

### Frontend — New Classrooms Page

#### [NEW] [AdminClassroomsPage.tsx](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/pages/admin/AdminClassroomsPage.tsx)

A new admin page with two main sections:

**1. Classroom List Table**
- Shows all classrooms with: Name, Department, Building, Floor, Grid Size (e.g. "5×5"), Seat Count, Actions
- Search/filter by name
- Create, Edit, Delete buttons

**2. Create/Edit Modal**
- Form fields: Name, Department (dropdown), Building, Floor, Rows, Columns
- **Live digital twin preview**: As the admin types rows/cols, a real-time seat grid preview renders below the form, showing the seat labels (A1, A2, B1, B2, etc.) in the Neobrutalism seat-cell style
- The grid dynamically resizes as rows/cols values change

**3. Classroom Detail View (expandable row or modal)**
- Shows the full seat grid digital twin for an existing classroom
- Each seat cell shows its label and RFID tag ID
- Visual matching of the existing twin page styles (seat-cell, seat-empty, etc.)

---

### Frontend — Enhanced Schedule Management

#### [MODIFY] [AdminClassesPage.tsx](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/pages/admin/AdminClassesPage.tsx)

Add **Edit** functionality (currently only has Create and Delete):
- Add an "Edit" button to each class row
- Open edit modal pre-filled with current values
- Allow changing lecturer, classroom, day, start/end time, group name
- Call `PUT /admin/classes/{id}` on save

#### [MODIFY] [AdminSchedulesPage.tsx](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/pages/admin/AdminSchedulesPage.tsx)

Enhance the enrollment page with inline course + schedule quick-add:
- Add a "Quick Add Course" button that opens a mini course-creation modal (reusing the same API) so admins don't have to leave the page
- Add a "Quick Add Schedule" button that opens a mini class-schedule modal
- Both feed back into the enrollment form dropdowns immediately

---

### Navigation & Routing

#### [MODIFY] [AdminLayout.tsx](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/components/AdminLayout.tsx)

Add a new sidebar link for "Classrooms" between "Courses" and "Classes", with a building/room SVG icon.

#### [MODIFY] [App.tsx](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/App.tsx)

Add route: `<Route path="classrooms" element={<AdminClassroomsPage />} />`

#### [MODIFY] [api.ts](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/services/api.ts)

Extend the `adminApi.classrooms` object with full CRUD methods:
- `create`, `update`, `delete`, `getSeats`
- Add `adminApi.classes.update` (currently missing)

---

### CSS Additions

#### [MODIFY] [index.css](file:///c:/Users/pc/Desktop/attendance-system/dashboard/src/index.css)

Add styles for:
- `.twin-preview` — the live seat grid preview inside the modal, smaller scale
- `.twin-preview .seat-cell` — scaled-down seat cells for the in-modal preview
- `.classroom-info-grid` — responsive info layout for classroom details
- `.quick-add-btn` — small inline button for quick-add actions in enrollment page

## Open Questions

> [!IMPORTANT]
> **Seat label convention**: Currently seats use labels like "A-1", "A-2". Should we keep this `[RowLetter]-[ColNumber]` pattern for auto-generated seats, or do you prefer a different format?

> [!NOTE]
> **Seat RFID tags**: When auto-generating seats for a new classroom, the system needs unique RFID tag IDs for each seat. I'll auto-generate placeholder tag IDs in the format `SEAT-{classroom_name}-{row}{col}` that can be updated later when physical tags are provisioned. Does this work for your prototype?

## Verification Plan

### Automated Tests
- Start the dev server and verify new API endpoints respond correctly
- Test classroom CRUD via browser: create, edit, delete classrooms
- Verify seat grid auto-generation matches the requested rows × cols
- Test the digital twin preview renders correctly in the create/edit modal
- Test class schedule editing (PUT endpoint)
- Test quick-add course/schedule from enrollment page

### Manual Verification
- Navigate to the new Classrooms page and verify the Neobrutalism styling matches existing pages
- Create a classroom and confirm the live seat grid preview updates dynamically
- Edit a class schedule and confirm changes persist
- Use quick-add buttons on the enrollment page to add a course and schedule inline
