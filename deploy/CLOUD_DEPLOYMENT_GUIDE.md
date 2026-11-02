# 🚀 SDC LMS — Cloud Deployment Guide (100% Free / Zero-Card)

This guide documents how to deploy the **Sindhi Digital Classroom (SDC) LMS** to cloud hosting without paying anything or providing a credit card.

---

## 🌟 Comparison of Zero-Card Free Cloud Hosts

| Platform | Cost / Card Req. | Specs / Resources | Persistent Disk | Custom Domain & SSL | Recommended For |
|---|---|---|---|---|---|
| **Hugging Face Spaces** | **100% Free (No Card)** | 16 GB RAM, 2 vCPUs | ✅ 50 GB free persistent storage | ✅ Free `*.hf.space` HTTPS URL | **Top Pick: Best specs & zero sleeping** |
| **Render** | **100% Free (No Card)** | 512 MB RAM, 0.5 CPU | ⚠️ Ephemeral on free tier | ✅ Free `*.onrender.com` HTTPS URL | Quick web deployment via GitHub |
| **Koyeb** | **100% Free (No Card)** | 512 MB RAM, 2 vCPUs | ⚠️ Ephemeral on free tier | ✅ Free `*.koyeb.app` HTTPS URL | Native Docker micro-services |
| **Self-Hosted VPS** | $3–$5/mo or Free Trial | Full root access | ✅ Full persistent NVMe SSD | ✅ Full custom domain & certbot | Enterprise production |

---

## Option 1: Deploy to Hugging Face Spaces (Top Pick: 16 GB RAM, No Card)

Hugging Face Spaces is the most generous zero-card host available today for AI and web apps:
- **No credit card required.**
- **16 GB RAM and 2 vCPUs free.**
- **Automatic free HTTPS domain:** `https://<your-username>-sdc-lms.hf.space`

### Steps:
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. **Space Name:** `sdc-sindhi-lms` (or any name you choose).
3. **License:** Select `mit` or `apache-2.0`.
4. **Space SDK:** Choose **`Docker`** -> **`Blank`**.
5. **Space Hardware:** Select **`CPU basic • 2 vCPU • 16GB RAM • Free`**.
6. Click **Create Space**.
7. In your local terminal, initialize a git remote or push the SDC directory to your Hugging Face Space repository:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-hf-username>/sdc-sindhi-lms
   git push hf main
   ```
8. Hugging Face Spaces will automatically build the `Dockerfile`, start the application on port `7860`, run the healthcheck, and provide your live URL immediately!

---

## Option 2: Deploy to Render (Free Web Service via GitHub)

Render allows deploying web services directly from GitHub without a credit card.

### Steps:
1. Push your repository to your GitHub account (public or private).
2. Go to [dashboard.render.com](https://dashboard.render.com) and sign in with GitHub.
3. Click **New +** -> **Web Service**.
4. Select your SDC repository.
5. Configure the settings:
   - **Name:** `sindhi-digital-classroom`
   - **Language:** `Python 3` (or choose `Docker`)
   - **Branch:** `main`
   - **Region:** Frankfurt (EU) or Oregon (US)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free` (0.5 CPU, 512 MB RAM)
6. Add Environment Variables under **Advanced**:
   - `ENVIRONMENT` = `production`
   - `SECRET_KEY` = `generate-a-random-32-char-key-here`
   - `DATABASE_PATH` = `data/sdc_platform.db`
   - `AI_PROVIDER` = `auto`
7. Click **Create Web Service**.
8. Render will build and deploy your app at:
   `https://sindhi-digital-classroom.onrender.com`

> **Note on Render Free Tier:** Render's free tier spins down after 15 minutes of inactivity and wakes up upon new traffic. The database is initialized and seeded automatically on startup.

---

## Option 3: Deploy with Docker Compose on Any VPS / Server

If you have a Linux server (Ubuntu/Debian), you can deploy with Docker Compose in two commands:

1. Clone or copy the project files to the server:
   ```bash
   scp -r sindhi-digital-classroom user@your-server-ip:/opt/sdc
   cd /opt/sdc
   ```

2. Launch using Docker Compose:
   ```bash
   docker compose up -d --build
   ```

3. Check running status and health probe:
   ```bash
   docker compose ps
   curl -i http://localhost:8000/api/health
   ```

---

## 🔒 Production Security Checklist Before Going Live

- [x] **Secret Key:** Set a cryptographically secure `SECRET_KEY` ($\ge 32$ chars) in `.env.production`.
- [x] **CORS Origins:** Configure `CORS_ALLOWED_ORIGINS` to point to your live domain (wildcards `*` are rejected in production mode).
- [x] **Health Check:** Monitor `/api/health` and `/api/status` for real-time uptime monitoring.
- [x] **Automated Backups:** Run `python scripts/backup_sqlite.py --database data/sdc_platform.db --output-dir /backup-mount` periodically via cron.

