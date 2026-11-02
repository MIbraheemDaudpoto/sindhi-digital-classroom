import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('src/services/ai_tutor_service.py', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('def ask_question')
print(text[idx:idx+3500])
