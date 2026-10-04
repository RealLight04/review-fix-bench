import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/listing.py"


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
    page_count = ns.get("page_count")
    paginate = ns.get("paginate")
    if page_count is None or paginate is None:
        res.check(False, "page_count or paginate was renamed or removed")
        return

    # 1) 경계에서 페이지 수가 맞는다: 딱 나눠떨어짐, 하나 넘침, 항목 없음, 항목 하나, per_page 1
    cases = [
        ((20, 10), 2), ((21, 10), 3), ((29, 10), 3), ((30, 10), 3), ((1, 10), 1),
        ((5, 10), 1), ((0, 10), 0), ((1, 1), 1), ((7, 1), 7), ((10, 3), 4), ((9, 3), 3),
        ((100, 25), 4), ((101, 25), 5),
    ]
    for args, want in cases:
        try:
            got = page_count(*args)
            res.check(got == want, f"page_count{args} returned {got!r}, expected {want}")
        except Exception as e:
            res.check(False, f"page_count{args} raises {type(e).__name__}: {e}")

    # 2) per_page가 0 이하이면 예전처럼 0 (예외 없이)
    for args in ((10, 0), (10, -5), (0, 0), (0, -1)):
        try:
            got = page_count(*args)
            res.check(got == 0, f"page_count{args} returned {got!r}, expected 0")
        except Exception as e:
            res.check(False, f"page_count{args} raises {type(e).__name__}: {e}")
    # 항목 수가 음수여도 0
    try:
        res.check(page_count(-3, 10) == 0, "page_count(-3, 10) is not 0")
    except Exception as e:
        res.check(False, f"page_count(-3, 10) raises {type(e).__name__}: {e}")

    # 3) 모든 페이지를 이어붙이면 항목 전체가 빠짐없이 나온다. 그 다음 페이지는 비어 있다.
    try:
        for total in range(0, 36):
            items = list(range(total))
            for per_page in range(1, 13):
                n = page_count(total, per_page)
                joined = []
                for p in range(1, n + 1):
                    joined.extend(paginate(items, p, per_page))
                res.check(joined == items,
                          f"pages 1..{n} of {total} items at {per_page} per page do not cover every item")
                res.check(paginate(items, n + 1, per_page) == [],
                          f"page {n + 1} of {total} items at {per_page} per page is not empty")
    except Exception as e:
        res.check(False, f"walking all pages raises {type(e).__name__}: {e}")

    # 4) paginate는 범위 안 페이지에서 예전과 같은 조각을, 범위 밖에서는 빈 리스트를 돌려준다
    try:
        items = list(range(21))
        res.check(paginate(items, 1, 10) == list(range(0, 10)), "paginate page 1 changed")
        res.check(paginate(items, 2, 10) == list(range(10, 20)), "paginate page 2 changed")
        res.check(paginate(items, 3, 10) == [20], "paginate page 3 changed")
        res.check(paginate(items, 4, 10) == [], "paginate past the last page is not empty")
        res.check(paginate(items, 0, 10) == [], "paginate page 0 is not empty")
        res.check(paginate(items, -1, 10) == [], "paginate negative page is not empty")
        res.check(paginate(items, 1, 0) == [], "paginate with per_page 0 is not empty")
        res.check(paginate(items, 1, -2) == [], "paginate with negative per_page is not empty")
        res.check(paginate([], 1, 10) == [], "paginate of an empty list is not empty")
        res.check(paginate(items, 2, 1) == [1], "paginate with per_page 1 changed")
        res.check(paginate(tuple(items), 3, 10) == [20], "paginate no longer returns a list for a tuple")
    except Exception as e:
        res.check(False, f"paginate raises {type(e).__name__}: {e}")

    # page_count 밖의 코드는 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"def:page_count"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
