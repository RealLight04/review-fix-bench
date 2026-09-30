import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, nondeterministic_calls, parse, run_module, same_except, untouched

TARGET = "app/dedupe.py"


def rows(n, start=None):
    """Fresh, equal dicts every call, so a key built from object identity shows up."""
    return [{"title": "샘플 콘서트", "start_date": start} for _ in range(n)]


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    if parse(res, TARGET, src) is None:
        return

    ns = run_module(res, TARGET, src)
    if ns is None:
        return
    fn = ns.get("batch_keys")
    if fn is None:
        res.check(False, "batch_keys was renamed or removed")
        return

    # 1) 제목이 같고 날짜가 없는 5건: 키가 전부 달라야 한다
    try:
        keys = fn("tix", rows(5))
        res.check(len(set(keys)) == 5,
                  f"dateless rows still collide: {len(set(keys))} unique of 5")
        # 날짜 있는 행의 키와도 겹치면 안 된다
        mixed = fn("tix", rows(2) + rows(1, date(2026, 11, 1)))
        res.check(len(set(mixed)) == 3, "a dateless key collides with another row")
    except Exception as e:
        res.check(False, f"raised on dateless rows: {type(e).__name__}: {e}")

    # 2) 날짜가 있는 행의 키 형식은 그대로: 기존 저장 행과 이어져야 한다
    try:
        got = fn("tix", rows(1, date(2026, 11, 1)))[0]
        res.check(got == "tix:샘플콘서트|2026-11-01",
                  f"changed the key format for dated rows: {got!r}")
    except Exception as e:
        res.check(False, f"broke the dated path: {type(e).__name__}: {e}")

    # 3) 키는 입력 행과 같은 순서로 나와야 한다 (정렬하거나 섞으면 행과 키가 어긋난다)
    try:
        batch = rows(1, date(2026, 11, 2)) + rows(1) + rows(1, date(2026, 11, 1))
        got = fn("tix", batch)
        res.check(len(got) == 3 and got[0].endswith("|2026-11-02") and got[2].endswith("|2026-11-01")
                  and "2026-11" not in got[1],
                  f"keys no longer line up with their rows: {got!r}")
    except Exception as e:
        res.check(False, f"raised on the ordering probe: {type(e).__name__}: {e}")

    # 4) 같은 입력이면 같은 키: 실행마다 달라지면 매번 '새 공연'이 된다.
    #    새로 만든 같은 내용의 dict로 두 번 불러서 id()나 무작위 값을 잡아낸다.
    try:
        first, second = fn("tix", rows(5)), fn("tix", rows(5))
        res.check(first == second, "keys differ between two identical batches")
        res.check(all(date.today().isoformat() not in k for k in first),
                  "a dateless key is built from today's date")
    except Exception as e:
        res.check(False, f"raised on stability probe: {type(e).__name__}: {e}")
    unstable = nondeterministic_calls(src, "batch_keys")
    res.check(not unstable, f"batch_keys calls {', '.join(unstable)}, which is not stable between runs")

    same_except(res, TARGET, orig[TARGET], src, skip={"def:batch_keys"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
