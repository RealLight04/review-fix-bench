"""users 테이블 생성."""


def upgrade(conn):
    conn.execute(
        "CREATE TABLE users ("
        "id INTEGER PRIMARY KEY, "
        "email TEXT NOT NULL, "
        "full_name TEXT)"
    )
