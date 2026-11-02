import urllib.request
import json
import sys

base_url = "http://127.0.0.1:8000"

endpoints = [
    ("/health", "GET", None),
    ("/api/health", "GET", None),
    ("/api/courses", "GET", None),
    ("/api/lessons", "GET", None),
    ("/api/tutor/ask", "POST", {"question": "سيٽ ڇا آهي؟", "class_level": 6, "subject": "Math"}),
    ("/api/tutor/tts?text=ٽيسٽ", "GET", None),
    ("/api/tutor/transcribe", "POST", None),
    ("/api/progress/track", "POST", {"user_id": "usr-stu-101", "lesson_id": "lesson-math-6-1", "last_position_seconds": 10.0, "is_completed": False})
]

results = []

for ep, method, payload in endpoints:
    url = base_url + ep
    req = urllib.request.Request(url, method=method)
    if payload is not None:
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(payload).encode('utf-8')
    else:
        data = None
    try:
        with urllib.request.urlopen(req, data=data, timeout=5) as resp:
            body = resp.read()
            results.append({
                "endpoint": ep,
                "method": method,
                "status": resp.status,
                "content_type": resp.headers.get("content-type"),
                "body_len": len(body),
                "snippet": body[:200].decode('utf-8', errors='replace')
            })
    except urllib.error.HTTPError as e:
        err_body = e.read()
        results.append({
            "endpoint": ep,
            "method": method,
            "status": e.code,
            "error": str(e),
            "snippet": err_body[:200].decode('utf-8', errors='replace')
        })
    except Exception as e:
        results.append({
            "endpoint": ep,
            "method": method,
            "status": "ERROR",
            "error": str(e)
        })

with open("scratch/live_endpoints_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Saved to scratch/live_endpoints_result.json successfully")
