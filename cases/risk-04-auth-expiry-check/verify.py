import sys
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/auth.py"


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
    valid = ns.get("is_session_valid")
    issue = ns.get("issue_session")
    end = ns.get("end_session")
    if valid is None or issue is None or end is None:
        res.check(False, "is_session_valid, issue_session or end_session was renamed or removed")
        return

    # 1) the validity check: live sessions pass, the expiry instant and later do not
    expiry = datetime(2026, 5, 1, 17, 0, 0)
    session = {"user_id": 7, "token": "t", "expires_at": expiry}
    probes = [
        ("one hour before expiry", expiry - timedelta(hours=1), True),
        ("one second before expiry", expiry - timedelta(seconds=1), True),
        ("exactly at expiry", expiry, False),
        ("one second after expiry", expiry + timedelta(seconds=1), False),
        ("one hour after expiry", expiry + timedelta(hours=1), False),
        ("a day after expiry", expiry + timedelta(days=1), False),
    ]
    for label, now, want in probes:
        try:
            got = valid(session, now)
            res.check(got == want and isinstance(got, bool),
                      f"is_session_valid {label}: got {got!r}, expected {want}")
        except Exception as e:
            res.check(False, f"is_session_valid raises {label}: {type(e).__name__}: {e}")
    try:
        res.check(valid(None, expiry) is False, "is_session_valid(None, now) must return False")
    except Exception as e:
        res.check(False, f"is_session_valid(None, now) raises: {type(e).__name__}: {e}")

    # keyword call keeps working, so the signature is unchanged
    try:
        res.check(valid(session=session, now=expiry - timedelta(minutes=5)) is True,
                  "is_session_valid(session=..., now=...) no longer works")
    except Exception as e:
        res.check(False, f"signature of is_session_valid changed: {type(e).__name__}: {e}")

    # 2) end to end: a fresh session is valid for its lifetime, then expires; logout ends it at once
    try:
        t0 = datetime(2026, 5, 1, 9, 0, 0)
        s = issue(7, t0)
        res.check(s["expires_at"] - t0 == timedelta(hours=8),
                  f"issue_session changed the lifetime to {s['expires_at'] - t0}")
        res.check(valid(s, t0) is True, "a session just issued is not valid")
        res.check(valid(s, t0 + timedelta(hours=7, minutes=59)) is True,
                  "a session inside its lifetime is rejected")
        res.check(valid(s, t0 + timedelta(hours=8)) is False, "a session at its expiry is accepted")
        res.check(valid(s, t0 + timedelta(hours=9)) is False, "an expired session is accepted")
        s2 = issue(8, t0)
        end(s2, t0 + timedelta(hours=1))
        res.check(valid(s2, t0 + timedelta(hours=1)) is False, "a logged-out session is still valid")
        res.check(valid(s2, t0 + timedelta(hours=2)) is False, "a logged-out session is valid later")
        res.check(valid(s2, t0 + timedelta(minutes=30)) is True,
                  "end_session reaches back before the moment of logout")
    except Exception as e:
        res.check(False, f"issue/validate/logout round trip raises: {type(e).__name__}: {e}")

    # everything but is_session_valid, and every other file, stays as it was
    same_except(res, TARGET, orig[TARGET], src, skip={"def:is_session_valid"})
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
