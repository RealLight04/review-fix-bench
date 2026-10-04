"""users.full_name 을 first_name / last_name 으로 나눈다."""


def upgrade(conn):
    conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
    conn.execute(
        "UPDATE users SET "
        "first_name = substr(full_name, 1, instr(full_name, ' ') - 1), "
        "last_name = substr(full_name, instr(full_name, ' ') + 1) "
        "WHERE instr(full_name, ' ') > 0"
    )
    conn.execute("ALTER TABLE users DROP COLUMN full_name")
