# Finding

**File:** `app/screener.py:12`
**Verdict:** CONFIRMED

The 8-point trend template that `passes_trend_template` implements requires
the 150-day MA to be **above** the 200-day MA. The function checks
`ma150 < ma200`, which is that condition reversed.

**Failure scenario:** every stock whose 150-day MA sits below its 200-day MA
passes this check, and every stock in a genuine uptrend fails it. The screener
returns precisely the wrong set.

**Expected fix:** correct the comparison. Do not change the other seven checks,
the thresholds, or the return shape.
