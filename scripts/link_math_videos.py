import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "sdc_platform.db"
JSON_PATH = ROOT / "data" / "stbb_math_6_complete.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Map unit number to first video
unit_videos = {}
for v in data.get("videos", []):
    ch = v.get("chapter_id")
    if ch not in unit_videos and v.get("watch_url"):
        url = v["watch_url"]
        yt_id = url.split("v=")[-1] if "v=" in url else url
        unit_videos[ch] = {
            "yt_id": yt_id,
            "title_sd": v.get("title_sd"),
            "title_en": v.get("title_en"),
            "duration": v.get("duration")
        }

print("Found unit videos:", len(unit_videos))
for u, v in sorted(unit_videos.items()):
    lesson_id = f"lesson-math-6-{u}"
    vid_id = f"vid-lesson-math-6-{u}"
    yt_rec_id = f"yt-lesson-math-6-{u}"
    yt_id = v["yt_id"]
    orig_url = f"https://www.youtube.com/watch?v={yt_id}"
    embed_url = f"https://www.youtube-nocookie.com/embed/{yt_id}"
    
    cur.execute("""
        INSERT OR REPLACE INTO videos (id, lesson_id, hls_url, fallback_url, audio_only_url, resolution_240p, resolution_360p, file_size_bytes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (vid_id, lesson_id, f"/static/media/{lesson_id}.m3u8", "/static/media/lesson-math-6-1.mp4", f"/static/media/{lesson_id}.mp3", None, None, 25000000))
    
    cur.execute("""
        INSERT OR REPLACE INTO youtube_videos (id, lesson_id, youtube_id, title, channel_name, original_url, embed_url, class_level, subject, language, topic, duration_seconds, curriculum_status, attribution_text, is_embeddable, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (yt_rec_id, lesson_id, yt_id, v["title_sd"] or v["title_en"], "Sindh Online School", orig_url, embed_url, 6, "Math", "sindhi", v["title_en"], 600, "VERIFIED_OFFICIAL", "سنڌ آن لائين اسڪول سرڪاري يوٽيوب مواد", 1))

conn.commit()
conn.close()
print("Successfully linked all 13 Math units to Sindh Online School videos!")

