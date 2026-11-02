import urllib.request
import json

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3) as res:
        print('Status:', res.status)
        print('Body:', res.read().decode('utf-8'))
except Exception as e:
    print('Error connecting to /api/health:', e)

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/sdc/stats', timeout=3) as res:
        print('SDC Stats Status:', res.status)
        print('Body:', res.read().decode('utf-8'))
except Exception as e:
    print('Error connecting to /api/sdc/stats:', e)

