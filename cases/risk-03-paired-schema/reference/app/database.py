"""엔진 + 자가치유 마이그레이션."""
import sqlite3

DB_PATH = "data/app.db"

# 기존 DB에 없는 컬럼을 시작할 때 ALTER로 채운다.
# models.py에 컬럼을 추가하면 여기에도 반드시 같이 추가할 것.
MIGRATIONS = {
    "shows": {
        "venue": "TEXT",
        "start_date": "DATE",
        "is_upcoming": "BOOLEAN DEFAULT 1",
        "poster_url": "TEXT",
    },
}


def init_db():
    con = sqlite3.connect(DB_PATH)
    for table, columns in MIGRATIONS.items():
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns.items():
            if name not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    con.commit()
    con.close()
