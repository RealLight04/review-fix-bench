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
        # 보내기 전에 표시부터 저장한다. 저장이 안 되면 이번 주기엔 보내지 않는다.
        row.alerted = True
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            log.warning("발송 표시 저장 실패, 다음 주기에 다시 시도: %s", e)
            continue
        try:
            send(row.body)
        except Exception as e:
            log.warning("알림 발송 실패: %s", e)
            row.alerted = False
            try:
                db.commit()
            except Exception as e2:
                db.rollback()
                log.error("발송 실패 표시 되돌리기 실패: %s", e2)
            continue
        sent += 1
    return sent
