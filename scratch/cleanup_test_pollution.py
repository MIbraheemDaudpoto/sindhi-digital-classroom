import sqlite3
import shutil
from datetime import datetime

backup_path = f"data/backups/sdc_platform_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy2("data/sdc_platform.db", backup_path)
print(f"Backup created at: {backup_path}")

conn = sqlite3.connect("data/sdc_platform.db")
conn.row_factory = sqlite3.Row

# Check tables with test-crs or test-lsn
test_courses = conn.execute("SELECT id FROM courses WHERE id LIKE 'test-crs-%'").fetchall()
test_cids = [c["id"] for c in test_courses]
print(f"Found {len(test_cids)} test courses: {test_cids}")

test_lessons = conn.execute("SELECT id FROM lessons WHERE course_id LIKE 'test-crs-%' OR id LIKE 'test-lsn-%'").fetchall()
test_lids = [l["id"] for l in test_lessons]
print(f"Found {len(test_lids)} test lessons: {test_lids}")

# Check references in progress
prog_count = conn.execute(f"SELECT COUNT(*) as c FROM progress WHERE lesson_id IN ({','.join(['?']*len(test_lids))})", test_lids).fetchone()["c"] if test_lids else 0
print(f"References in progress table: {prog_count}")

# Check references in questions
q_count = conn.execute(f"SELECT COUNT(*) as c FROM questions WHERE lesson_id IN ({','.join(['?']*len(test_lids))})", test_lids).fetchone()["c"] if test_lids else 0
print(f"References in questions table: {q_count}")

if test_lids:
    conn.execute(f"DELETE FROM questions WHERE lesson_id IN ({','.join(['?']*len(test_lids))})", test_lids)
    conn.execute(f"DELETE FROM progress WHERE lesson_id IN ({','.join(['?']*len(test_lids))})", test_lids)
    conn.execute(f"DELETE FROM lessons WHERE id IN ({','.join(['?']*len(test_lids))})", test_lids)

if test_cids:
    conn.execute(f"DELETE FROM courses WHERE id IN ({','.join(['?']*len(test_cids))})", test_cids)

conn.commit()
print("Successfully cleaned up test course artifacts from live database.")
conn.close()

