# Finding

**File:** `app/signup.py:31`
**Verdict:** CONFIRMED

When a signup form fails validation, `register` logs the entire submitted form
at ERROR level with `logger.error("signup validation failed: %s", user)`. The
dict holds the person's name, email address, phone number and date of birth, so
all of those values are written into the application log.

**Failure scenario:** someone mistypes their date of birth. The log now holds
a line with their full name, email, phone number and date of birth next to the
error. Those log files are shipped to the log vendor and are readable by the
whole team, so personal values end up in places they were never meant to be,
and they stay there for as long as the logs are kept.

**Expected fix:** keep logging the failed signup, but log only which fields
failed (or an id), never the submitted values. The returned result and the
success-path log line must stay as they are.
