import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/player.js', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('setupYouTubePlayer')
print(text[idx+1500:idx+3500])
