# SDC Authentication & Session Verification Report (Phase 2)

**Project:** Sindhi Digital Classroom (SDC)  
**Security Focus:** Authentication Lifecycle, Navigation Continuity, Two-Role RBAC Lock, Multi-Worker Session Revocation  
**Audit Standard:** `agency-application-security-engineer` & `agency-backend-architect`

---

## 1. Root Cause Analysis: Navigation and Login Continuity Defect

### Observed Issue
Users clicking `← عوامي ويب سائيٽ` from the logged-in LMS returned to the public landing page (`landing.html`). When clicking "لاگ ان" or navigating back to the LMS, users encountered login prompts or inconsistent session state.

### Root Cause
1. **Public Header Navbar State:** The public landing header statically rendered `<a href="/login">لاگ ان</a>` regardless of whether a valid session token existed in `localStorage.getItem('sdc_current_user')`.
2. **Missing Token-Aware Redirect on Public Catalog Links:** Public lesson discovery cards in `landing.html` linked to `/login?next=/app/learn/${l.id}` instead of immediately detecting valid sessions and taking authenticated users directly into the LMS.
3. **In-Memory Session Revocation Vulnerability:** Prior to Phase 2, `AuthService._revoked_users` was stored exclusively in an in-memory dictionary. Upon any process restart or in a multi-worker deployment (e.g. Gunicorn / Uvicorn with multiple workers), session revocation checks failed silently, either invalidating valid sessions or permitting revoked tokens to continue.

---

## 2. Implemented Architecture and Fixes

### A. Persistent Multi-Worker Session Revocation (`revocation_cutoff_epoch`)
- Added column `revocation_cutoff_epoch REAL DEFAULT 0.0` to the `users` SQLite table with index `idx_users_revocation`.
- Migrated `init_db()` in `src/database/session.py` to auto-apply this schema addition.
- Updated `verify_session_token()` and `revoke_user_sessions()` in `src/services/auth_service.py`:
  - When a user logs out or resets their PIN, `revocation_cutoff_epoch` is updated in SQLite atomically.
  - During token verification, if in-memory cache is cold (e.g. after server reboot or across worker processes), the revocation cutoff is queried directly from SQLite. Any token timestamp prior to this epoch is rejected with `401 Unauthorized`.

### B. Smart Navigation Session Synchronization
- Implemented `syncAuthNavState()` in `static/landing.html`:
  - On page load, if a valid session exists in `localStorage`, the login button transforms to `LMS ڏانهن واپس ({user_code})` and links directly to `/app`.
  - Public lesson cards dynamically route authenticated users straight into the classroom view.

### C. Strict Two-Role Security Policy (`STUDENT`, `ADMIN`)
- Enforced at both the dependency layer (`src/api/deps.py`) and schema validation.
- Administrative roles (`SUPER_ADMIN`, `SCHOOL_ADMIN`, `TEACHER`, `CONTENT_REVIEWER`, `DISTRICT_OFFICER`) are unified under `ADMIN` for authorization checks.
- Students attempting privileged operations (creating assignments, approving quiz drafts, viewing audit logs) receive a strict `403 Forbidden`.
- Public registration (`POST /api/auth/register`) enforces `STUDENT` role assignment; any attempt to supply privileged roles is rejected with `400 Bad Request`.

---

## 3. Automated Test Verification Results

All tests pass under strict production settings (`allow_test_query_auth=False`):

| Test Case | Module | Description | Result |
| :--- | :--- | :--- | :--- |
| `test_workflow_student_login_public_nav_and_return` | `tests/test_e2e_user_workflows.py` | Valid session survives public website navigation | **PASSED** |
| `test_workflow_logout_and_session_revocation` | `tests/test_e2e_user_workflows.py` | Immediate token rejection on logout | **PASSED** |
| `test_workflow_multi_worker_revocation_survives_memory_reset` | `tests/test_e2e_user_workflows.py` | Revocation cutoff survives memory purge | **PASSED** |
| `test_workflow_student_idor_and_privilege_escalation_blocked` | `tests/test_e2e_user_workflows.py` | Student-to-student IDOR and Admin API attempts blocked | **PASSED** |
| `test_production_rejects_query_parameter_auth_bypass` | `tests/test_two_role_security.py` | Query parameter spoofing rejected | **PASSED** |
| `test_tampered_token_is_rejected` | `tests/test_two_role_security.py` | HMAC cryptographic signature validation | **PASSED** |
| `test_complete_password_recovery_workflow` | `tests/test_otp_password_recovery.py` | Mobile OTP password reset with single-use token | **PASSED** |
