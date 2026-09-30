# Finding

**File:** `app/messages.py:4`
**Verdict:** CONFIRMED

`SUBSCRIBE_OK` reads "구독이 완료되었습니가." The ending is a typo for
"완료되었습니다."

**Failure scenario:** every subscriber sees a typo in the first message the
product sends them.

**Expected fix:** correct that one string. Do not touch the other messages,
do not "improve" their wording.
