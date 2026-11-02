import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('src/services/ai_tutor_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print("".join(lines[500:640]))
