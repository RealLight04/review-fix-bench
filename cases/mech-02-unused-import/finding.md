# Finding

**File:** `app/collector.py:1-3`
**Verdict:** CONFIRMED

`json` and `timedelta` are imported but never used anywhere in the module.

**Failure scenario:** noise. A reader scanning imports assumes the module does
JSON work and date arithmetic, and looks for code that does not exist.

**Expected fix:** remove the two unused imports. Leave every other import and
every line of logic alone.
