import requests, json
res = requests.get('http://127.0.0.1:8000/api/lessons?class_level=6')
print("Status:", res.status_code)
courses = res.json()
print("Courses count:", len(courses))
for c in courses:
    print(f"Course: {c['id']}, Subject: {c['subject']}, Lessons: {len(c.get('lessons', []))}")

