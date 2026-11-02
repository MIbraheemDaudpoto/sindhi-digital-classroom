import sqlite3

conn = sqlite3.connect('data/sdc_platform.db')
cursor = conn.cursor()

with open('scratch/db_schema_and_contents.txt', 'w', encoding='utf-8') as f:
    for row in cursor.execute("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table', 'view')"):
        f.write(f"=== {row[0].upper()}: {row[1]} ===\n")
        f.write(f"{row[2]}\n\n")

    f.write("\n================ TABLE ROW COUNTS ================\n")
    for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        tname = row[0]
        cnt = cursor.execute(f"SELECT COUNT(*) FROM [{tname}]").fetchone()[0]
        f.write(f"{tname}: {cnt} rows\n")

print("Schema and counts written to scratch/db_schema_and_contents.txt")

