# Finding

**File:** `app/sources/common.py:29`
**Verdict:** CONFIRMED

`parse_dates` returns `(None, None)` when the date text is unparseable, and
`build_show` immediately calls `.isoformat()` on the first element without
checking. Listings whose date element is missing or in an unexpected format
crash the whole collection run.

**Failure scenario:** one ticket listing renders its date as "추후 공지"
(to be announced). `parse_dates` returns `(None, None)`,
`None.isoformat()` raises `AttributeError`, and the exception escapes
`build_show`, aborting collection for every remaining listing in the batch.

**Expected fix:** handle the `None` case so the row is still produced with a
null date. Keep the source_key format unchanged for rows that do have a date,
because changing it would orphan existing rows.
