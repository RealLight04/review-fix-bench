import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/feed.py"


def post(pid, ts, pinned=False):
    return {"id": pid, "title": f"t{pid}", "created_at": ts, "pinned": pinned}


def ids(rows):
    return [p["id"] for p in rows]


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
    latest = ns.get("latest_posts")
    if latest is None:
        res.check(False, "latest_posts was renamed or removed")
        return

    def probe(label, posts, limit, expected):
        try:
            got = ids(latest(posts, limit))
            res.check(got == expected, f"{label}: expected {expected}, got {got}")
        except Exception as e:
            res.check(False, f"{label}: raises {type(e).__name__}: {e}")

    # 1) 가장 최근 글이 먼저, limit개만
    posts = [post(1, 300), post(2, 100), post(3, 500), post(4, 200), post(5, 400)]
    probe("newest three", posts, 3, [3, 5, 1])
    probe("limit 1", posts, 1, [3])
    # 2) limit이 목록보다 크면 전부, 최신순
    probe("limit larger than the list", posts, 10, [3, 5, 1, 4, 2])
    # 3) limit 0, 빈 목록
    probe("limit 0", posts, 0, [])
    probe("empty list", [], 5, [])
    # 4) created_at이 같으면 들어온 순서 유지
    ties = [post(1, 100), post(2, 200), post(3, 200), post(4, 300), post(5, 200), post(6, 100)]
    probe("ties keep input order", ties, 6, [4, 2, 3, 5, 1, 6])
    probe("ties cut at the limit", ties, 3, [4, 2, 3])
    probe("ties cut inside a tie group", ties, 2, [4, 2])
    # 5) 입력 목록은 건드리지 않는다
    try:
        fresh = [post(1, 300), post(2, 100), post(3, 500), post(4, 200), post(5, 400)]
        before = [dict(p) for p in fresh]
        latest(fresh, 3)
        res.check(fresh == before, "latest_posts modified the list it was given")
    except Exception as e:
        res.check(False, f"raises when checking the input list: {type(e).__name__}: {e}")

    # 6) pinned_first는 그대로 동작
    pf = ns.get("pinned_first")
    if pf is None:
        res.check(False, "pinned_first was renamed or removed")
    else:
        try:
            rows = [post(1, 100), post(2, 900, True), post(3, 300), post(4, 50, True), post(5, 200)]
            res.check(ids(pf(rows)) == [2, 4, 1, 3, 5],
                      f"pinned_first changed behavior: {ids(pf(rows))}")
        except Exception as e:
            res.check(False, f"pinned_first raises {type(e).__name__}: {e}")

    # latest_posts 밖의 코드는 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"def:latest_posts"})
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
