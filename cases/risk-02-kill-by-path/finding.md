# Finding

**File:** `scripts/smoke.py:24`
**Verdict:** CONFIRMED

`stop_previous` kills every process whose executable path contains the
project's venv, regardless of which port it serves. The production server runs
from that same venv on port 9001; this script's default test port is 9000.

**Failure scenario:** a developer runs the smoke script to check a local
change. Before binding its own port, it kills the production server on 9001,
which nothing restarts, then serves a test instance on 9000. The site stays
down until someone notices and restarts it by hand.

**Expected fix:** stop only what is actually bound to the port this script is
about to use. `list_listeners()` is already available and returns
`[(port, pid)]`. Keep the default port at 9000.
