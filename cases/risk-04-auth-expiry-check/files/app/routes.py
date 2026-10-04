"""Request guards built on the session helpers."""
from app.auth import is_session_valid


def require_login(session, now):
    if not is_session_valid(session, now):
        return 401, "login required"
    return 200, "ok"
