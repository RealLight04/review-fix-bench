import logging
from datetime import date, datetime

log = logging.getLogger(__name__)


def collect(sources):
    """소스별 수집."""
    today = date.today()
    results = {}
    for name, fetch in sources.items():
        try:
            rows = fetch()
        except Exception as exc:
            log.warning("%s 수집 실패: %s", name, exc)
            results[name] = f"실패 — {type(exc).__name__}"
            continue
        results[name] = f"{len(rows)}건 ({datetime.now():%H:%M})"
    log.info("수집 완료 %s", today)
    return results
