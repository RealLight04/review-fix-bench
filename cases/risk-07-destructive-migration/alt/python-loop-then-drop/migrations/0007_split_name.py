"""users.full_name 을 first_name / last_name 으로 나눈다."""


def upgrade(conn):
    conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
    rows = conn.execute("SELECT id, full_name FROM users").fetchall()
    for user_id, full_name in rows:
        parts = (full_name or "").split(None, 1)
        first = parts[0] if parts else full_name
        last = parts[1] if len(parts) > 1 else ""
        conn.execute(
            "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?",
            (first, last, user_id),
        )
    conn.execute("ALTER TABLE users DROP COLUMN full_name")
