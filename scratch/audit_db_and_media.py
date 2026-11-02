import sqlite3, hashlib, os
from pathlib import Path

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row

print("=== 1. LESSONS IN DATABASE ===")
lessons = conn.execute('SELECT id, subject_id, class_level, unit_number, title_sindhi, title_english, duration_seconds, status FROM lessons').fetchall()
print(f'Total Lessons: {len(lessons)}')
for l in lessons:
    print(f"  [{l['id']}] sub={l['subject_id']} cl={l['class_level']} u={l['unit_number']} status={l['status']} dur={l['duration_seconds']}s | {l['title_english']}")

print("\n=== 2. VIDEOS TABLE ===")
videos = conn.execute('SELECT v.id, v.lesson_id, v.youtube_id, v.title, v.local_file_path, v.duration_seconds, v.curriculum_status, v.is_embeddable FROM videos v').fetchall()
print(f'Total Videos: {len(videos)}')
for v in videos:
    print(f"  [{v['lesson_id']}] yt={v['youtube_id']} path={v['local_file_path']} dur={v['duration_seconds']} embed={v['is_embeddable']} | {v['title']}")

print("\n=== 3. MEDIA FILES AUDIT ===")
media_dir = Path("static/media")
if media_dir.exists():
    for f in media_dir.glob("*.mp4"):
        content = f.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        print(f"  {f.name}: size={len(content)} bytes, SHA-256={sha}")
else:
    print("  static/media does not exist")

print("\n=== 4. QUESTIONS & CHECKPOINTS ===")
questions = conn.execute('SELECT lesson_id, count(*) as q_count FROM questions GROUP BY lesson_id').fetchall()
print(f'Questions per lesson count: {len(questions)}')
for q in questions:
    print(f"  [{q['lesson_id']}]: {q['q_count']} questions")

chk = conn.execute('SELECT q.id, q.lesson_id, q.timestamp_seconds, q.topic FROM questions q WHERE q.timestamp_seconds > 0').fetchall()
print(f'In-video checkpoints (timestamp > 0): {len(chk)}')
for c in chk:
    print(f"  [{c['lesson_id']}] at {c['timestamp_seconds']}s: {c['topic']}")

print("\n=== 5. PROGRESS & ATTEMPTS ===")
prog = conn.execute('SELECT * FROM progress').fetchall()
print(f'Progress records: {len(prog)}')
for p in prog:
    print(f"  user={p['user_id']} lesson={p['lesson_id']} pos={p['position_seconds']}s completed={p['is_completed']}")

att = conn.execute('SELECT * FROM attempts').fetchall()
print(f'Quiz attempts: {len(att)}')
for a in att:
    print(f"  user={a['user_id']} q={a['question_id']} opt={a['selected_option']} correct={a['is_correct']}")

