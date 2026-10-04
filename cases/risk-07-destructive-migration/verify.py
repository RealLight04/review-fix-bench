import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "migrations/0007_split_name.py"
BASE = "migrations/0006_create_users.py"

USERS = [
    (1, "a@example.com", "Kim"),                 # 한 단어 이름
    (2, "b@example.com", "Kim Minsu"),           # 두 단어
    (3, "c@example.com", "Maria de la Cruz"),    # 여러 단어
    (4, "d@example.com", None),                  # 이름 없음
]


def load(res, name, src):
    ns = run_module(res, name, src)
    fn = ns.get("upgrade") if ns else None
    if ns is not None and fn is None:
        res.check(False, f"{name}: upgrade was renamed or removed")
    return fn


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    if parse(res, TARGET, src) is None:
        return
    base_up = load(res, BASE, orig[BASE])
    upgrade = load(res, TARGET, src)
    if base_up is None or upgrade is None:
        return

    # 기존 사용자가 들어 있는 DB에 마이그레이션을 적용한다
    conn = sqlite3.connect(":memory:")
    try:
        base_up(conn)
        conn.executemany("INSERT INTO users (id, email, full_name) VALUES (?, ?, ?)", USERS)
        conn.commit()
        try:
            upgrade(conn)
            conn.commit()
        except Exception as e:
            res.check(False, f"upgrade raised {type(e).__name__}: {e}")
            return

        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
        res.check("first_name" in cols and "last_name" in cols,
                  f"users has no first_name/last_name after upgrade (columns: {cols})")
        res.check("email" in cols, "the email column is gone")
        if "first_name" not in cols or "last_name" not in cols:
            return
        rows = {r[0]: r for r in conn.execute(
            "SELECT id, email, first_name, last_name FROM users")}
        res.check(len(rows) == len(USERS), f"users has {len(rows)} rows after upgrade, expected {len(USERS)}")

        for uid, email, full in USERS:
            row = rows.get(uid)
            if row is None:
                res.check(False, f"user {uid} is gone")
                continue
            res.check(row[1] == email, f"user {uid}: email changed to {row[1]!r}")
            first, last = row[2], row[3]
            if full is None:
                continue  # 이름이 없던 사용자는 행만 남으면 된다
            res.check(bool(first) and isinstance(first, str),
                      f"user {uid} ({full!r}): first_name is empty ({first!r})")
            joined = f"{first or ''} {last or ''}".strip()
            res.check(joined == full,
                      f"user {uid}: first_name+last_name give {joined!r}, the old name was {full!r}")
            if " " in full:
                res.check(bool(last),
                          f"user {uid} ({full!r}): last_name is empty ({last!r})")
            else:
                res.check(first == full,
                          f"user {uid}: one-word name {full!r} became first_name={first!r}")
    finally:
        conn.close()

    # 마이그레이션 밖의 코드는 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"def:upgrade"}, imports="exact")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
