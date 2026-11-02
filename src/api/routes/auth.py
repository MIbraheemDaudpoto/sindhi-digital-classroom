"""Authentication and Account Recovery routes for SDC.
Supports Student and Admin roles, brute-force rate limiting, and genuine
Pakistani mobile SMS OTP password recovery.
Authored under agency-api-platform-engineer and agency-application-security-engineer.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.deps import get_current_user
from src.config import settings
from src.models.schemas import (
    AuthResponse,
    ConfirmPasswordResetRequest,
    ForgotPasswordRequest,
    PasswordResetResponse,
    PublicSchoolResponse,
    ResetPinRequest,
    SendOtpRequest,
    StudentLoginRequest,
    StudentSignupRequest,
    TeacherLoginRequest,
    VerifyOtpRequest,
    VerifyPasswordResetOtpRequest,
)
from src.services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, taking proxy headers into account."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- OTP & Password Recovery Endpoints ---

@router.post("/otp/send", status_code=status.HTTP_200_OK)
async def send_otp(req: SendOtpRequest, request: Request):
    """Generate and dispatch OTP to student mobile phone."""
    ip = get_client_ip(request)
    if not auth_service.check_rate_limit(f"otp_ip:{ip}", settings.rate_limit_otp_per_minute, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="گهڻيون او ٽي پي درخواستون (Too many OTP requests from this IP. Please wait)."
        )
    try:
        return auth_service.send_otp(req.phone, req.purpose, client_ip=ip)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/otp/verify", status_code=status.HTTP_200_OK)
async def verify_otp(req: VerifyOtpRequest):
    """Verify submitted OTP code with attempt limiting."""
    valid = auth_service.verify_otp(req.phone, req.otp)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="غلط يا مدي خارج او ٽي پي ڪوڊ (Invalid or expired OTP code)."
        )
    return {"status": "ok", "verified": True, "message": "او ٽي پي جي ڪامياب تصديق (OTP verified)."}


@router.post("/forgot-password/request", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def forgot_password_request(req: ForgotPasswordRequest, request: Request):
    """Initiate password recovery via SMS OTP. Returns a generic response to prevent account enumeration."""
    ip = get_client_ip(request)
    if not auth_service.check_rate_limit(f"pwd_ip:{ip}", 5, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="گهڻيون درخواستون. مهرباني ڪري ڪجهه دير انتظار ڪريو (Rate limit exceeded)."
        )
    try:
        res = auth_service.request_password_reset(req.phone, client_ip=ip)
        return PasswordResetResponse(status="ok", message=res["message"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password/verify-otp", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def forgot_password_verify_otp(req: VerifyPasswordResetOtpRequest):
    """Verify password recovery OTP and issue single-use authorization token."""
    try:
        reset_token = auth_service.verify_password_reset_otp(req.phone, req.otp)
        return PasswordResetResponse(
            status="ok",
            message="او ٽي پي جي ڪامياب تصديق (OTP verified). هاڻي نئون پاسورڊ يا پن مقرر ڪريو.",
            reset_token=reset_token
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password/reset", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
async def forgot_password_confirm_reset(req: ConfirmPasswordResetRequest):
    """Set new password using single-use authorization token. Invalidates all active sessions."""
    try:
        auth_service.confirm_password_reset(req.reset_token, req.new_password)
        return PasswordResetResponse(
            status="ok",
            message="پاسورڊ ڪاميابيءَ سان تبديل ٿي ويو (Password reset successfully. Please log in)."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reset-pin", status_code=status.HTTP_200_OK)
async def reset_pin(req: ResetPinRequest):
    """Legacy endpoint for student PIN reset via verified Mobile OTP."""
    try:
        auth_service.reset_student_pin(req.phone, req.otp, req.new_pin)
        return {"status": "ok", "message": "پن ڪوڊ ڪاميابيءَ سان تبديل ٿي ويو (PIN reset successfully)."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Login & Registration Endpoints ---

@router.post("/login/student", response_model=AuthResponse)
async def login_student(req: StudentLoginRequest, request: Request):
    """Authenticate student via Mobile Number / Student ID or School Code + PIN."""
    ip = get_client_ip(request)
    ident_key = req.identifier or req.student_code or "unknown"
    if not auth_service.check_rate_limit(f"login_stu:{ip}:{ident_key}", settings.rate_limit_login_per_minute, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="گهڻيون ناڪام ڪوششون. مهرباني ڪري هڪ منٽ انتظار ڪريو (Too many login attempts)."
        )

    resp = auth_service.authenticate_student(req)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="غلط اسڪول ڪوڊ، شاگرد آءِ ڊي يا پن داخل ڪيو ويو آهي (Invalid credentials)."
        )
    return resp


@router.post("/login/staff", response_model=AuthResponse)
async def login_staff(req: TeacherLoginRequest, request: Request):
    """Authenticate administrative accounts (Admin / Super Admin)."""
    ip = get_client_ip(request)
    if not auth_service.check_rate_limit(f"login_staff:{ip}:{req.identifier}", settings.rate_limit_login_per_minute, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="گهڻيون ناڪام ڪوششون (Too many login attempts. Please wait)."
        )

    resp = auth_service.authenticate_teacher_or_staff(req)
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="غلط يوزر نالو يا پاسورڊ (Invalid credentials)."
        )
    return resp


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_student(req: StudentSignupRequest, request: Request):
    """Register student account. Enforces ordinary STUDENT role only."""
    ip = get_client_ip(request)
    if not auth_service.check_rate_limit(f"register_ip:{ip}", 10, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="گهڻيون رجسٽريشن درخواستون (Registration rate limit exceeded)."
        )

    try:
        return auth_service.register_student(req)
    except ValueError as e:
        err_msg = str(e)
        if "کڻجي چڪو آهي" in err_msg or "already exists" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.get("/schools", response_model=List[PublicSchoolResponse])
async def list_schools():
    """List registered schools for student registration and verification."""
    return auth_service.list_public_schools()


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retrieve active authenticated profile, role, and permission scope."""
    raw_role = current_user.get("legacy_role") or current_user.get("role")
    if raw_role == "STUDENT":
        permissions = [
            "view_curriculum",
            "take_quiz",
            "ask_tutor",
            "submit_assignment",
            "sync_offline"
        ]
    else:  # ADMIN & staff
        permissions = [
            "manage_all_users",
            "view_audit_logs",
            "review_lessons",
            "approve_questions",
            "generate_ai_questions",
            "view_district_reports",
            "system_settings",
            "manage_curriculum"
        ]

    return {
        "user_id": current_user["id"],
        "role": raw_role,
        "is_admin": current_user.get("is_admin", False),
        "pseudonymous_code": current_user["pseudonymous_code"],
        "full_name": current_user.get("full_name"),
        "school_id": current_user.get("school_id"),
        "school_name": current_user.get("school_name"),
        "district": current_user.get("district"),
        "phone": current_user.get("phone"),
        "language": current_user.get("language", "sindhi"),
        "permissions": permissions
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: dict = Depends(get_current_user)):
    """Log out active session and record audit event."""
    from datetime import datetime, timezone
    import uuid
    from src.database.session import get_db

    now_iso = datetime.now(timezone.utc).isoformat()
    auth_service.revoke_user_sessions(current_user["id"])
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
            VALUES (?, ?, 'USER_LOGOUT', 'user', ?, NULL, ?)
            """,
            (str(uuid.uuid4()), current_user["id"], current_user["id"], now_iso)
        )
    return {"status": "ok", "message": "لاگ آئوٽ ڪامياب ٿيو (Logged out successfully)."}
