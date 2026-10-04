"""Text rendering for feed rows."""


def post_line(post):
    """One line per post for the plain-text digest."""
    return f"#{post['id']} {post['title']}"
