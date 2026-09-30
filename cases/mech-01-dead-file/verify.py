import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, untouched


def verify(res, case_dir, work, orig, cur):
    res.check("templates/watchlist.html" not in cur,
              "templates/watchlist.html still exists")
    untouched(res, orig, cur, allowed={"templates/watchlist.html"})


main(verify)
