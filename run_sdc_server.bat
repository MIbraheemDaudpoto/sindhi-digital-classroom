@echo off
chcp 65001 >nul
title Sindhi Digital Classroom (SDC) - Offline AI Server
echo =========================================================================
echo       🌟 SINDHI DIGITAL CLASSROOM (SDC) - OFFLINE AI RAG SERVER 🌟
echo       Curriculum: STBB Class 6 General Science (8 Units / 12 Chapters)
echo       Neural AI Model: Fine-Tuned SindhiLLM (safetensors / Transformers)
echo =========================================================================
echo.

set PYTHONPATH=.

echo [1/3] Checking environment & fine-tuned model...
python -c "from src.services.ai_provider import get_ai_system_status; s = get_ai_system_status(); print('>> Active AI Engine:', s['active_provider_type']); print('>> Model Name:', s['active_model_name']); print('>> Live Neural Inference:', s['is_live_inference'])"
echo.

echo [2/3] Starting FastAPI Uvicorn Server on http://127.0.0.1:8000 ...
echo >> Web Classroom UI: http://127.0.0.1:8000
echo >> Interactive API Docs: http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C anytime to stop the server.
echo.

python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
pause
