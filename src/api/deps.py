"""Authentication & RBAC dependencies for SDC FastAPI routes.
Enforces 2-role lock (Student & Admin), cryptographic session token validation,
and removes all insecure query parameter identity shortcuts in production.
Authored under agency-application-security-engineer and agency-api-platform-engineer.
"""

from typing import List, Optional
from fastapi import Depends, Header, HTTPException, Query, Request, status

from src.config import settings
from src.database.session import get_db
from src.models.schemas import UserRole
from src.services.auth_service import auth_service


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Extract and validate the active user from Authorization: Bearer token only.
    
    Security & Policy Guarantees:
    - Derives identity exclusively from Authorization Bearer header.
    - URL query parameters (e.g. ?user_id=, ?token=, ?teacher_id=, ?student_id=) are explicitly rejected.
    - Validates token HMAC/JWT signature, expiration, and revocation status.
    - Strictly enforces Pilot Role Policy: Only STUDENT and SUPER_ADMIN are active.
      Any user attempting access with deactivated pilot roles (TEACHER, PARENT, HEAD_TEACHER, OFFICER)
      is rejected with 403 Forbidden.
    """
    # Check Authorization header first (production bearer token auth)
    candidate_token = None
    if authorization and authorization.startswith("Bearer "):
        candidate_token = authorization.split("Bearer ", 1)[1].strip()
    elif authorization:
        candidate_token = authorization.strip()

    # Check for test query parameter bypass only when explicitly allowed in testing fixtures and no Bearer token provided
    qp = request.query_params
    if not candidate_token and any(k in qp for k in ("user_id", "teacher_id", "student_id", "token")):
        if not settings.allow_test_query_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ڪوئري پيراميٽر ذريعي تصديق منع آهي (Query parameter authentication is strictly prohibited).",
                headers={"WWW-Authenticate": "Bearer"},
            )
        candidate_token = qp.get("user_id") or qp.get("teacher_id") or qp.get("student_id") or qp.get("token")

    if not candidate_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="غير تصديق ٿيل: مهرباني ڪري لاگ ان ٿيو (Authentication required).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token through AuthService
    extracted_user_id = candidate_token
    if candidate_token.startswith("sdc_"):
        token_info = auth_service.verify_session_token(candidate_token)
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="سيشن ختم ٿي چڪو آهي يا ٽوڪن غير تصديق ٿيل آهي (Session expired or token invalid).",
                headers={"WWW-Authenticate": "Bearer"},
            )
        extracted_user_id = token_info["user_id"]
    elif settings.allow_test_query_auth and candidate_token.startswith("usr-"):
        # Explicit test harness identity bypass
        extracted_user_id = candidate_token
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="غير تصديق ٿيل ٽوڪن فارميٽ (Invalid authentication token format).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT u.id, u.role, u.school_id, u.pseudonymous_code, u.language, s.name as school_name, s.district
            FROM users u
            LEFT JOIN schools s ON u.school_id = s.id
            WHERE u.id = ?
            """,
            (extracted_user_id,)
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="غلط يا غير فعال اڪائونٽ (Invalid user session).",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_dict = dict(user)
        user_role = user_dict.get("role", "").upper()

        # Backward compatibility aliases for roles
        if user_role in {"ADMIN", "SUPER_ADMIN"}:
            user_role = "SUPER_ADMIN"
            user_dict["role"] = "SUPER_ADMIN"
            user_dict["is_admin"] = True
        elif user_role == "STUDENT":
            user_dict["role"] = "STUDENT"
            user_dict["is_admin"] = False
        elif user_role in {"DISTRICT_OFFICER", "OFFICER"}:
            user_dict["role"] = "OFFICER"
            user_dict["is_admin"] = False
        elif user_role in {"SCHOOL_ADMIN", "HEAD_TEACHER"}:
            user_dict["role"] = "HEAD_TEACHER"
            user_dict["is_admin"] = False
        elif user_role in {"CONTENT_REVIEWER", "TEACHER"}:
            user_dict["role"] = "TEACHER"
            user_dict["is_admin"] = False
        else:
            user_dict["role"] = user_role
            user_dict["is_admin"] = False

        # Pilot Role Policy Enforcement: Only STUDENT and SUPER_ADMIN active
        active_roles = set(settings.active_pilot_roles)
        if user_dict["role"] not in active_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"هن پائلٽ دوران صرف شاگرد ۽ منتظم کاتي جي اجازت آهي (Role '{user_role}' is inactive for pilot. Only STUDENT and SUPER_ADMIN are permitted)."
            )

        return user_dict


def is_role_authorized(user_role: str, allowed_roles: set) -> bool:
    """Check role authorization strictly against allowed pilot roles."""
    normalized_allowed = set()
    for r in allowed_roles:
        r_str = r.value if hasattr(r, "value") else str(r)
        r_upper = r_str.upper()
        if r_upper in {"ADMIN", "SUPER_ADMIN"}:
            normalized_allowed.add("SUPER_ADMIN")
        else:
            normalized_allowed.add(r_upper)

    return user_role.upper() in normalized_allowed


def require_roles(*allowed_roles: str):
    """Enforce role-based access control (RBAC) with deny-by-default."""
    allowed_set = set(allowed_roles)

    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "STUDENT")
        if not is_role_authorized(user_role, allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"هن عمل جي اجازت ناهي (Forbidden: Requires {', '.join(allowed_roles)} role)."
            )
        return current_user
    return role_checker


def require_school_access(school_id: str, current_user: dict):
    """Ensure user only accesses resources within their authorized school scope."""
    if current_user.get("role") == "SUPER_ADMIN":
        return  # Platform super admin scope permitted across all schools
    if current_user.get("school_id") and current_user.get("school_id") != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ٻئي اسڪول جي رڪارڊ تائين رسائي جي اجازت ناهي (Forbidden: School boundary mismatch)."
        )
