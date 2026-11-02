import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request, json

payload = {
    "model": "llama3.2:1b",
    "messages": [
        {"role": "system", "content": "You are a Sindhi teacher. Answer in Sindhi."},
        {"role": "user", "content": "خالي سيٽ ڇا کي چئجي ٿو؟"}
    ],
    "max_tokens": 100
}

t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:11434/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode())
        t1 = time.time()
        print(f"Ollama responded in {t1 - t0:.2f}s!")
        print("Response:", res["choices"][0]["message"]["content"])
except Exception as e:
    print("Ollama error:", e)
