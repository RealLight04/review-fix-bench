"""users.full_name 을 first_name / last_name 으로 나눈다."""


def upgrade(conn):
    # full_name 은 남겨 둔다. 지우는 건 값이 안전하게 옮겨진 뒤 다음 마이그레이션에서.
    conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
    conn.execute(
        "UPDATE users SET "
        "first_name = CASE WHEN instr(full_name, ' ') = 0 THEN full_name "
        "ELSE substr(full_name, 1, instr(full_name, ' ') - 1) END, "
        "last_name = CASE WHEN instr(full_name, ' ') = 0 THEN '' "
        "ELSE substr(full_name, instr(full_name, ' ') + 1) END"
    )
