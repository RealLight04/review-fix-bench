"""수집 소스 공통 유틸."""
import re
from datetime import date

_DATE = re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")


def norm(s):
    """공백·기호를 뺀 영숫자만 남긴다."""
    return "".join(ch for ch in (s or "") if ch.isalnum())


def parse_dates(text):
    """'2026.11.01 ~ 2026.11.03' → (date, date). 못 읽으면 (None, None)."""
    if not text:
        return None, None
    found = _DATE.findall(text)
    if not found:
        return None, None
    out = [date(int(y), int(m), int(d)) for y, m, d in found]
    return out[0], out[-1]


def build_show(source, title, date_text, venue):
    """수집 결과 한 건을 dict로."""
    start, end = parse_dates(date_text)
    stamp = start.isoformat() if start else "nodate"
    return {
        "source": source,
        "source_key": f"{source}:{norm(title)}|{stamp}",
        "title": title,
        "venue": venue,
        "start_date": start,
        "end_date": end,
        "date_text": date_text,
    }
