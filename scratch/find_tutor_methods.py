import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('src/services/ai_tutor_service.py', 'r', encoding='utf-8') as f:
    text = f.read()
for i, line in enumerate(text.splitlines()):
    if 'def ' in line:
        print(f"{i+1}: {line}")
