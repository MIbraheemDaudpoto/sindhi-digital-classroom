import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, unit_number, title_sindhi, title_english FROM lessons WHERE id LIKE '%math%' ORDER BY unit_number")
math_lessons = c.fetchall()
print(f"Total Math Lessons: {len(math_lessons)}")
for l in math_lessons:
    c.execute("SELECT youtube_id, title, is_embeddable, embed_url FROM youtube_videos WHERE lesson_id = ?", (l['id'],))
    y = c.fetchone()
    yt_info = f"{y['youtube_id']} ({y['title']})" if y else "MISSING"
    print(f"{l['id']} (Unit {l['unit_number']}): {l['title_sindhi']} -> YT: {yt_info}")

