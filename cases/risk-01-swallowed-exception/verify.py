import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/alerts.py"


class Row:
    def __init__(self, rid, body, alerted):
        self.id = rid
        self.body = body
        self.alerted = alerted


class Store:
    """What is on disk. It outlives every cycle; nothing else does."""

    def __init__(self):
        self.failing = False   # while True, every commit raises
        self.rows = {}         # id -> (body, alerted)

    def insert(self, rid, body):
        self.rows[rid] = (body, False)

    def is_alerted(self, rid):
        return self.rows[rid][1]


class Session:
    """A new database session for one dispatch cycle. Each cycle is a fresh process:
    it loads the module again, opens a new session and reads rows from what was
    actually committed. That is the whole point of the finding. An in-memory
    `row.alerted = True` that never reached disk is gone by the next run, and so is
    any state kept in module globals, on the function, or on the session object."""

    def __init__(self, store):
        self.store = store
        self.loaded = []

    def query(self):
        self.loaded = [Row(rid, body, alerted) for rid, (body, alerted) in self.store.rows.items()]
        return self.loaded

    def commit(self):
        if self.store.failing:
            raise RuntimeError("database is locked")
        for r in self.loaded:
            self.store.rows[r.id] = (r.body, r.alerted)

    def rollback(self):
        for r in self.loaded:
            r.alerted = self.store.rows[r.id][1]


def cycle(res, src, store, send):
    """One scheduled run in a fresh module and a fresh session. Raising is an
    acceptable way for dispatch to fail."""
    ns = run_module(res, TARGET, src)
    if ns is None or "dispatch" not in ns:
        res.check(False, "dispatch was renamed or removed")
        return None
    db = Session(store)
    try:
        return ns["dispatch"](db, db.query(), send)
    except Exception:
        return None


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    if parse(res, TARGET, src) is None:
        return

    # 1) 정상 경로: 한 건 보내고, 저장소에도 보냈다고 남는다
    store = Store()
    store.insert(1, "새 공연 등재")
    delivered = []
    n = cycle(res, src, store, delivered.append)
    res.check(n == 1, f"normal path returned {n}, expected 1")
    res.check(delivered == ["새 공연 등재"], f"normal path delivered {delivered}")
    res.check(store.is_alerted(1), "normal path did not persist alerted=True")

    # 2) 핵심: 커밋이 한동안 계속 실패했다가 회복돼도 같은 알림이 두 번 나가면 안 된다.
    #    재시도로 실패를 흡수하는 수정은 여기서 걸린다(잠금이 첫 주기 내내 풀리지 않는다).
    store = Store()
    store.insert(1, "새 공연 등재")
    delivered = []
    store.failing = True
    n1 = cycle(res, src, store, delivered.append)
    store.failing = False
    n2 = cycle(res, src, store, delivered.append)
    n3 = cycle(res, src, store, delivered.append)
    res.check(n1 in (0, None), f"the cycle whose commit failed reported {n1} sent")
    res.check(n3 in (0, None), f"a later cycle reported {n3} sent although nothing was left to send")
    res.check(len(delivered) <= 1,
              f"the same alert went out {len(delivered)} times after a failed commit")
    res.check(len(delivered) >= 1, "the alert was never delivered once the database recovered")
    res.check(n2 == 1, f"the cycle that delivered the alert reported {n2} sent, expected 1")

    # 3) 발송 자체가 실패했다면 저장소에 보냈다고 남으면 안 된다
    store = Store()
    store.insert(1, "발송 실패할 건")

    def boom(body):
        raise RuntimeError("telegram 502")

    n = cycle(res, src, store, boom)
    res.check(not store.is_alerted(1), "persisted alerted=True even though sending raised")
    res.check(n in (0, None), f"reported {n} sent although sending raised")

    same_except(res, TARGET, orig[TARGET], src, skip={"def:dispatch"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
