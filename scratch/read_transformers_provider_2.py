import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print("".join(lines[550:660]))
