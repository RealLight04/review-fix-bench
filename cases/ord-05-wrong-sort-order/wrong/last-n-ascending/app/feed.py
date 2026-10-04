"""Home feed helpers. A post is a dict with id, title, created_at (epoch seconds), pinned."""


def latest_posts(posts, limit):
    """Newest posts first, at most `limit` of them."""
    ordered = sorted(posts, key=lambda p: p["created_at"])
    return ordered[-limit:]


def pinned_first(posts):
    """Pinned posts first, each group keeping its incoming order."""
    pinned = [p for p in posts if p.get("pinned")]
    rest = [p for p in posts if not p.get("pinned")]
    return pinned + rest
