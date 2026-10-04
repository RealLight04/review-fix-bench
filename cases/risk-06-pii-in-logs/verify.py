import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/signup.py"


class FakeLogger:
    """Collects every call as (level, msg, args, kwargs) instead of logging."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, level):
        if level.startswith("_"):
            raise AttributeError(level)

        def record(msg=None, *args, **kwargs):
            self.calls.append((level, msg, args, kwargs))
        return record

    def text(self):
        return "\n".join(f"{lvl} {m!r} {a!r} {k!r}" for lvl, m, a, k in self.calls)


class FakeDB:
    def __init__(self):
        self.inserted = []

    def insert_user(self, user):
        self.inserted.append(dict(user))
        return 7


PROBES = [
    # (form, expected failed fields, personal values that must not reach the log)
    ({"name": "김민준", "email": "minjun.kim@mjkim-private", "phone": "010-4821-7365",
      "birth_date": "1991.03.14"},
     ["email", "birth_date"],
     ["김민준", "민준", "minjun", "mjkim", "4821", "7365", "01048217365", "1991", "03.14"]),
    ({"name": "Jane Roe", "email": "jane.roe@corp-mail.org", "phone": "02-555-0199",
      "birth_date": "1988-07-02"},
     ["phone"],
     ["Jane", "Roe", "jane.roe", "corp-mail", "555-0199", "5550199", "1988", "07-02"]),
]


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
    register = ns.get("register")
    if register is None:
        res.check(False, "register was renamed or removed")
        return

    # 1) 실패한 가입: 개인 값은 로그 어디에도 없고, 실패 사실과 필드 이름은 남는다
    for form, failed, secrets in PROBES:
        snapshot = dict(form)
        logger, db = FakeLogger(), FakeDB()
        try:
            out = register(dict(form), db, logger)
        except Exception as e:
            res.check(False, f"raises on a bad form: {type(e).__name__}: {e}")
            continue
        text = logger.text()
        leaked = [s for s in secrets if s in text]
        res.check(not leaked, f"personal values reached the logger: {leaked!r} in {text!r}")
        res.check(out == {"ok": False, "errors": failed},
                  f"result for a bad form changed: {out!r}")
        res.check(not db.inserted, "a form that failed validation was saved")
        warned = [c for c in logger.calls if c[0] in ("error", "warning", "exception", "critical")]
        res.check(bool(warned), "the failed signup is no longer logged at warning level or above")
        res.check(all(f in text for f in failed),
                  f"the log no longer says which fields failed ({failed!r}): {text!r}")
        res.check(form == snapshot, "register modified the form it was given")

    # 2) 성공 경로: 저장하고, 예전과 같은 한 줄만 남긴다
    good = {"name": "김민준", "email": "minjun.kim@mjkim-private.net", "phone": "010-4821-7365",
            "birth_date": "1991-03-14"}
    logger, db = FakeLogger(), FakeDB()
    try:
        out = register(dict(good), db, logger)
        res.check(out == {"ok": True, "user_id": 7}, f"result for a good form changed: {out!r}")
        res.check(db.inserted == [good], "the good form was not saved as submitted")
        res.check(logger.calls == [("info", "signup ok: user_id=%s", (7,), {})],
                  f"success-path logging changed: {logger.calls!r}")
    except Exception as e:
        res.check(False, f"broke the normal path: {type(e).__name__}: {e}")

    same_except(res, TARGET, orig[TARGET], src, skip={"def:register"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
