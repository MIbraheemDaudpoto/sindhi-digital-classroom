import urllib.request
import urllib.parse
import json

base_url = "http://127.0.0.1:8000"

def get(path):
    url = base_url + path
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return {"status": r.status, "data": json.loads(r.read().decode('utf-8'))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode('utf-8', errors='replace')}
    except Exception as e:
        return {"status": "ERR", "error": str(e)}

def post(path, body):
    url = base_url + path
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return {"status": r.status, "data": json.loads(r.read().decode('utf-8'))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode('utf-8', errors='replace')}
    except Exception as e:
        return {"status": "ERR", "error": str(e)}

out = {}
# 1. Test search with sindhi query
q = urllib.parse.quote("سيٽ")
out["search"] = get(f"/api/sdc/search?q={q}")

# 2. Test SDC Ask
out["sdc_ask"] = post("/api/sdc/ask", {"question": "سيٽ ڇا آهي؟"})

# 3. Test stats
out["sdc_stats"] = get("/api/sdc/stats")

# 4. Test dashboards without auth
out["dashboard_student"] = get("/api/dashboards/student")

with open("scratch/live_sdc_test.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print("Saved to scratch/live_sdc_test.json")

