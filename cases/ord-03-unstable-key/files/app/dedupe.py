"""수집 배치 안에서 키를 만들고 중복을 접는다."""


def norm(s):
    return "".join(ch for ch in (s or "") if ch.isalnum())


def batch_keys(source, rows):
    """rows: [{title, start_date}] → [key]

    start_date는 date 또는 None.
    """
    keys = []
    for row in rows:
        start = row.get("start_date")
        if start:
            keys.append(f"{source}:{norm(row['title'])}|{start.isoformat()}")
        else:
            keys.append(f"{source}:{norm(row['title'])}|nodate")
    return keys
