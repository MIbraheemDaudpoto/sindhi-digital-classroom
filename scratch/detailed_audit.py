import sqlite3, os, hashlib
from pathlib import Path

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row

with open('scratch/db_detailed_audit.txt', 'w', encoding='utf-8') as out:
    out.write("=== COURSES ===\n")
    for r in conn.execute("SELECT * FROM courses"):
        out.write(f"  id={r['id']}, class_level={r['class_level']}, subject={r['subject']}, title_en={r['title_english']}, title_sd={r['title_sindhi']}\n")

    out.write("\n=== LESSONS ===\n")
    lessons = conn.execute("SELECT * FROM lessons").fetchall()
    out.write(f"Total Lessons: {len(lessons)}\n")
    for r in lessons:
        out.write(f"  id={r['id']}, course_id={r['course_id']}, unit={r['unit_number']}, dur={r['duration_seconds']}s, status={r['status']} | {r['title_english']} | {r['title_sindhi']}\n")

    out.write("\n=== VIDEOS ===\n")
    videos = conn.execute("SELECT * FROM videos").fetchall()
    out.write(f"Total Videos: {len(videos)}\n")
    for r in videos:
        out.write(f"  id={r['id']}, lesson_id={r['lesson_id']}, hls={r['hls_url']}, fallback={r['fallback_url']}, audio={r['audio_only_url']}, res240={r['resolution_240p']}, res360={r['resolution_360p']}\n")

    out.write("\n=== YOUTUBE_VIDEOS ===\n")
    yt = conn.execute("SELECT * FROM youtube_videos").fetchall()
    out.write(f"Total YouTube Videos: {len(yt)}\n")
    for r in yt:
        out.write(f"  id={r['id']}, lesson_id={r['lesson_id']}, yt_id={r['youtube_id']}, cl={r['class_level']}, sub={r['subject']}, embed={r['is_embeddable']}, title={r['title']}\n")

    out.write("\n=== QUESTIONS ===\n")
    q_counts = conn.execute("SELECT lesson_id, count(*) as cnt, sum(case when timestamp_seconds > 0 then 1 else 0 end) as chk_cnt FROM questions GROUP BY lesson_id").fetchall()
    for r in q_counts:
        out.write(f"  lesson_id={r['lesson_id']}: total_q={r['cnt']}, checkpoints={r['chk_cnt']}\n")

    out.write("\n=== ATTEMPTS ===\n")
    att = conn.execute("SELECT * FROM attempts").fetchall()
    out.write(f"Total Attempts: {len(att)}\n")
    for r in att:
        out.write(f"  user={r['user_id']}, q={r['question_id']}, opt={r['selected_option']}, correct={r['is_correct']}, time={r['time_taken_seconds']}s, created={r['created_at']}\n")

    out.write("\n=== PROGRESS ===\n")
    prog = conn.execute("SELECT * FROM progress").fetchall()
    out.write(f"Total Progress records: {len(prog)}\n")
    for r in prog:
        out.write(f"  {dict(r)}\n")

    out.write("\n=== CHAT LOGS ===\n")
    cl = conn.execute("SELECT id, user_id, lesson_id, question_text, is_refused, created_at FROM chat_logs ORDER BY created_at DESC LIMIT 20").fetchall()
    out.write(f"Recent Chat Logs (total {conn.execute('SELECT count(*) FROM chat_logs').fetchone()[0]}):\n")
    for r in cl:
        out.write(f"  [{r['id']}] user={r['user_id']}, lesson={r['lesson_id']}, refused={r['is_refused']} | Q: {r['question_text']}\n")

    out.write("\n=== LOCAL MEDIA FILES ===\n")
    media_dir = Path("static/media")
    if media_dir.exists():
        files = list(media_dir.glob("*.*"))
        out.write(f"Total files in static/media: {len(files)}\n")
        for f in files:
            b = f.read_bytes()
            sha = hashlib.sha256(b).hexdigest()
            out.write(f"  {f.name}: size={len(b)} bytes, sha256={sha}\n")
    else:
        out.write("static/media not found\n")

print("Detailed audit written to scratch/db_detailed_audit.txt")
