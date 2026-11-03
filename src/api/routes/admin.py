"""Administrative & RBAC Governance routes for SDC.
Locked strictly to 2-Role System (STUDENT and ADMIN).
Provides user administration, AI question generation with approval gates,
audit logging, and system health monitoring.
Authored under agency-application-security-engineer and agency-api-platform-engineer.
"""

from datetime import datetime, timezone
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import get_current_user, require_roles
from src.config import settings
from src.database.session import get_db
from src.models.schemas import (
    AuditLogResponse,
    ChangeAdminCredentialsRequest,
    StudentInviteRequest,
    StudentProgressListResponse,
    UserCreateRequest,
    UserResponse,
    UserRole,
)
from src.services.auth_service import hash_pin_or_password, verify_pin_or_password
from src.services.question_generator import question_generator

router = APIRouter(prefix="/api/admin", tags=["Administration"])


@router.post("/student-invites", status_code=status.HTTP_201_CREATED)
async def create_student_invite(
    req: StudentInviteRequest,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Issue a single-use student registration code; only its hash is stored."""
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=req.expires_in_days)).isoformat()
    code = "SDC-" + secrets.token_urlsafe(12).replace("-", "A").replace("_", "B").upper()
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    with get_db() as conn:
        if req.school_id and not conn.execute("SELECT 1 FROM schools WHERE id = ?", (req.school_id,)).fetchone():
            raise HTTPException(status_code=404, detail="School not found.")
        conn.execute(
            "INSERT INTO student_invites (code_hash, school_id, created_by, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (code_hash, req.school_id or current_user.get("school_id"), current_user["id"], now.isoformat(), expires_at)
        )
        conn.execute(
            "INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at) VALUES (?, ?, 'STUDENT_INVITE_CREATED', 'student_invite', ?, ?, ?)",
            (str(uuid.uuid4()), current_user["id"], code_hash[:12], json.dumps({"expires_at": expires_at}), now.isoformat())
        )
    return {"invite_code": code, "expires_at": expires_at, "single_use": True}


@router.get("/students/progress", response_model=StudentProgressListResponse)
async def list_student_progress(
    q: Optional[str] = Query(None, max_length=80),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Admin-only progress overview limited to real Class 6 Math and Science records."""
    search = f"%{q.strip()}%" if q and q.strip() else None
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'STUDENT' AND (? IS NULL OR pseudonymous_code LIKE ?)",
            (search, search)
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT u.id AS user_id, u.pseudonymous_code AS student_code, s.name AS school_name,
              (SELECT COUNT(DISTINCT p.lesson_id) FROM progress p JOIN lessons l ON l.id=p.lesson_id
               JOIN courses c ON c.id=l.course_id WHERE p.user_id=u.id AND p.is_completed=1
                 AND c.class_level=6 AND c.subject IN ('Math','Science') AND l.status IN ('PUBLISHED','APPROVED')) AS completed_lessons,
              (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id=l.course_id
               WHERE c.class_level=6 AND c.subject IN ('Math','Science') AND l.status IN ('PUBLISHED','APPROVED')) AS total_lessons,
              (SELECT COUNT(*) FROM quiz_sessions qs WHERE qs.user_id=u.id AND qs.status='COMPLETED'
                 AND qs.class_level=6 AND qs.subject IN ('Math','Science')) AS completed_quizzes,
              (SELECT AVG(qs.percentage) FROM quiz_sessions qs WHERE qs.user_id=u.id AND qs.status='COMPLETED'
                 AND qs.class_level=6 AND qs.subject IN ('Math','Science')) AS average_quiz_score_pct,
              (SELECT MAX(activity_at) FROM (
                 SELECT p.updated_at AS activity_at FROM progress p WHERE p.user_id=u.id
                 UNION ALL SELECT COALESCE(qs.submitted_at,qs.created_at) FROM quiz_sessions qs
                   WHERE qs.user_id=u.id AND qs.status='COMPLETED'
              )) AS last_activity
            FROM users u LEFT JOIN schools s ON s.id=u.school_id
            WHERE u.role='STUDENT' AND (? IS NULL OR u.pseudonymous_code LIKE ?)
            ORDER BY u.pseudonymous_code COLLATE NOCASE LIMIT ? OFFSET ?
            """,
            (search, search, limit, offset)
        ).fetchall()
        summary = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM users WHERE role='STUDENT') AS students,
                 (SELECT COUNT(DISTINCT p.user_id || ':' || p.lesson_id) FROM progress p
                    JOIN lessons l ON l.id=p.lesson_id JOIN courses c ON c.id=l.course_id
                    JOIN users u ON u.id=p.user_id
                    WHERE u.role='STUDENT' AND p.is_completed=1 AND c.class_level=6
                      AND c.subject IN ('Math','Science') AND l.status IN ('PUBLISHED','APPROVED')) AS completed_lessons,
                 (SELECT COUNT(*) FROM quiz_sessions qs JOIN users u ON u.id=qs.user_id
                    WHERE u.role='STUDENT' AND qs.status='COMPLETED' AND qs.class_level=6
                      AND qs.subject IN ('Math','Science')) AS completed_quizzes,
                 (SELECT AVG(qs.percentage) FROM quiz_sessions qs JOIN users u ON u.id=qs.user_id
                    WHERE u.role='STUDENT' AND qs.status='COMPLETED' AND qs.class_level=6
                      AND qs.subject IN ('Math','Science')) AS average_quiz_score_pct"""
        ).fetchone()
    return StudentProgressListResponse(
        items=[dict(row) for row in rows], total=total, limit=limit, offset=offset,
        summary=dict(summary) if summary else {}
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    school_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """List active student accounts for administrative account support."""
    with get_db() as conn:
        query = """
            SELECT u.id, u.role, u.school_id, s.name as school_name, u.pseudonymous_code,
                   u.email, u.phone, u.language, u.created_at
            FROM users u
            LEFT JOIN schools s ON u.school_id = s.id
            WHERE u.role = 'STUDENT'
        """
        params = []
        if school_id:
            query += " AND u.school_id = ?"
            params.append(school_id)
        if role and role.upper() != "STUDENT":
            return []
        query += " ORDER BY u.created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [
            UserResponse(
                id=r["id"],
                role=r["role"],
                school_id=r["school_id"],
                school_name=r["school_name"],
                pseudonymous_code=r["pseudonymous_code"],
                email=r["email"],
                phone=r["phone"],
                language=r["language"] or "sindhi",
                created_at=r["created_at"]
            )
            for r in rows
        ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreateRequest,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Admin provisions an account. In 2-role system, role is either STUDENT or ADMIN."""
    now_iso = datetime.now(timezone.utc).isoformat()
    new_user_id = f"usr-{uuid.uuid4().hex[:8]}"
    assigned_school_id = req.school_id

    if req.role not in {UserRole.STUDENT, UserRole.ADMIN}:
        raise HTTPException(status_code=400, detail="Only Student and Admin accounts can be created.")
    role_to_assign = "STUDENT" if req.role == UserRole.STUDENT else "SUPER_ADMIN"

    caller_role = current_user.get("legacy_role") or current_user.get("role")

    # District Officer cannot provision accounts
    if caller_role == "DISTRICT_OFFICER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District Officers are not authorized to provision user accounts."
        )

    # School Admin boundaries & privilege escalation defense
    if caller_role == "SCHOOL_ADMIN":
        if req.role.value.upper() not in {"STUDENT", "TEACHER"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School Admins can only provision students or teachers."
            )
        if assigned_school_id and current_user.get("school_id") and assigned_school_id != current_user.get("school_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School Admins cannot create users for other schools."
            )

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE pseudonymous_code = ?",
            (req.pseudonymous_code.strip(),)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="هي ڪوڊ يا يوزر نالو اڳ ۾ ئي استعمال ۾ آهي (Pseudonymous code already exists)."
            )

        hashed = hash_pin_or_password(req.pin_or_password)
        conn.execute(
            """
            INSERT INTO users (id, role, school_id, pseudonymous_code, pin_hash, email, phone, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_user_id, role_to_assign, assigned_school_id, req.pseudonymous_code.strip(), hashed, req.email, req.phone, req.language, now_iso)
        )

        conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, 'USER_CREATED', 'user', ?, ?, ?)
            """,
            (str(uuid.uuid4()), current_user["id"], new_user_id, json.dumps({"role": role_to_assign, "code": req.pseudonymous_code}), now_iso)
        )

        school_name = None
        if assigned_school_id:
            s_row = conn.execute("SELECT name FROM schools WHERE id = ?", (assigned_school_id,)).fetchone()
            if s_row:
                school_name = s_row["name"]

        return UserResponse(
            id=new_user_id,
            role=role_to_assign,
            school_id=assigned_school_id,
            school_name=school_name,
            pseudonymous_code=req.pseudonymous_code,
            email=req.email,
            phone=req.phone,
            language=req.language,
            created_at=now_iso
        )


@router.post("/students/{student_id}/reset-pin", status_code=status.HTTP_200_OK)
async def admin_reset_student_pin(
    student_id: str,
    new_pin: str = Query(..., min_length=4, max_length=6),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Administrative assistance: Reset student PIN when mobile access is unavailable."""
    if not new_pin.isdigit() or len(new_pin) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be 4 to 6 numeric digits.")

    now_iso = datetime.now(timezone.utc).isoformat()
    new_hash = hash_pin_or_password(new_pin)

    with get_db() as conn:
        user = conn.execute("SELECT id, pseudonymous_code FROM users WHERE id = ? AND role = 'STUDENT'", (student_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شاگرد اڪائونٽ نه مليو (Student account not found).")

        conn.execute("UPDATE users SET pin_hash = ? WHERE id = ?", (new_hash, student_id))
        conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, 'ADMIN_PIN_RESET', 'user', ?, ?, ?)
            """,
            (str(uuid.uuid4()), current_user["id"], student_id, json.dumps({"student_code": user["pseudonymous_code"]}), now_iso)
        )

    return {"status": "ok", "message": f"شاگرد {user['pseudonymous_code']} جو پن ڪوڊ ڪاميابيءَ سان تبديل ڪيو ويو."}


@router.post("/change-credentials", status_code=status.HTTP_200_OK)
async def admin_change_credentials(
    req: ChangeAdminCredentialsRequest,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Change current administrator username and/or password with current password verification."""
    with get_db() as conn:
        admin_row = conn.execute("SELECT id, pseudonymous_code, pin_hash FROM users WHERE id = ?", (current_user["id"],)).fetchone()
        if not admin_row or not verify_pin_or_password(req.current_password, admin_row["pin_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="موجوده پاسورڊ غلط آهي (Current password is incorrect)."
            )

        new_hash = hash_pin_or_password(req.new_password)
        new_username = req.new_username.strip() if req.new_username else admin_row["pseudonymous_code"]

        # Check username uniqueness if changed
        if new_username != admin_row["pseudonymous_code"]:
            existing = conn.execute("SELECT id FROM users WHERE pseudonymous_code = ? AND id != ?", (new_username, current_user["id"])).fetchone()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"يوزر نالو '{new_username}' اڳ ۾ موجود آهي (Username already taken)."
                )

        conn.execute(
            "UPDATE users SET pseudonymous_code = ?, pin_hash = ? WHERE id = ?",
            (new_username, new_hash, current_user["id"])
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, 'ADMIN_CREDENTIALS_CHANGED', 'user', ?, ?, ?)
            """,
            (str(uuid.uuid4()), current_user["id"], current_user["id"], json.dumps({"new_username": new_username}), now_iso)
        )

    return {
        "status": "ok",
        "message": "ايڊمن جا يوزر نالو ۽ پاسورڊ ڪاميابيءَ سان تبديل ٿي ويا (Credentials updated successfully).",
        "username": new_username
    }


# --- AI Question Generation & Approval Endpoints ---

@router.post("/lessons/{lesson_id}/generate-questions", status_code=status.HTTP_200_OK)
async def generate_ai_questions_for_lesson(
    lesson_id: str,
    count: int = Query(3, ge=1, le=10),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Admin triggers AI draft question synthesis from lesson transcripts."""
    try:
        drafts = question_generator.generate_draft_questions_for_lesson(
            lesson_id=lesson_id,
            admin_user_id=current_user["id"],
            question_count=count
        )
        return {
            "status": "ok",
            "message": f"{len(drafts)} نوان سوال ڊرافٽ طور تيار ڪيا ويا آهن (Draft questions created for Admin approval).",
            "questions": drafts
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/questions/pending", status_code=status.HTTP_200_OK)
async def list_pending_quiz_questions(
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """List all quiz questions in PENDING_APPROVAL status awaiting Admin sign-off."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT q.*, l.title_sindhi as lesson_title
            FROM questions q
            JOIN lessons l ON q.lesson_id = l.id
            WHERE q.status = 'PENDING_APPROVAL'
            ORDER BY q.timestamp_seconds ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/questions/{question_id}/approve", status_code=status.HTTP_200_OK)
async def approve_quiz_question(
    question_id: str,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Approve a quiz question so it becomes visible to students during video playback."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        conn.execute(
            "UPDATE questions SET status = 'APPROVED', approved_by = ?, approved_at = ? WHERE id = ?",
            (current_user["id"], now_iso, question_id)
        )
        conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, 'QUESTION_APPROVED', 'question', ?, NULL, ?)
            """,
            (str(uuid.uuid4()), current_user["id"], question_id, now_iso)
        )
    return {"status": "ok", "message": "سوال منظور ڪيو ويو ۽ شاگردن لاءِ جاري ٿي چڪو آهي (Question approved)."}


@router.post("/questions/{question_id}/reject", status_code=status.HTTP_200_OK)
async def reject_quiz_question(
    question_id: str,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Reject a draft quiz question."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        conn.execute(
            "UPDATE questions SET status = 'REJECTED', approved_by = ?, approved_at = ? WHERE id = ?",
            (current_user["id"], now_iso, question_id)
        )
    return {"status": "ok", "message": "سوال رد ڪيو ويو (Question rejected)."}


# --- System Audit Logs & Diagnostics ---

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Retrieve platform security audit logs."""
    caller_role = current_user.get("legacy_role") or current_user.get("role")
    if caller_role in {"SCHOOL_ADMIN", "TEACHER", "DISTRICT_OFFICER", "STUDENT"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Administrators are authorized to view platform audit logs."
        )
    with get_db() as conn:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [
            AuditLogResponse(
                id=r["id"],
                user_id=r["user_id"],
                action=r["action"],
                resource_type=r["resource_type"],
                resource_id=r["resource_id"],
                details_json=r["details_json"],
                created_at=r["created_at"]
            )
            for r in rows
        ]


@router.get("/system/health", status_code=status.HTTP_200_OK)
async def get_system_health(
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Administrative diagnostic endpoint: database status, latency, and counts."""
    start_t = time.time()
    with get_db() as conn:
        user_count = conn.execute("SELECT count(*) as c FROM users").fetchone()["c"]
        student_count = conn.execute("SELECT count(*) as c FROM users WHERE role = 'STUDENT'").fetchone()["c"]
        course_count = conn.execute("SELECT count(*) as c FROM courses").fetchone()["c"]
        lesson_count = conn.execute("SELECT count(*) as c FROM lessons").fetchone()["c"]
        question_count = conn.execute("SELECT count(*) as c FROM questions").fetchone()["c"]
        wal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    db_latency_ms = round((time.time() - start_t) * 1000, 2)

    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "active_roles_policy": "TWO_ROLE_SYSTEM (STUDENT, ADMIN)",
        "database": {
            "path": settings.database_path,
            "journal_mode": wal_mode,
            "latency_ms": db_latency_ms,
            "total_users": user_count,
            "students": student_count,
            "courses": course_count,
            "lessons": lesson_count,
            "quiz_questions": question_count
        },
        "ai_system": {
            "provider": settings.ai_provider,
            "model": settings.ai_model_name,
            "grounding_threshold": settings.grounding_confidence_threshold
        },
        "sms_gateway": {
            "provider": settings.sms_provider,
            "sender_id": settings.sms_sender_id
        }
    }


@router.get("/permissions-matrix")
async def get_permissions_matrix():
    """Return the strict 2-Role permissions matrix for SDC."""
    return {
        "architecture": "SDC Two-Role Security Model",
        "roles": [
            {
                "role": "STUDENT",
                "description_sindhi": "شاگرد (نصاب پڙهڻ، وڊيو ڪوئيز، اسائينمينٽس، آف لائن سنڪ ۽ اي آءِ سکيا مددگار)",
                "allowed_actions": [
                    "GET /api/lessons",
                    "GET /api/lessons/{id}",
                    "GET /api/quiz/{id}/questions (APPROVED questions only)",
                    "POST /api/quiz/attempt",
                    "POST /api/lessons/{id}/progress",
                    "POST /api/tutor/ask",
                    "POST /api/assignments/{id}/submit",
                    "POST /api/sync/queue (own records only)",
                    "GET /api/dashboards/student",
                    "POST /api/auth/forgot-password/*"
                ],
                "denied_actions": [
                    "POST /api/admin/*",
                    "POST /api/lessons/upload",
                    "POST /api/quiz/{id}/review",
                    "POST /api/admin/questions/*/approve",
                    "GET /api/admin/audit-logs",
                    "GET /api/dashboards/teacher",
                    "GET /api/dashboards/officer"
                ]
            },
            {
                "role": "ADMIN",
                "description_sindhi": "انتظاميه ۽ استاد (شاگردن جا اڪائونٽس، نصاب جو انتظام، اي آءِ سوالن جي منظوري ۽ سسٽم آڊٽ)",
                "allowed_actions": [
                    "ALL Administrative Endpoints (/api/admin/*)",
                    "POST /api/admin/lessons/{id}/generate-questions (AI Question Generator)",
                    "POST /api/admin/questions/{id}/approve (Question Gate)",
                    "POST /api/admin/students/{id}/reset-pin (Assisted Account Recovery)",
                    "GET /api/admin/audit-logs",
                    "GET /api/admin/system/health",
                    "POST /api/lessons/upload",
                    "POST /api/lessons/{id}/review",
                    "GET /api/dashboards/teacher",
                    "GET /api/dashboards/officer",
                    "GET /api/dashboards/export-anonymized"
                ],
                "denied_actions": [
                    "Public registration as ADMIN (Administrative invitation / DB provisioning only)"
                ]
            },
            {
                "role": "TEACHER",
                "description_sindhi": "استاد (ڪلاس جي پيشرفت، ڪوئيز نتيجا، اسائينمينٽس جائزو)",
                "allowed_actions": ["GET /api/dashboards/teacher", "POST /api/lessons/{id}/progress"],
                "denied_actions": ["POST /api/lessons/{id}/review", "POST /api/admin/*"]
            },
            {
                "role": "CONTENT_REVIEWER",
                "description_sindhi": "مواد جو جائزو وٺندڙ (نصاب ۽ ويڊيو جائزو)",
                "allowed_actions": ["POST /api/lessons/{id}/review", "GET /api/lessons"],
                "denied_actions": ["POST /api/admin/users"]
            },
            {
                "role": "SCHOOL_ADMIN",
                "description_sindhi": "اسڪول ايڊمن (اسڪول جي يوزرز جو انتظام)",
                "allowed_actions": ["POST /api/admin/users", "GET /api/admin/users"],
                "denied_actions": ["GET /api/admin/audit-logs"]
            },
            {
                "role": "DISTRICT_OFFICER",
                "description_sindhi": "ضلعي آفيسر (ضلعي رپورٽس ۽ جائزو)",
                "allowed_actions": ["GET /api/dashboards/officer"],
                "denied_actions": ["POST /api/admin/users"]
            },
            {
                "role": "SUPER_ADMIN",
                "description_sindhi": "سپريئر ايڊمنسٽريٽر (مڪمل سسٽم ڪنٽرول ۽ آڊٽ)",
                "allowed_actions": ["ALL"],
                "denied_actions": []
            }
        ]
    }


# ============================================================================
# Phase 3.2: Reusable Multi-Subject Textbook Management & Honest AI Diagnostics
# ============================================================================

from fastapi import File, Form, UploadFile
from src.services.textbook_ingestion_service import textbook_ingestion_service
from src.services.ai_provider import get_ai_system_status


@router.get("/ai/status")
async def get_ai_diagnostics(
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Return honest AI provider, active model, and inference health diagnostics."""
    return get_ai_system_status()


@router.get("/subjects")
async def list_subjects(
    class_level: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """List curriculum subjects and textbooks."""
    with get_db() as conn:
        query = "SELECT id, class_level, slug, title_sindhi, title_english, is_active, created_at FROM subjects WHERE 1=1"
        params = []
        if class_level:
            query += " AND class_level = ?"
            params.append(class_level)
        query += " ORDER BY class_level ASC, title_english ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/subjects")
async def create_subject(
    class_level: int = Form(...),
    slug: str = Form(...),
    title_sindhi: str = Form(...),
    title_english: str = Form(...),
    description_sindhi: Optional[str] = Form(None),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Admin creates or registers a new subject under a class level."""
    subj_id = textbook_ingestion_service.create_or_get_subject(
        class_level=class_level,
        slug=slug,
        title_sindhi=title_sindhi,
        title_english=title_english,
        description_sindhi=description_sindhi
    )
    return {"status": "ok", "subject_id": subj_id, "message": "Subject created successfully."}


@router.get("/textbooks")
async def list_textbooks(
    subject_id: Optional[str] = Query(None),
    class_level: Optional[int] = Query(None),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """List uploaded textbook editions and their processing statuses."""
    with get_db() as conn:
        query = """
            SELECT t.id, t.subject_id, s.slug as subject_slug, s.title_sindhi as subject_title,
                   t.title_sindhi, t.title_english, t.class_level, t.edition_year,
                   t.page_count, t.version, t.is_active, t.processing_status, t.created_at
            FROM textbooks t
            JOIN subjects s ON t.subject_id = s.id
            WHERE 1=1
        """
        params = []
        if subject_id:
            query += " AND t.subject_id = ?"
            params.append(subject_id)
        if class_level:
            query += " AND t.class_level = ?"
            params.append(class_level)
        query += " ORDER BY t.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/textbooks/upload", status_code=status.HTTP_201_CREATED)
async def upload_textbook_pdf(
    file: UploadFile = File(...),
    class_level: int = Form(...),
    subject_id: str = Form(...),
    title_sindhi: str = Form(...),
    title_english: str = Form(...),
    edition_year: str = Form("2024-2025"),
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Upload and ingest a real Sindhi textbook PDF."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        result = textbook_ingestion_service.ingest_textbook_pdf(
            file_bytes=content,
            filename=file.filename or "uploaded.pdf",
            class_level=class_level,
            subject_id=subject_id,
            title_sindhi=title_sindhi,
            title_english=title_english,
            edition_year=edition_year
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}")


@router.post("/textbooks/{textbook_id}/activate")
async def activate_textbook_edition(
    textbook_id: str,
    current_user: dict = Depends(require_roles(UserRole.ADMIN))
):
    """Admin activates a validated textbook edition, making it live for student AI tutoring."""
    success = textbook_ingestion_service.activate_textbook(textbook_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Textbook edition not found.")
    return {"status": "ok", "textbook_id": textbook_id, "is_active": 1, "message": "Textbook edition is now active."}
