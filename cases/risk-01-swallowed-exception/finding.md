# Finding

**File:** `app/alerts.py:19`
**Verdict:** CONFIRMED

`dispatch` sends the notification, then marks the row as alerted, then commits.
The `except` around the whole block swallows any failure and moves on to the
next row, so when the commit fails the mark is never saved while the message
has already gone out.

**Failure scenario:** a transient DB lock during commit. The user receives the
alert, the row is never marked `alerted=True`, and the next run 20 minutes
later sends the identical alert again. Repeats every cycle until the write
succeeds.

**Expected fix:** the sent/marked state must not diverge from what was actually
delivered. Do not change the notification text or add a new dependency.
