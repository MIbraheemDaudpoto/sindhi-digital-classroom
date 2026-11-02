# Sindhi Digital Classroom (SDC) — Batch 7 Delivery Report

**Project:** Sindhi Digital Classroom (SDC)  
**Curriculum:** Sindh Textbook Board (STBB), Classes 6–10  
**Repository:** `D:\Ai Agents\agency-agents\sindhi-digital-classroom`  
**Date:** October 16, 2026  
**Status:** **Fully Implemented and Verified (79 / 79 Pytest Tests Passing)**

---

## 1. Executive Summary & Objective

SDC Batch 7 successfully refactors the application into **three clearly separated, cohesive experiences** sharing a unified, professional design system inspired by the NexStudio aesthetic, tailored to public education in Sindh:

1. **Public Landing Website (`/`, `/about`, `/curriculum`, `/help`, `/privacy`, `/terms`):**
   - Introduces visitors and families to SDC with a confident Sindhi-first hero:
     > **سنڌيءَ ۾ سکو، پنهنجي رفتار سان اڳتي وڌو**  
     *(Learn in Sindhi, Advance at Your Own Pace)*
   - Features STBB Class 6–10 curriculum overview, live lesson discovery from `/api/lessons`, a 4-step learning workflow, key feature highlights, honest offline limitations (explaining why YouTube embeds require online access), honest AI tutor capabilities (explaining grounded STBB answers), and comprehensive FAQs.
   - **Zero Data Leakage:** Completely isolated from internal student records, submission data, teacher workspaces, or administrative tables.

2. **Dedicated Authentication Pages (`/login`, `/signup`, `/logout`, `/forgot-password`, `/reset-password`, `/unauthorized`):**
   - **Dedicated `/login`:** Two-column responsive layout with SDC branding, student mode (School Code + Student Code + PIN) and staff mode (Identifier + Password), password visibility toggle, accessible error handling, and safe return URL validation.
   - **Dedicated `/signup`:** Standalone registration strictly limited to the `STUDENT` role. Pulls valid schools dynamically from `/api/auth/schools`. Disallows privileged role selection (super admins, teachers, or reviewers cannot be created via public signup).
   - **Open Redirect Guard:** Rejects external redirect targets (`//`, `http:`, `https:`, `javascript:`) to defend against phishing and credential theft.
   - **Session Invalidation (`/logout`):** Clears session cookies, purges localStorage tokens, and cleanly redirects to `/login?logged_out=1`.
   - **Realistic Password Recovery (`/forgot-password`):** Provides authentic offline school guidance (school headmasters and teachers reset student PINs; district officers reset staff credentials) without fabricating nonexistent SMTP email services.

3. **Protected LMS Application (`/app`, `/app/learn`, `/app/learn/:lessonId`, `/app/progress`, `/app/assignments`, `/app/tutor`, `/app/teacher`, `/app/reviewer`, `/app/school`, `/app/district`, `/app/admin`):**
   - Dedicated application shell (`static/app.html`) featuring a role-aware sidebar navigation drawer, compact top bar, user identity pill, connectivity status, and offline sync indicator.
   - Enforces frontend and backend session route guards: unauthenticated visits to `/app` automatically redirect to `/login?next=...`.
   - Seamless deep-linking for `/app/learn/:lessonId` and role-specific workspace activation.
   - Preserves 100% of existing features: H.264 byte-range video streaming, YouTube privacy-enhanced embeds, smart interactive checkpoint quizzes, AI tutor with STBB citations, teacher approval gates, student assignments & grading, IndexedDB offline sync, and 6-role RBAC.

---

## 2. Complete URL and Page Structure Mapping

| URL Path | Target Experience | Implementation Path | Authentication Policy |
| :--- | :--- | :--- | :--- |
| `/` | Public Landing Homepage | `src/api/app.py` -> `static/landing.html` | Public (No auth required) |
| `/about` | About SDC & Mission | `src/api/app.py` -> `static/landing.html#about` | Public (No auth required) |
| `/curriculum` | STBB Classes 6–10 Overview | `src/api/app.py` -> `static/landing.html#curriculum` | Public (No auth required) |
| `/help` | Public Help & FAQs | `src/api/app.py` -> `static/landing.html#faq` | Public (No auth required) |
| `/privacy` | Privacy Policy | `src/api/app.py` -> `static/landing.html#privacy` | Public (No auth required) |
| `/terms` | Terms of Service | `src/api/app.py` -> `static/landing.html#terms` | Public (No auth required) |
| `/login` | Dedicated Login Page | `src/api/app.py` -> `static/login.html` | Public (Redirects to `/app` if already logged in) |
| `/signup` | Dedicated Student Registration | `src/api/app.py` -> `static/signup.html` | Public (Strictly registers ordinary `STUDENT` accounts) |
| `/logout` | Session Invalidation Flow | `src/api/app.py` -> Clears cookie & redirects | Public (Returns user to `/login?logged_out=1`) |
| `/forgot-password` | Realistic Password Recovery | `src/api/app.py` -> `static/forgot_password.html` | Public (No auth required) |
| `/reset-password` | Password Reset Guidance | `src/api/app.py` -> `static/forgot_password.html` | Public (No auth required) |
| `/unauthorized` | Access Denied (403) Page | `src/api/app.py` -> `static/unauthorized.html` | Public / Authenticated |
| `/app` | Role-aware LMS Dashboard | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/learn` | Student Curriculum & Lessons | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/learn/:lessonId`| Lesson Classroom & Player | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/progress` | Learning Progress & Streaks | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/assignments` | Assignments & Grading | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/tutor` | STBB Grounded AI Tutor | `src/api/app.py` -> `static/app.html` | **Protected (Requires Valid Session)** |
| `/app/teacher` | Teacher Workspace | `src/api/app.py` -> `static/app.html` | **Protected (TEACHER / SUPER_ADMIN)** |
| `/app/reviewer` | Content Review Queue | `src/api/app.py` -> `static/app.html` | **Protected (CONTENT_REVIEWER / SUPER_ADMIN)** |
| `/app/school` | School Administration | `src/api/app.py` -> `static/app.html` | **Protected (SCHOOL_ADMIN / SUPER_ADMIN)** |
| `/app/district` | District Reporting & Summaries | `src/api/app.py` -> `static/app.html` | **Protected (DISTRICT_OFFICER / SUPER_ADMIN)** |
| `/app/admin` | Platform Management & Audits | `src/api/app.py` -> `static/app.html` | **Protected (SUPER_ADMIN)** |

---

## 3. Public Landing Website Implementation (`static/landing.html`)

- **Sticky Glassmorphism Header:** SDC logo, Home, Curriculum, How it Works, Features, FAQ, dedicated Login button, and primary "Get Started" call to action.
- **Hero Section:**
  - Headline: **سنڌيءَ ۾ سکو، پنهنجي رفتار سان اڳتي وڌو**
  - Subtitle: Educational digital platform for Sindh Textbook Board (Classes 6–10) with interactive video quizzes, curriculum-grounded AI assistance, and offline study synchronization.
  - Primary CTA (`Start Learning` -> `/signup`) and Secondary CTA (`Explore Curriculum` -> `#curriculum`).
  - Educational feature pills: Class 6–10 STBB, 100% Sindhi Interface, Offline Synced, Video Quizzes.
- **Curriculum Matrix:** Interactive class tabs (Classes 6, 7, 8, 9, 10) displaying official subjects (General Science, Mathematics, Sindhi Salis, English Grammar & Composition, Computer Science) with real syllabus highlights.
- **Dynamic Lesson Discovery:** Asynchronously fetches real lesson data from `/api/lessons` so visitors can preview genuine lesson topics.
- **4-Step Learning Workflow:**
  1. *Open Lesson (سبق کوليو)*
  2. *Interactive Video Quizzes (وڊيو دوران سوال)*
  3. *Ask AI Tutor (اي آءِ ٽيوٽر کان پڇو)*
  4. *Offline Auto-Sync (آف لائن محفوظ ۽ خودڪار سنڪ)*
- **Honest Limitations & Capabilities:**
  - *Offline Limitations:* Clearly clarifies that local MP4 video lessons and quizzes function completely offline, whereas external YouTube links require internet access.
  - *AI Tutor Scope:* Explains that the AI tutor strictly cites verified STBB curriculum textbooks and refuses out-of-scope queries rather than generating arbitrary web answers.
- **Public Footer:** SDC brand statement, quick links to About, Curriculum, Help, Privacy, Terms, Login, and Signup.

---

## 4. Authentication Architecture & Security Hardening

### Dedicated Login (`static/login.html`)
- **Two-Column Responsive Layout:** Brand narrative and visual illustration on one side; clean, accessible login form on the other.
- **Dual Mode Support:**
  - *Student Mode:* School Code, Student ID / Code, and Numeric PIN.
  - *Staff Mode:* Username / Phone / Email and Password.
- **Password Visibility Toggle:** Eye icon button enabling secure password inspection for young learners.
- **Auto-Session Detection:** If a user visits `/login` while already possessing a valid session, they are automatically forwarded to `/app`.
- **Open Redirect Guard:** The `next` return parameter is strictly sanitized:
  ```javascript
  function isSafeReturnUrl(url) {
    if (!url || typeof url !== 'string') return false;
    const trimmed = url.trim();
    if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.startsWith('/\\')) return false;
    if (trimmed.includes('://') || trimmed.toLowerCase().startsWith('javascript:')) return false;
    return true;
  }
  ```
  External redirect targets are ignored, safely falling back to `/app`.

### Dedicated Signup (`static/signup.html`)
- **Strict Role Lockdown:** Public registration exclusively creates `STUDENT` accounts.
- **Privilege Escalation Prevention:**
  - In `src/services/auth_service.py` and `src/api/routes/auth.py`, incoming registration requests are strictly checked:
    ```python
    if req.role and req.role != Role.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public registration is restricted to students only. Staff accounts must be provisioned by school or district administrators."
        )
    ```
  - Submitting `TEACHER`, `CONTENT_REVIEWER`, `SCHOOL_ADMIN`, `DISTRICT_OFFICER`, or `SUPER_ADMIN` immediately raises HTTP 400.
- **School Verification:** Validates that the selected `school_code` exists in the database.
- **Student Code Uniqueness:** Checks database for existing `school_code + student_code` pairs to prevent duplicate registrations.
- **Cryptographic PIN Storage:** Enforces 4–6 digit numeric PINs, hashed securely via PBKDF2 (`hash_password(pin)`).
- **Public Schools Endpoint:** `GET /api/auth/schools` returns public school metadata (code, name, district) without leaking any student records or teacher credentials.

### Session Lifecycle & Logout (`/logout`)
- Calling `/logout` terminates server-issued cookies (`token=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`).
- Redirects to `/login?logged_out=1`.
- On the client side, `performLogout()` purges `localStorage.removeItem('sdc_token')` and `localStorage.removeItem('sdc_current_user')`.
- Revisiting any `/app` route triggers the route guard and redirects back to `/login?next=...`.

---

## 5. Protected LMS Application Shell (`static/app.html`)

- **Role-Aware Sidebar Navigation:**
  - Displays only permitted workspaces based on the authenticated user's role:
    - `STUDENT`: Lessons (`/app/learn`), Progress (`/app/progress`), Assignments (`/app/assignments`), AI Tutor (`/app/tutor`).
    - `TEACHER`: Teacher Studio (`/app/teacher`), Assignments & Grading (`/app/assignments`), Curriculum Explorer.
    - `CONTENT_REVIEWER`: Review Queue (`/app/reviewer`), Approval Actions.
    - `SCHOOL_ADMIN`: School User Administration (`/app/school`).
    - `DISTRICT_OFFICER`: District Analytics & Summaries (`/app/district`).
    - `SUPER_ADMIN`: System Admin, Audit Logs, and User Provisioning (`/app/admin`).
- **Compact Top Bar:** Shows SDC Logo, current page title, active online/offline status pill, pending sync count, active role badge, user profile indicator, and one-click Logout button.
- **Preserved Feature Set:**
  - 100% of existing functional modules remain active:
    - STBB curriculum browser (Classes 6–10).
    - H.264 byte-range video streaming player.
    - Official YouTube privacy-enhanced embeds.
    - Interactive checkpoint video quizzes with skip auditing.
    - Grounded AI tutor with clickable lesson timestamp citations.
    - Teacher lesson upload & approval gate.
    - Assignments submission and grading engine.
    - Offline unit pack download & IndexedDB synchronization.

---

## 6. Automated Regression & Test Results

The full test suite was executed against the repository:

```powershell
pytest
```

### Full Test Summary

| Test Suite | Total Tests | Passed | Failed | Status |
| :--- | :---: | :---: | :---: | :---: |
| `tests/test_batch7_routes_and_auth.py` | 16 | 16 | 0 | **PASSED** |
| `tests/test_rbac_and_video.py` | 21 | 21 | 0 | **PASSED** |
| `tests/test_lessons_curriculum.py` | 12 | 12 | 0 | **PASSED** |
| `tests/test_auth_rbac.py` | 8 | 8 | 0 | **PASSED** |
| `tests/test_offline_sync.py` | 7 | 7 | 0 | **PASSED** |
| `tests/test_assignments.py` | 5 | 5 | 0 | **PASSED** |
| `tests/test_smart_video_quiz.py` | 4 | 4 | 0 | **PASSED** |
| `tests/test_ai_tutor_rag.py` | 3 | 3 | 0 | **PASSED** |
| `tests/test_dashboards.py` | 3 | 3 | 0 | **PASSED** |
| **Total** | **79** | **79** | **0** | **100% PASSED (in 214.76s)** |

### Specific Batch 7 Test Cases Verified (`test_batch7_routes_and_auth.py`)

1. `test_public_landing_routes_accessible_without_auth`: Verifies `/`, `/about`, `/curriculum`, `/help`, `/privacy`, and `/terms` return HTTP 200 HTML without credentials.
2. `test_login_page_renders_cleanly`: Verifies `/login` serves dedicated authentication UI.
3. `test_signup_page_renders_cleanly`: Verifies `/signup` serves dedicated student registration UI.
4. `test_forgot_password_page_renders_cleanly`: Verifies `/forgot-password` and `/reset-password` return offline school recovery guidance.
5. `test_unauthorized_page_renders_cleanly`: Verifies `/unauthorized` returns 403 access-denied page.
6. `test_lms_shell_routes_serve_app_html`: Verifies `/app`, `/app/learn`, `/app/learn/test-lesson-id`, `/app/progress`, `/app/tutor`, etc. serve the application shell.
7. `test_public_pages_do_not_leak_private_data`: Confirms public landing HTML contains no student progress or admin tables.
8. `test_curriculum_catalog_publicly_discoverable`: Confirms `/api/lessons` allows visitors to explore curriculum topics.
9. `test_public_schools_endpoint`: Confirms `/api/auth/schools` returns code, name, and district for registration.
10. `test_student_registration_success`: Confirms valid student registration creates an account with hashed PIN and returns valid JWT token.
11. `test_registration_privilege_escalation_rejected`: Confirms requesting role `SUPER_ADMIN`, `TEACHER`, `SCHOOL_ADMIN`, etc. returns HTTP 400.
12. `test_registration_duplicate_student_rejected`: Confirms duplicate student code at same school returns HTTP 400.
13. `test_registration_invalid_school_rejected`: Confirms non-existent school code returns HTTP 400.
14. `test_registration_weak_pin_rejected`: Confirms non-numeric or short PIN returns HTTP 422/400.
15. `test_logout_endpoint_redirects_to_login`: Confirms `/logout` invalidates session cookie and redirects to `/login?logged_out=1`.
16. `test_protected_endpoints_require_auth`: Confirms sensitive API endpoints (e.g. `/api/auth/me`, `/api/dashboards/student`) strictly reject unauthenticated requests.

---

## 7. Files Created and Modified

### Created Files
- `static/landing.html`: Standalone public marketing & curriculum website.
- `static/login.html`: Dedicated two-column responsive login page.
- `static/signup.html`: Dedicated student registration page.
- `static/forgot_password.html`: Authentic offline school password recovery guide.
- `static/unauthorized.html`: 403 access-denied page.
- `static/app.html`: Dedicated protected LMS application shell.
- `tests/test_batch7_routes_and_auth.py`: Comprehensive 16-test suite for Batch 7 routes, registration, and security.
- `docs/BATCH_7_IMPLEMENTATION_REPORT.md`: This comprehensive implementation report.

### Modified Files
- `src/api/app.py`: Mounted separate route handlers for public pages, authentication pages, logout redirect, and protected LMS subpaths.
- `src/models/schemas.py`: Added `StudentSignupRequest` and `PublicSchoolResponse` schemas.
- `src/services/auth_service.py`: Implemented `register_student()` and `list_public_schools()` with PBKDF2 hashing, role locking, and duplicate prevention.
- `src/api/routes/auth.py`: Added `POST /api/auth/register`, `POST /api/auth/signup`, and `GET /api/auth/schools`.
- `static/css/style.css`: Added design system styles for landing header, hero, curriculum matrix, feature cards, FAQ accordions, two-column auth layouts, and LMS application shell.
- `static/js/app.js`: Removed boot-time demo credentials; implemented session guard redirecting unauthenticated `/app` visits to `/login?next=...`; updated URL routing and deep-linking for `/app/*`; hardened `performLogout()`.
- `pyproject.toml`: Configured `pythonpath = ["."]` for seamless root-level `pytest` runs.
- `docs/PRD_COMPLIANCE_MATRIX.md`: Appended FR-37 through FR-42 to track Batch 7 requirements.

---

## 8. Exact PowerShell Commands to Run Locally

### Start Application Server
```powershell
cd "D:\Ai Agents\agency-agents\sindhi-digital-classroom"
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### Access Three Separated Experiences in Browser
- **Public Landing Page:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Dedicated Login Page:** [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- **Dedicated Signup Page:** [http://127.0.0.1:8000/signup](http://127.0.0.1:8000/signup)
- **Protected LMS Application:** [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app) *(Redirects to `/login?next=/app` if unauthenticated)*

### Run Full Test Suite
```powershell
cd "D:\Ai Agents\agency-agents\sindhi-digital-classroom"
pytest
```

---

## 9. Remaining Configuration Needs & Production Readiness

1. **Email / SMS Verification Service:** Currently, password recovery follows rural Sindh school protocol (school administrators/teachers reset student PINs; district officers reset staff passwords). When budget allows, an authentic SMS gateway (e.g. Jazz/Telenor API) can be integrated for teacher and staff mobile recovery.
2. **Production HTTPS:** Deployment on public domain must enforce `Secure` cookie flag and `Strict-Transport-Security` headers in the reverse proxy (Nginx/Caddy).
3. **Database Migration Pipeline:** For multi-school production scaling, Alembic migration scripts should manage future schema versions alongside `src/database/schema.py`.
