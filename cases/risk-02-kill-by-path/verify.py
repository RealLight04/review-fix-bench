import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "scripts/smoke.py"

# 시나리오: 같은 venv에서 도는 프로세스 셋
#   4242 = 운영 서버, 9001 LISTEN  ← 절대 죽이면 안 됨
#   5555 = 9000에 남아 있는 옛 테스트 인스턴스  ← 이건 죽여야 함
#   6666 = 같은 venv의 무관한 워커, 아무 포트도 안 씀  ← 죽이면 안 됨
PROCESSES = [(4242, "/home/x/myapp/venv/bin/python"),
             (5555, "/home/x/myapp/venv/bin/python"),
             (6666, "/home/x/myapp/venv/bin/python"),
             (7777, "/usr/bin/python")]
LISTENERS = [(9001, 4242), (9000, 5555)]


def run(res, src, port=None):
    """Load the module with only allow-listed imports (see harness.run_module), then
    replace the three environment hooks with recording stubs. Nothing here can
    reach real processes."""
    ns = run_module(res, TARGET, src)
    if ns is None:
        return None, [], None
    killed = []
    ns["list_processes"] = lambda: list(PROCESSES)
    ns["list_listeners"] = lambda: list(LISTENERS)
    ns["kill"] = lambda pid: killed.append(pid)
    fn = ns.get("stop_previous")
    if fn is None:
        return None, killed, ns
    returned = fn() if port is None else fn(port)
    ns["__returned__"] = returned
    return fn, killed, ns


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    if parse(res, TARGET, src) is None:
        return

    try:
        fn, killed, ns = run(res, src)
    except Exception as e:
        res.check(False, f"stop_previous raised: {type(e).__name__}: {e}")
        return
    if ns is None:
        return
    if fn is None:
        res.check(False, "stop_previous was renamed or removed")
        return

    res.check(ns.get("__returned__") == [5555], f"stop_previous should return the pids it killed, [5555]; got {ns.get('__returned__')!r}")
    res.check(4242 not in killed,
              "STILL KILLS THE PRODUCTION SERVER on 9001, which is the whole finding")
    res.check(6666 not in killed, "killed an unrelated venv process that holds no port")
    res.check(7777 not in killed, "killed a process outside this project")
    res.check(5555 in killed,
              "did not kill the stale instance actually sitting on port 9000")

    # 기본 포트는 9000으로 유지돼야 한다
    res.check(ns.get("DEFAULT_PORT") == 9000,
              f"changed DEFAULT_PORT to {ns.get('DEFAULT_PORT')!r}; finding said keep 9000")

    # 포트를 넘기면 그 포트만 대상으로
    try:
        _, killed_9001, ns9001 = run(res, src, port=9001)
        res.check(ns9001 is not None and ns9001.get("__returned__") == [4242], f"stop_previous(9001) should return [4242]; got {ns9001.get('__returned__') if ns9001 else None!r}")
        res.check(killed_9001 == [4242],
                  f"explicit port=9001 should target only pid 4242, got {killed_9001}")
    except Exception as e:
        res.check(False, f"stop_previous(port) raised: {type(e).__name__}: {e}")

    same_except(res, TARGET, orig[TARGET], src, skip={"def:stop_previous"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
