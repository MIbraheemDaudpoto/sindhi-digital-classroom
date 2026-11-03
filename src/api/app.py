"""Sindhi Digital Classroom (SDC) FastAPI Application.
Authored under agency-backend-architect and agency-software-architect.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes.admin import router as admin_router
from src.api.routes.assignments import router as assignments_router
from src.api.routes.auth import router as auth_router
from src.api.routes.dashboards import router as dashboards_router
from src.api.routes.lessons import router as lessons_router
from src.api.routes.sync import router as sync_router
from src.api.routes.tutor import router as tutor_router
from src.api.routes.video_quiz import router as video_quiz_router
from src.api.routes.rag_course import router as rag_course_router
from src.api.routes.sdc_rag import router as sdc_rag_router
from src.config import settings
from src.database.session import get_db, init_db
from src.services.sdc_rag_db import ensure_sdc_data_seeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed baseline curriculum on startup."""
    settings.validate_production_settings()
    init_db()
    # Ensure seed curriculum is populated
    from data.seed_curriculum import seed_sdc_curriculum
    seed_sdc_curriculum()
    # Ensure SDC M5/M6 RAG canonical data (90 chunks, 201 glossary terms, 39 exercises, 113 videos) is seeded
    ensure_sdc_data_seeded()
    # Sync environment-provided Admin credentials if configured
    if settings.admin_password:
        from src.services.auth_service import hash_pin_or_password
        with get_db() as conn:
            hashed_pw = hash_pin_or_password(settings.admin_password)
            username = settings.admin_username or "superadmin"
            conn.execute(
                """
                UPDATE users 
                SET pseudonymous_code = ?, pin_hash = ?
                WHERE role IN ('ADMIN', 'SUPER_ADMIN') AND id = 'usr-super-admin-01'
                """,
                (username, hashed_pw)
            )
            conn.commit()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Offline-Capable PWA with Sindhi Voice AI and Smart Video Quiz (Sindh Textbook Board)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(sdc_rag_router)
app.include_router(auth_router)
app.include_router(lessons_router)
app.include_router(video_quiz_router)
app.include_router(rag_course_router)
app.include_router(tutor_router)
app.include_router(dashboards_router)
app.include_router(sync_router)
app.include_router(assignments_router)
app.include_router(admin_router)



# Static Files & PWA Web App Shell
static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if static_dir.exists():
    media_dir = (static_dir / "media").resolve()

    @app.get("/static/media/{filename:path}", tags=["Media"])
    async def serve_media_with_ranges(filename: str, request: Request):
        """Serve media files supporting HTTP 206 Partial Content byte ranges for video playback (FR-08)."""
        clean_filename = Path(filename).name  # Prevent directory traversal
        file_path = (media_dir / clean_filename).resolve()

        if not file_path.exists() or not str(file_path).startswith(str(media_dir)):
            if getattr(settings, "media_cdn_url", ""):
                cdn_target = f"{settings.media_cdn_url.rstrip('/')}/{clean_filename}"
                return RedirectResponse(url=cdn_target, status_code=307)
            raise HTTPException(
                status_code=404,
                detail="وڊيو فائل نه ملي (Requested media file not found)."
            )

        file_size = file_path.stat().st_size
        content_type = "video/mp4"
        if clean_filename.endswith(".webm"):
            content_type = "video/webm"
        elif clean_filename.endswith(".m3u8"):
            content_type = "application/x-mpegurl"
        elif clean_filename.endswith(".mp3"):
            content_type = "audio/mpeg"

        range_header = request.headers.get("range")
        if not range_header:
            return FileResponse(
                str(file_path),
                media_type=content_type,
                headers={"Accept-Ranges": "bytes"}
            )

        # Parse Range: "bytes=start-end"
        try:
            range_val = range_header.replace("bytes=", "").strip()
            parts = range_val.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                raise ValueError()
        except Exception:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        chunk_size = (end - start) + 1
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type
        }
        return Response(content=data, status_code=206, headers=headers)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # A. Public Landing Website Routes (Batch 7)
    @app.get("/classroom", include_in_schema=False)
    @app.get("/sdc", include_in_schema=False)
    async def serve_sdc_classroom():
        # Backward-compatible redirect: keep /classroom pointing into the integrated LMS tools shell
        return RedirectResponse(url="/app/tools", status_code=303)

    @app.get("/", include_in_schema=False)
    @app.get("/about", include_in_schema=False)
    @app.get("/curriculum", include_in_schema=False)
    @app.get("/help", include_in_schema=False)
    @app.get("/privacy", include_in_schema=False)
    @app.get("/terms", include_in_schema=False)
    async def serve_public_landing():
        landing_file = static_dir / "landing.html"
        if landing_file.exists():
            return FileResponse(str(landing_file), media_type="text/html")
        return FileResponse(str(static_dir / "index.html"), media_type="text/html")

    # B. Dedicated Authentication Routes (Batch 7)
    @app.get("/login", include_in_schema=False)
    async def serve_login():
        login_file = static_dir / "login.html"
        if login_file.exists():
            return FileResponse(str(login_file), media_type="text/html")
        return FileResponse(str(static_dir / "index.html"), media_type="text/html")

    @app.get("/admin-portal", include_in_schema=False)
    @app.get("/admin/login", include_in_schema=False)
    async def serve_admin_portal():
        return RedirectResponse(url="/login?portal=admin", status_code=303)

    @app.get("/signup", include_in_schema=False)
    async def serve_signup():
        signup_file = static_dir / "signup.html"
        if signup_file.exists():
            return FileResponse(str(signup_file), media_type="text/html")
        return FileResponse(str(static_dir / "index.html"), media_type="text/html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon():
        fav = static_dir / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav), media_type="image/x-icon")
        png = static_dir / "icon.png"
        if png.exists():
            return FileResponse(str(png), media_type="image/png")
        raise HTTPException(status_code=404, detail="Favicon not found")

    @app.get("/logout", include_in_schema=False)
    async def serve_logout():
        return RedirectResponse(url="/login?logged_out=1", status_code=303)

    @app.get("/forgot-password", include_in_schema=False)
    @app.get("/reset-password", include_in_schema=False)
    async def serve_forgot_password():
        fp_file = static_dir / "forgot_password.html"
        if fp_file.exists():
            return FileResponse(str(fp_file), media_type="text/html")
        return FileResponse(str(static_dir / "login.html"), media_type="text/html")

    @app.get("/unauthorized", include_in_schema=False)
    async def serve_unauthorized():
        unauth_file = static_dir / "unauthorized.html"
        if unauth_file.exists():
            return FileResponse(str(unauth_file), media_type="text/html")
        return FileResponse(str(static_dir / "login.html"), media_type="text/html")

    # C. Protected LMS Application Routes (Batch 7)
    @app.get("/app", include_in_schema=False)
    @app.get("/app/{subpath:path}", include_in_schema=False)
    async def serve_lms_app(subpath: str = ""):
        app_file = static_dir / "app.html"
        if app_file.exists():
            return FileResponse(str(app_file), media_type="text/html")
        return FileResponse(str(static_dir / "index.html"), media_type="text/html")


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Verify platform health and connectivity."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "roles_policy": "TWO_ROLE_LOCK (STUDENT, ADMIN)",
        "language_support": ["sindhi", "english"],
        "curriculum": "Sindh Textbook Board (Class 6-10)"
    }


@app.get("/api/ready", tags=["Health"])
async def readiness_check():
    """Verify system readiness: database connectivity, WAL mode, storage."""
    import time
    start = time.time()
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
            wal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        db_latency = round((time.time() - start) * 1000, 2)
        return {
            "status": "ready",
            "database": {"connected": True, "journal_mode": wal, "latency_ms": db_latency},
            "media_storage": {"ready": static_dir.exists()},
            "sms_gateway": {"provider": settings.sms_provider}
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@app.get("/api/status", tags=["Health & Architecture"])
async def comprehensive_system_status():
    """Comprehensive system telemetry and Free-for-Dev Blueprint readiness."""
    import platform, json, urllib.request
    from src.services.ai_provider import get_ai_system_status

    try:
        import psutil
        vm = psutil.virtual_memory()
        cpu_cores = psutil.cpu_count(logical=True)
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_available_gb = round(vm.available / (1024**3), 2)
        ram_used_percent = vm.percent
    except Exception:
        cpu_cores = 1
        ram_total_gb = 0.51
        ram_available_gb = 0.51
        ram_used_percent = 45.0

    ai_status = get_ai_system_status()
    
    # Check Ollama local service
    ollama_online = False
    ollama_models = []
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=0.5) as r:
            if r.status == 200:
                ollama_online = True
                data = json.loads(r.read().decode())
                ollama_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        pass

    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "system_resources": {
            "os": platform.platform(),
            "cpu_cores": cpu_cores,
            "ram_total_gb": ram_total_gb,
            "ram_available_gb": ram_available_gb,
            "ram_used_percent": ram_used_percent
        },
        "ai_engine": {
            **ai_status,
            "ollama_service_online": ollama_online,
            "ollama_available_models": ollama_models
        },
        "free_for_dev_blueprint": {
            "compute_tier": "Oracle Cloud 24GB ARM Ready" if settings.environment == "production" else "Local / Pi 5 Edge",
            "media_cdn": {
                "configured": bool(settings.media_cdn_url),
                "cdn_url": settings.media_cdn_url or "Local disk fallback (/static/media/)",
                "provider": "Backblaze B2 + Cloudflare CDN (0$ Egress)" if settings.media_cdn_url else "Local Storage"
            },
            "edge_database": {
                "engine": "SQLite WAL" if not settings.database_url else ("Turso libSQL" if "libsql" in settings.database_url else "PostgreSQL"),
                "embedded_replicas_ready": True
            },
            "tunneling": {
                "compatible": "Cloudflare Zero Trust (cloudflared)",
                "allows_remote_access_without_public_ip": True
            },
            "monitoring": {
                "better_stack_configured": bool(settings.better_stack_heartbeat_url),
                "sentry_configured": bool(settings.sentry_dsn)
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host=settings.host, port=settings.port, reload=settings.debug)
