import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('login-student-pin')
print(text[idx:idx+500])

