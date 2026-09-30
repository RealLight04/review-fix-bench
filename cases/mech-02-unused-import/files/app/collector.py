import json
import logging
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)


def collect(sources):
    """각 소스를 돌며 결과를 모은다. 한 소스가 터져도 나머지는 계속한다."""
    today = date.today()
    results = {}
    for name, fetch in sources.items():
        try:
            rows = fetch()
        except Exception as e:
            log.warning("%s 수집 실패: %s", name, e)
            results[name] = f"실패 — {type(e).__name__}"
            continue
        results[name] = f"{len(rows)}건 ({datetime.now():%H:%M})"
    log.info("수집 완료 %s", today)
    return results
