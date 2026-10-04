# Finding

**File:** `app/auth.py:21`
**Verdict:** CONFIRMED

`is_session_valid` compares the session's expiry timestamp with the current
time the wrong way round: it returns `session["expires_at"] <= now`, which is
true once the expiry has passed. Sessions that have expired are treated as
valid, and sessions that are still live are rejected.

**Failure scenario:** a user logs in at 09:00, so `issue_session` sets
`expires_at` to 17:00. At 18:00 `is_session_valid(session, now)` evaluates
`17:00 <= 18:00`, returns `True`, and `require_login` lets the request through
although the session expired an hour ago. At 10:00 the same session evaluates
`17:00 <= 10:00`, returns `False`, and the user is asked to log in again.
A session closed with `end_session` is likewise still accepted later on.

**Expected fix:** a session is valid only while `now` is strictly before
`expires_at`; at the instant of expiry it is already expired. A `None` session
must keep returning `False`. Keep the signature of `is_session_valid`, and do
not change how `issue_session` or `end_session` work.
