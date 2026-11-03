"""Authentication & Session Service for SDC.
Supports Student and Admin roles, cryptographic HMAC session tokens,
legitimate Pakistani SMS OTP password recovery, and brute-force rate limiting.
Authored under agency-application-security-engineer and agency-backend-architect.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Dict, List, Optional, Tuple
import uuid

from src.config import settings
from src.database.session import get_db
from src.models.schemas import AuthResponse, StudentLoginRequest, StudentSignupRequest, TeacherLoginRequest, UserRole
from src.services.sms_service import get_sms_provider, normalize_pakistan_phone, SMSProviderError

logger = logging.getLogger("sdc.auth")


def hash_pin_or_password(secret: str, salt: Optional[str] = None) -> str:
    """Hash secret using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${hashed.hex()}"


def verify_pin_or_password(secret: str, stored_hash: str) -> bool:
    """Verify secret against stored salt$hash string using constant-time comparison."""
    try:
        salt, expected_hash = stored_hash.split("$", 1)
        computed = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(computed.hex(), expected_hash)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Authentication, session management, and password recovery service."""

    def __init__(self):
        # In-memory stores for ephemeral state
        # _otp_cache: normalized_phone -> {otp_hash, salt, expires_at, attempts_left, cooldown_until, purpose, user_id}
        self._otp_cache: Dict[str, dict] = {}
        # _rate_limits: key -> list of timestamp epochs
        self._rate_limits: Dict[str, List[float]] = {}
        # _revoked_users: user_id -> revocation_timestamp
        self._revoked_users: Dict[str, float] = {}

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Sliding-window rate limiter. Returns True if request is allowed, False if exceeded."""
        if not settings.rate_limit_enabled:
            return True
        now = time.time()
        timestamps = self._rate_limits.get(key, [])
        # Prune expired timestamps
        cutoff = now - window_seconds
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_requests:
            self._rate_limits[key] = timestamps
            return False
        timestamps.append(now)
        self._rate_limits[key] = timestamps
        return True

    def create_session_token(self, user_id: str, role: str) -> str:
        """Create a cryptographically signed session token with embedded timestamp and HMAC signature."""
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        nonce = secrets.token_hex(4)
        role_slug = "admin" if role.upper() in {"ADMIN", "SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "OFFICER"} else "stu"
        payload = f"{role_slug}:{user_id}:{now_epoch}:{nonce}"
        sig = hmac.new(settings.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        return f"sdc_{role_slug}_{user_id}_{now_epoch}_{nonce}_{sig}"

    def verify_session_token(self, token: str) -> Optional[dict]:
        """Verify token signature, freshness, and account status."""
        if not token or not token.startswith("sdc_"):
            return None

        parts = token.split("_")
        # Format: sdc_{role_slug}_{user_id}_{epoch}_{nonce}_{sig} or legacy sdc_{role}_{user_id}_{epoch}_{nonce}
        extracted_user_id = None
        token_epoch = None

        if len(parts) >= 6:
            role_slug, extracted_user_id, epoch_str, nonce, sig = parts[1], parts[2], parts[3], parts[4], parts[5]
            try:
                token_epoch = int(epoch_str)
                # Verify HMAC signature
                expected_payload = f"{role_slug}:{extracted_user_id}:{token_epoch}:{nonce}"
                expected_sig = hmac.new(settings.secret_key.encode("utf-8"), expected_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
                if not hmac.compare_digest(sig, expected_sig):
                    return None
            except ValueError:
                return None
        elif len(parts) >= 3:
            # Legacy unsigned tokens are accepted only in isolated test fixtures.
            # They are forgeable and must never authenticate a normal app session.
            if settings.environment.lower() != "test":
                return None
            usr_candidate = next((p for p in parts if p.startswith("usr-")), None)
            extracted_user_id = usr_candidate or parts[2]
            for p in parts[2:]:
                if p.isdigit() and len(p) >= 9:
                    try:
                        token_epoch = int(p)
                    except ValueError:
                        pass
                    break

        if not extracted_user_id:
            return None

        # Check expiration (24 hours default)
        if token_epoch:
            now_epoch = int(datetime.now(timezone.utc).timestamp())
            if now_epoch - token_epoch > settings.session_expiry_seconds:
                return None

        # Check if user sessions were revoked in memory or database (e.g. after logout or password reset)
        cutoff_epoch = self._revoked_users.get(extracted_user_id)
        if cutoff_epoch is None:
            try:
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT revocation_cutoff_epoch FROM users WHERE id = ?",
                        (extracted_user_id,)
                    ).fetchone()
                    if row and row["revocation_cutoff_epoch"]:
                        cutoff_epoch = float(row["revocation_cutoff_epoch"])
                        self._revoked_users[extracted_user_id] = cutoff_epoch
            except Exception:
                pass

        if cutoff_epoch is not None and token_epoch:
            if token_epoch < cutoff_epoch:
                return None

        return {"user_id": extracted_user_id}

    def revoke_user_sessions(self, user_id: str) -> None:
        """Invalidate all tokens issued for a user prior to this timestamp, persisted to DB."""
        now_epoch = time.time()
        self._revoked_users[user_id] = now_epoch
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET revocation_cutoff_epoch = ? WHERE id = ?",
                    (now_epoch, user_id)
                )
        except Exception as e:
            logger.warning(f"Could not persist session revocation to DB: {e}")

    # --- OTP & Password Recovery Workflow ---

    def send_otp(self, phone: str, purpose: str = "REGISTRATION", client_ip: str = "unknown") -> dict:
        """Generate and dispatch a cryptographically secure OTP via real SMS gateway."""
        try:
            clean_phone = normalize_pakistan_phone(phone)
        except ValueError as e:
            raise ValueError(str(e))

        # Rate limit by phone number and IP
        if not self.check_rate_limit(f"otp:{clean_phone}", settings.rate_limit_otp_per_minute, 60):
            raise ValueError("گهڻيون او ٽي پي درخواستون. مهرباني ڪري هڪ منٽ انتظار ڪريو (Too many OTP requests. Please wait 1 minute).")

        # Check cooldown (exempt in test environment)
        cached = self._otp_cache.get(clean_phone)
        now = time.time()
        if cached and now < cached.get("cooldown_until", 0) and settings.environment != "test":
            wait_seconds = int(cached["cooldown_until"] - now)
            raise ValueError(f"مهرباني ڪري {wait_seconds} سيڪنڊن کان پوءِ نئون ڪوڊ گهرو (Please wait {wait_seconds}s before requesting a new OTP).")

        # Generate cryptographically secure numeric OTP (6 digits)
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(8)
        otp_hash = hashlib.sha256(f"{salt}:{otp_code}".encode("utf-8")).hexdigest()

        self._otp_cache[clean_phone] = {
            "otp_hash": otp_hash,
            "salt": salt,
            "purpose": purpose,
            "expires_at": now + settings.otp_expiry_seconds,
            "cooldown_until": now + settings.otp_resend_cooldown_seconds,
            "attempts_left": settings.otp_max_attempts,
            "verified": False,
        }

        # Dispatch via configured SMS Provider
        sms_provider = get_sms_provider()
        sms_text = f"سنڌي ڊجيٽل ڪلاس روم: اوهان جو تصديقي او ٽي پي ڪوڊ {otp_code} آهي. هي ڪوڊ 5 منٽن تائين ڪارآمد آهي."
        try:
            sms_provider.send_sms(clean_phone, sms_text)
        except SMSProviderError as e:
            # Clean up cache on delivery failure to prevent unsendable lock
            del self._otp_cache[clean_phone]
            raise ValueError(str(e))

        # Format response with honest delivery reporting
        if settings.sms_provider == "mock":
            resp = {
                "status": "ok",
                "message": "او ٽي پي تيار ڪيو ويو آهي (Development Mock Mode: ايس ايم ايس موڪليو ويو تصور ڪيو ويو آهي).",
                "phone": clean_phone,
                "provider": "mock",
            }
            if settings.environment in {"development", "test"}:
                resp["otp_hint"] = otp_code
        else:
            resp = {
                "status": "ok",
                "message": "او ٽي پي ڪاميابيءَ سان اوهان جي موبائل نمبر تي موڪليو ويو آهي (OTP sent successfully via SMS gateway).",
                "phone": clean_phone,
                "provider": settings.sms_provider,
            }
        return resp

    def verify_otp(self, phone: str, otp: str) -> bool:
        """Verify OTP with attempt limits, expiry validation, and constant-time check."""
        try:
            clean_phone = normalize_pakistan_phone(phone)
        except ValueError:
            clean_phone = phone.strip().replace("-", "").replace(" ", "")

        cached = self._otp_cache.get(clean_phone)
        if not cached:
            return False

        now = time.time()
        if now > cached["expires_at"]:
            del self._otp_cache[clean_phone]
            return False

        if cached["attempts_left"] <= 0:
            del self._otp_cache[clean_phone]
            return False

        # Compute hash and compare in constant time
        salt = cached["salt"]
        computed_hash = hashlib.sha256(f"{salt}:{otp.strip()}".encode("utf-8")).hexdigest()
        if hmac.compare_digest(computed_hash, cached["otp_hash"]):
            cached["verified"] = True
            return True
        else:
            cached["attempts_left"] -= 1
            if cached["attempts_left"] <= 0:
                del self._otp_cache[clean_phone]
            return False

    def request_password_reset(self, phone: str, client_ip: str = "unknown") -> dict:
        """Initiate password recovery. Returns generic message to prevent account enumeration."""
        try:
            clean_phone = normalize_pakistan_phone(phone)
        except ValueError as e:
            raise ValueError(str(e))

        # Rate limit
        if not self.check_rate_limit(f"pwd_reset:{clean_phone}", 3, 60):
            raise ValueError("گهڻيون درخواستون. مهرباني ڪري ڪجهه دير انتظار ڪريو (Too many reset requests).")

        # Check if student account exists
        with get_db() as conn:
            user = conn.execute(
                "SELECT id, pseudonymous_code FROM users WHERE phone = ? AND role = 'STUDENT'",
                (clean_phone,)
            ).fetchone()

        if user:
            # Generate and dispatch OTP
            return self.send_otp(clean_phone, purpose="PASSWORD_RESET", client_ip=client_ip)
        else:
            # Generic response to prevent account enumeration
            return {
                "status": "ok",
                "message": "جيڪڏهن هي موبائل نمبر رجسٽر ٿيل آهي، ته او ٽي پي موڪليو ويو آهي (If this number is registered, an OTP has been sent).",
                "phone": clean_phone
            }

    def verify_password_reset_otp(self, phone: str, otp: str) -> str:
        """Verify OTP for password reset and issue a single-use authorization reset token."""
        try:
            clean_phone = normalize_pakistan_phone(phone)
        except ValueError as e:
            raise ValueError(str(e))

        if not self.verify_otp(clean_phone, otp):
            raise ValueError("او ٽي پي ڪوڊ غلط آهي يا ختم ٿي ويو آهي (Invalid or expired OTP).")

        # Invalidate the OTP now that it's verified
        if clean_phone in self._otp_cache:
            del self._otp_cache[clean_phone]

        # Find student
        with get_db() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE phone = ? AND role = 'STUDENT'",
                (clean_phone,)
            ).fetchone()
            if not user:
                raise ValueError("شاگرد اڪائونٽ نه مليو (Student account not found).")

            user_id = user["id"]
            reset_token = secrets.token_urlsafe(32)
            token_hash = hash_token(reset_token)
            expires_at = time.time() + settings.password_reset_token_expiry_seconds
            now_iso = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (str(uuid.uuid4()), user_id, token_hash, expires_at, now_iso)
            )

        return reset_token

    def confirm_password_reset(self, reset_token: str, new_password: str) -> bool:
        """Complete password reset using single-use authorization token."""
        token_clean = reset_token.strip()
        if len(token_clean) < 16:
            raise ValueError("غلط ريسيٽ ٽوڪن (Invalid reset token).")

        if len(new_password) < 4:
            raise ValueError("پاسورڊ يا پن گهٽ ۾ گهٽ 4 عددن جو هجڻ لازمي آهي (Password/PIN must be at least 4 characters).")

        token_hash = hash_token(token_clean)
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            row = conn.execute(
                "SELECT id, user_id, expires_at, used FROM password_reset_tokens WHERE token_hash = ?",
                (token_hash,)
            ).fetchone()

            if not row:
                raise ValueError("غلط يا مدي خارج ريسيٽ ٽوڪن (Invalid or expired reset token).")
            if row["used"] == 1:
                raise ValueError("هي ريسيٽ ٽوڪن اڳ ۾ ئي استعمال ٿي چڪو آهي (This reset token has already been used).")
            if now > row["expires_at"]:
                raise ValueError("ريسيٽ ٽوڪن جو مدو ختم ٿي ويو آهي (Reset token expired).")

            user_id = row["user_id"]
            new_hash = hash_pin_or_password(new_password)

            # Invalidate the token (single use)
            conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (row["id"],))

            # Update student credentials
            conn.execute("UPDATE users SET pin_hash = ? WHERE id = ?", (new_hash, user_id))

            # Revoke all active sessions
            self.revoke_user_sessions(user_id)

            # Audit event
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'STUDENT_PASSWORD_RESET_SUCCESS', 'user', ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, user_id, '{"method": "SMS_OTP"}', now_iso)
            )

        return True

    def reset_student_pin(self, phone: str, otp: str, new_pin: str) -> bool:
        """Reset student PIN (legacy wrapper ensuring atomic OTP verification and update)."""
        clean_phone = phone.strip().replace("-", "").replace(" ", "")
        if not self.verify_otp(clean_phone, otp):
            raise ValueError("او ٽي پي ڪوڊ غلط آهي يا ختم ٿي ويو آهي (Invalid or expired OTP).")
        if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
            raise ValueError("نئون پن ڪوڊ 4 کان 6 عددن جو هجڻ لازمي آهي (PIN must be 4 to 6 numeric digits).")

        new_hash = hash_pin_or_password(new_pin)
        normalized_phone = None
        try:
            normalized_phone = normalize_pakistan_phone(phone)
        except ValueError:
            pass

        with get_db() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE phone = ? OR phone = ? OR pseudonymous_code = ?",
                (normalized_phone or clean_phone, clean_phone, phone.strip())
            ).fetchone()
            if not user:
                raise ValueError("هن موبائل نمبر سان ڪوبه شاگرد اڪائونٽ نه مليو (No student account found with this phone number).")
            conn.execute("UPDATE users SET pin_hash = ? WHERE id = ?", (new_hash, user["id"]))
            self.revoke_user_sessions(user["id"])
            return True

    # --- Student & Staff Login ---

    def authenticate_student(self, req: StudentLoginRequest) -> Optional[AuthResponse]:
        """Authenticate student via Mobile Number / Unique Student ID OR School Code + PIN."""
        with get_db() as conn:
            user = None

            # Path A: Authenticate via Mobile Phone or Student ID
            if req.identifier:
                ident = req.identifier.strip()
                clean_phone = ident.replace("-", "").replace(" ", "")
                normalized_phone = None
                try:
                    normalized_phone = normalize_pakistan_phone(ident)
                except ValueError:
                    pass

                user = conn.execute(
                    """
                    SELECT u.*, s.name as school_name, s.code as school_code, s.district
                    FROM users u
                    LEFT JOIN schools s ON u.school_id = s.id
                    WHERE (u.phone = ? OR u.phone = ? OR u.pseudonymous_code = ? OR u.full_name = ?) AND u.role = 'STUDENT'
                    """,
                    (normalized_phone or clean_phone, clean_phone, ident, ident)
                ).fetchone()

            # Path B: Authenticate via legacy School Code + Student Code
            elif req.school_code and req.student_code:
                school = conn.execute("SELECT id, name, district FROM schools WHERE code = ?", (req.school_code.strip(),)).fetchone()
                if not school:
                    return None
                user = conn.execute(
                    """
                    SELECT u.*, s.name as school_name, s.code as school_code, s.district
                    FROM users u
                    LEFT JOIN schools s ON u.school_id = s.id
                    WHERE u.school_id = ? AND u.pseudonymous_code = ? AND u.role = 'STUDENT'
                    """,
                    (school["id"], req.student_code.strip())
                ).fetchone()

            # Path C: Fallback to student_code directly if provided alone
            elif req.student_code:
                ident = req.student_code.strip()
                clean_phone = ident.replace("-", "").replace(" ", "")
                normalized_phone = None
                try:
                    normalized_phone = normalize_pakistan_phone(ident)
                except ValueError:
                    pass

                user = conn.execute(
                    """
                    SELECT u.*, s.name as school_name, s.code as school_code, s.district
                    FROM users u
                    LEFT JOIN schools s ON u.school_id = s.id
                    WHERE (u.pseudonymous_code = ? OR u.full_name = ? OR u.phone = ? OR u.phone = ?) AND u.role = 'STUDENT'
                    """,
                    (ident, ident, normalized_phone or clean_phone, clean_phone)
                ).fetchone()

            if not user or not verify_pin_or_password(req.pin, user["pin_hash"]):
                return None

            token = self.create_session_token(user["id"], "STUDENT")
            return AuthResponse(
                user_id=user["id"],
                role=UserRole.STUDENT,
                pseudonymous_code=user["pseudonymous_code"],
                full_name=user["full_name"] if "full_name" in user.keys() else None,
                school_id=user["school_id"],
                school_name=user["school_name"] or (user["school_name_custom"] if "school_name_custom" in user.keys() else None),
                city=user["district"] or (user["city"] if "city" in user.keys() else None),
                phone=user["phone"],
                language=user["language"] or "sindhi",
                token=token
            )

    def authenticate_teacher_or_staff(self, req: TeacherLoginRequest) -> Optional[AuthResponse]:
        """Authenticate administrative staff. In 2-role system, roles map to ADMIN."""
        with get_db() as conn:
            ident = req.identifier.strip()
            clean_phone = ident.replace("-", "").replace(" ", "")
            normalized_phone = None
            try:
                normalized_phone = normalize_pakistan_phone(ident)
            except ValueError:
                pass

            user = conn.execute(
                """
                SELECT u.*, s.name as school_name 
                FROM users u 
                LEFT JOIN schools s ON u.school_id = s.id
                WHERE (u.email = ? OR u.phone = ? OR u.phone = ? OR u.pseudonymous_code = ?)
                  AND u.role IN ('ADMIN', 'SUPER_ADMIN')
                """,
                (ident, normalized_phone or clean_phone, clean_phone, ident)
            ).fetchone()

            if not user or not verify_pin_or_password(req.password, user["pin_hash"]):
                return None

            # Only explicitly provisioned Admin accounts may use this login path.
            active_role = UserRole.ADMIN

            token = self.create_session_token(user["id"], active_role.value)
            return AuthResponse(
                user_id=user["id"],
                role=active_role,
                pseudonymous_code=user["pseudonymous_code"],
                full_name=user["full_name"] if "full_name" in user.keys() else None,
                school_id=user["school_id"],
                school_name=user["school_name"],
                language=user["language"] or "sindhi",
                token=token
            )

    def register_student(self, req: StudentSignupRequest) -> AuthResponse:
        """Register a student using a single-use administrator-issued invitation."""
        if req.role and req.role.upper() != "STUDENT":
            raise ValueError("عوامي رجسٽريشن رڳو شاگردن لاءِ آهي. انتظامي اڪائونٽس بذريعه دعوت جاري ٿيندا آهن (Public registration is restricted to students only).")

        if not req.pin.isdigit() or len(req.pin) < 4 or len(req.pin) > 6:
            raise ValueError("پن ڪوڊ 4 کان 6 عددن جو هجڻ لازمي آهي (PIN must be 4 to 6 numeric digits).")

        now_iso = datetime.now(timezone.utc).isoformat()
        invite_hash = hashlib.sha256(req.invite_code.strip().upper().encode("utf-8")).hexdigest()
        with get_db() as conn:
            invite = conn.execute(
                "SELECT school_id, expires_at, used_by FROM student_invites WHERE code_hash = ?",
                (invite_hash,)
            ).fetchone()
            if not invite or invite["used_by"] or invite["expires_at"] <= now_iso:
                raise ValueError("داخلا ڪوڊ غلط، استعمال ٿيل يا ختم ٿيل آهي (Invite code is invalid, used, or expired).")

            school_id = invite["school_id"]
            if req.school_code and req.school_code.strip():
                school = conn.execute("SELECT id FROM schools WHERE code = ?", (req.school_code.strip(),)).fetchone()
                if not school or school["id"] != school_id:
                    raise ValueError("اسڪول داخلا ڪوڊ سان نٿو ملي (School does not match this invite).")
            school = conn.execute("SELECT id, name, district FROM schools WHERE id = ?", (school_id,)).fetchone() if school_id else None
            school_name = school["name"] if school else None
            district_name = (req.city or (school["district"] if school else "سنڌ (Sindh)")).strip()

            # Generate unique student code
            if req.pseudonymous_code and req.pseudonymous_code.strip():
                clean_code = req.pseudonymous_code.strip()
                existing = conn.execute("SELECT id FROM users WHERE pseudonymous_code = ?", (clean_code,)).fetchone()
                if existing:
                    raise ValueError("هي شاگرد آءِ ڊي يا ڪوڊ اڳ ۾ ئي کڻجي چڪو آهي (Pseudonymous student code already exists).")
            else:
                clean_code = f"STU-{secrets.randbelow(90000) + 10000}"
                for _ in range(50):
                    existing = conn.execute("SELECT id FROM users WHERE pseudonymous_code = ?", (clean_code,)).fetchone()
                    if not existing:
                        break
                    clean_code = f"STU-{secrets.randbelow(90000) + 10000}"

            new_id = f"usr-stu-{uuid.uuid4().hex[:8]}"
            pin_hash = hash_pin_or_password(req.pin)
            student_full_name = (req.full_name or "").strip() or None
            custom_school_name = (req.school_name or "").strip() or None
            city_val = (req.city or "").strip() or district_name

            conn.execute(
                """
                INSERT INTO users (id, role, school_id, pseudonymous_code, full_name, school_name_custom, city, pin_hash, phone, language, created_at)
                VALUES (?, 'STUDENT', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id, school_id, clean_code, student_full_name, custom_school_name, city_val, pin_hash, None, req.language or "sindhi", now_iso)
            )

            consumed = conn.execute(
                "UPDATE student_invites SET used_by = ?, used_at = ? WHERE code_hash = ? AND used_by IS NULL AND expires_at > ?",
                (new_id, now_iso, invite_hash, now_iso)
            )
            if consumed.rowcount != 1:
                raise ValueError("داخلا ڪوڊ اڳ ۾ استعمال ٿي چڪو آهي (Invite code has already been used).")

            token = self.create_session_token(new_id, "STUDENT")
            return AuthResponse(
                user_id=new_id,
                role=UserRole.STUDENT,
                pseudonymous_code=clean_code,
                full_name=student_full_name,
                school_id=school_id,
                school_name=school_name,
                city=city_val,
                phone=None,
                language=req.language or "sindhi",
                token=token
            )

    def list_public_schools(self) -> list:
        """List verified schools available for enrollment."""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name, district, code FROM schools ORDER BY name ASC").fetchall()
            return [dict(r) for r in rows]


auth_service = AuthService()
