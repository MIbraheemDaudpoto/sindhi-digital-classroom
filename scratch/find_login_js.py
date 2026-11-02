import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('function submitStudentLogin')
print(text[idx:idx+600])

