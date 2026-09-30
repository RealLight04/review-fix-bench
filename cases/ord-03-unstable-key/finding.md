# Finding

**File:** `app/dedupe.py:19`
**Verdict:** CONFIRMED

`batch_keys` builds each row's key from the title alone when no date is
present, so rows that share a title collide. The upstream listing page carries
five entries titled exactly "샘플 콘서트", distinguished only by date.

**Failure scenario:** the date element's CSS class changes upstream, every date
comes back empty, all five rows collapse to one key, and the UNIQUE constraint
on `source_key` raises on insert. That takes down the whole collection run, not
just the one source.

**Expected fix:** make the dateless fallback unique per row. Keep the key
format for rows that DO have a date exactly as it is, so existing stored rows
still match.
