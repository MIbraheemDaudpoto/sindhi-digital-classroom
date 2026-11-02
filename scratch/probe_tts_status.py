import urllib.request
import json

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/tutor/tts/status', timeout=3) as res:
        print('Status:', res.status)
        print('Body:', res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('HTTPError:', e.code, e.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)

