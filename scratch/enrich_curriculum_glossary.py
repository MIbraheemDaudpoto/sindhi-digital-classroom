import sqlite3
import shutil
from datetime import datetime
import re

# 1. Backup DB
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_name = f"data/backups/sdc_platform_backup_{ts}.db"
shutil.copy2("data/sdc_platform.db", backup_name)
print(f"Verified backup saved: {backup_name}")

conn = sqlite3.connect("data/sdc_platform.db")
cur = conn.cursor()

chapter_ranges = [
    (1, 5, 22),
    (2, 23, 36),
    (3, 37, 44),
    (4, 45, 58),
    (5, 59, 73),
    (6, 74, 82),
    (7, 83, 95),
    (8, 96, 112),
    (9, 113, 126),
    (10, 127, 141),
    (11, 142, 155),
    (12, 156, 170)
]

# Explicit term topic mappings for unverified pages
topic_fallbacks = {
    "اولفڪٽري خابرو": 2, "نڪ": 2,
    "غير حياتياتي عنصر": 4, "جڙي ٻوٽي خور": 4, "گوشت خور": 4, "سڀ خور": 4, "بيڪٽيريا": 4, "فنگس": 4,
    "چڪائڻ": 7, "ڪافورجڻ": 7, "رنگي تجزياتي ڪاغذ": 7,
    "آڪسيجن": 5, "آرگان": 5, "هيليم": 5, "هيڊروجن": 5, "ميٿين": 5, "نائٽريفڪيشن": 4, "لحميات": 4, "ايزوٽ": 5, "غير فعال گئس": 5
}

rows = cur.execute("SELECT id, term_sd, pdf_page FROM sdc_glossary WHERE subject_id = 'science-6'").fetchall()
updated = 0
for r_id, term, pdf in rows:
    pdf = pdf or ""
    ch_id = None
    m = re.search(r'(\d+)', pdf)
    if m:
        page_num = int(m.group(1))
        for cid, p_start, p_end in chapter_ranges:
            if p_start <= page_num <= p_end:
                ch_id = cid
                break
    if not ch_id and term in topic_fallbacks:
        ch_id = topic_fallbacks[term]
    
    if ch_id:
        cur.execute("UPDATE sdc_glossary SET chapter_id = ? WHERE id = ?", (ch_id, r_id))
        updated += 1

conn.commit()

# Verify count per chapter
counts = cur.execute("SELECT chapter_id, count(*) FROM sdc_glossary WHERE subject_id = 'science-6' GROUP BY chapter_id ORDER BY chapter_id").fetchall()
print(f"Updated {updated} science-6 glossary items. Counts per chapter:")
for cid, cnt in counts:
    print(f"  Chapter {cid}: {cnt} terms")

conn.close()
