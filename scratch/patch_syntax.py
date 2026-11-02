import sys

# 1. Patch static/js/app.js
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'fetch(/api/dashboards/student?course_id=' in line:
        print(f"Found broken line in app.js at index {i}")
        lines[i] = '    const res = await fetch(`/api/dashboards/student?course_id=${encodeURIComponent(currentCourseId)}`, {\n'
        lines[i+1] = "      headers: { 'Authorization': `Bearer ${token}` }\n"
        lines[i+2] = '    });\n'
        break

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Updated static/js/app.js")

# 2. Patch static/js/tutor.js
with open('static/js/tutor.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'badgeText = 🤖' in line:
        print(f"Found broken line in tutor.js at index {i}")
        lines[i] = "      badgeText = '🤖 تصديق ٿيل اي آءِ تجزيو (Real LLM Inference)';\n"
        break

with open('static/js/tutor.js', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Updated static/js/tutor.js")

