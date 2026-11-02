import urllib.request
import urllib.parse
import json

q = urllib.parse.quote('سيٽ')
url = f'http://127.0.0.1:8000/api/sdc/search?q={q}'
with urllib.request.urlopen(url, timeout=3) as res:
    data = json.loads(res.read().decode('utf-8'))
    print('Chunk 0 keys:', list(data['chunks'][0].keys()))
    print('Chunk 0 sample:', {k: data['chunks'][0][k] for k in ['chunk_id', 'chapter_id', 'pdf_page_start']})
