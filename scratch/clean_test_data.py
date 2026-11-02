import sqlite3

for db_path in ['sindhi_classroom.db', 'data/sdc_platform.db']:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM lessons WHERE id LIKE 'test-%'")
        d_lsn = cur.rowcount
        cur.execute("DELETE FROM courses WHERE id LIKE 'test-%'")
        d_crs = cur.rowcount
        conn.commit()
        print(f"Cleaned {db_path}: {d_lsn} lessons, {d_crs} courses removed.")
        conn.close()
    except Exception as e:
        print(f"Error on {db_path}: {e}")
