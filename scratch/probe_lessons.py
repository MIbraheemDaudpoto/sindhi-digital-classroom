import urllib.request
import json

base = "http://127.0.0.1:8000"

with urllib.request.urlopen(f"{base}/api/lessons?class_level=6&subject=Math") as res:
    math_courses = json.loads(res.read().decode('utf-8'))

with urllib.request.urlopen(f"{base}/api/lessons?class_level=6&subject=Science") as res:
    sci_courses = json.loads(res.read().decode('utf-8'))

with open("scratch/lessons_summary.txt", "w", encoding="utf-8") as f:
    f.write(f"Math Courses: {len(math_courses)}\n")
    for c in math_courses:
        f.write(f"Course: {c['id']}, Subject: {c['subject']}, Lessons: {len(c['lessons'])}\n")
        for l in c['lessons']:
            f.write(f"  Unit {l['unit_number']} [{l['id']}]: {l['title_sindhi']} ({l['title_english']})\n")

    f.write(f"\nScience Courses: {len(sci_courses)}\n")
    for c in sci_courses:
        f.write(f"Course: {c['id']}, Subject: {c['subject']}, Lessons: {len(c['lessons'])}\n")
        for l in c['lessons']:
            f.write(f"  Unit {l['unit_number']} [{l['id']}]: {l['title_sindhi']} ({l['title_english']})\n")

print("Successfully written scratch/lessons_summary.txt")
