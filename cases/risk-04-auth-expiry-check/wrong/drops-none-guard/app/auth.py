"""Session handling for the web login."""
import hashlib
from datetime import timedelta

SESSION_TTL = timedelta(hours=8)


def issue_session(user_id, now):
    """Create a session for user_id that lasts SESSION_TTL from now."""
    raw = f"{user_id}:{now.isoformat()}"
    return {
        "user_id": user_id,
        "token": hashlib.sha256(raw.encode()).hexdigest(),
        "expires_at": now + SESSION_TTL,
    }


def is_session_valid(session, now):
    """True while the session has not expired."""
    return session["expires_at"] > now


def end_session(session, now):
    """Log out: expire the session immediately."""
    session["expires_at"] = now
    return session
