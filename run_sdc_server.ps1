# Sindhi Digital Classroom (SDC) PowerShell Launcher
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "      🌟 SINDHI DIGITAL CLASSROOM (SDC) - OFFLINE AI RAG SERVER 🌟       " -ForegroundColor Yellow
Write-Host "      Curriculum: STBB Class 6 General Science (8 Units / 12 Chapters)   " -ForegroundColor White
Write-Host "      Neural AI Model: Fine-Tuned SindhiLLM-1B (Native Sindhi)           " -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "."

Write-Host "[1/3] Inspecting active AI Model status..." -ForegroundColor Gray
python -c "from src.services.ai_provider import get_ai_system_status; s = get_ai_system_status(); print('>> Active AI Engine: ' + str(s['active_provider_type'])); print('>> Model Name: ' + str(s['active_model_name'])); print('>> Live Neural Inference: ' + str(s['is_live_inference']))"

Write-Host ""
Write-Host "[2/3] Starting Server..." -ForegroundColor Gray
Write-Host ">> Web Classroom UI: " -NoNewline; Write-Host "http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ">> Interactive API Docs: " -NoNewline; Write-Host "http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Red
Write-Host ""

python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
