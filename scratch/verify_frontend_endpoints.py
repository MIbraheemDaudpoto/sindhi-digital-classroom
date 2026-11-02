import urllib.request
import json

base_url = "http://127.0.0.1:8000"

endpoints = [
    ("/", 200),
    ("/app", 200),
    ("/classroom", 200),
    ("/api/health", 200),
    ("/api/sdc/stats", 200),
    ("/static/js/app.js", 200),
    ("/static/js/player.js", 200),
    ("/static/js/tutor.js", 200),
    ("/static/css/sdc_style.css", 200),
    ("/static/images/sdc-logo.svg", 200),
    ("/static/media/demo_lesson.mp4", 200),
    ("/api/lessons?class_level=6", 200),
    ("/api/lessons?class_level=6&subject=Math", 200),
    ("/api/lessons?class_level=6&subject=Science", 200),
]

all_passed = True
for path, expected_status in endpoints:
    url = base_url + path
    try:
        req = urllib.request.Request(url, method="HEAD" if path.endswith(".mp4") else "GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            status = res.status
            if status == expected_status:
                print(f"[OK] {path} -> {status}")
            else:
                print(f"[FAIL] {path} -> {status} (expected {expected_status})")
                all_passed = False
    except Exception as e:
        print(f"[ERROR] {path} -> {e}")
        all_passed = False

if all_passed:
    print("\nAll frontend routes and static assets verified successfully!")
else:
    print("\nSome endpoints failed.")

