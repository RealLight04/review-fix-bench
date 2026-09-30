import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, nondeterministic_calls, parse, run_module, same_except, untouched

TARGET = "app/sources/common.py"


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
    build = ns.get("build_show")
    if build is None:
        res.check(False, "build_show was renamed or removed")
        return

    # 1) 날짜를 못 읽어도 터지지 않는다. 행은 필드 하나 빠짐없이 나오고, 키는 실행마다 같아야 한다.
    for text in ("추후 공지", None, ""):
        try:
            row = build("tix", "샘플 콘서트", text, "공연장 A")
            key = row.pop("source_key", None)
            res.check(row == {"source": "tix", "title": "샘플 콘서트", "venue": "공연장 A",
                              "start_date": None, "end_date": None, "date_text": text},
                      f"row for date text {text!r} is not the expected dict: {row!r}")
            res.check(bool(key), f"source_key is empty for a dateless row ({text!r})")
            again = build("tix", "샘플 콘서트", text, "공연장 A")["source_key"]
            res.check(key == again, f"source_key changes between identical calls: {key!r} vs {again!r}")
            res.check(date.today().isoformat() not in (key or ""),
                      "source_key of a dateless row is built from today's date")
        except Exception as e:
            res.check(False, f"raises on date text {text!r}: {type(e).__name__}: {e}")
    try:
        k1 = build("tix", "샘플 콘서트", "추후 공지", "A")["source_key"]
        k2 = build("tix", "다른 공연", "추후 공지", "A")["source_key"]
        res.check(k1 != k2, "two different titles with no date get the same source_key")
    except Exception as e:
        res.check(False, f"raises on the second-title probe: {type(e).__name__}: {e}")
    unstable = nondeterministic_calls(src, "build_show")
    res.check(not unstable, f"build_show calls {', '.join(unstable)}, which is not stable between runs")

    # 2) 날짜가 있는 행은 예전과 완전히 같아야 한다 (키 형식이 바뀌면 기존 행과 끊긴다)
    try:
        row = build("tix", "샘플 콘서트", "2026.11.01 ~ 2026.11.03", "공연장 A")
        res.check(row == {"source": "tix", "source_key": "tix:샘플콘서트|2026-11-01",
                          "title": "샘플 콘서트", "venue": "공연장 A",
                          "start_date": date(2026, 11, 1), "end_date": date(2026, 11, 3),
                          "date_text": "2026.11.01 ~ 2026.11.03"},
                  f"row for a dated listing changed: {row!r}")
    except Exception as e:
        res.check(False, f"broke the normal path: {type(e).__name__}: {e}")

    # build_show 밖의 코드는 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"def:build_show"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
