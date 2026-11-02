import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('src/services/ai_provider.py', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('class LocalTransformersAIProvider')
print(text[idx:idx+3500])
