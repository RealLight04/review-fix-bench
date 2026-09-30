"""알림 발송. 한 번 보낸 건 다시 보내지 않는다."""
import logging

log = logging.getLogger(__name__)


def dispatch(db, rows, send):
    """미발송 행을 훑어 알림을 보낸다.

    db: commit()/rollback()을 가진 세션
    rows: alerted 속성을 가진 행들
    send: 본문을 받아 발송하는 함수. 실패하면 예외를 던진다.
    """
    sent = 0
    for row in rows:
        if row.alerted:
            continue
        try:
            send(row.body)
            row.alerted = True
            db.commit()
            sent += 1
        except Exception as e:
            log.warning("알림 발송 실패: %s", e)
    return sent
