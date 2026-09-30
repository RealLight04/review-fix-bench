# Finding

**File:** `templates/watchlist.html`
**Verdict:** CONFIRMED

`templates/watchlist.html` is dead. Nothing routes to it, no template links to
it, and the `/api/quote` endpoint its JavaScript calls no longer exists in
`app/routes.py`. The feature it belonged to was removed from the project.

**Failure scenario:** the page stays reachable in every checkout, dead code
that calls a route which returns 404 and that the project already chose to
delete.

**Expected fix:** delete the file. Nothing else.
