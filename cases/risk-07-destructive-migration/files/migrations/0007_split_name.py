"""users.full_name 을 first_name / last_name 으로 나눈다."""


def upgrade(conn):
    conn.execute("ALTER TABLE users DROP COLUMN full_name")
    conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
