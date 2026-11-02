import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/player.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('checkQuizPopups')
print("--- checkQuizPopups ---")
print(text[idx:idx+1200])

idx2 = text.find('triggerQuizPause')
print("\n--- triggerQuizPause ---")
print(text[idx2:idx2+1200])
