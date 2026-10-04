"""Queue worker that refunds cancelled orders."""
from app.refunds import process_refund

MAX_ATTEMPTS = 3


def run_refund_job(order, gateway, store):
    """Refund one cancelled order, retrying when an attempt raises."""
    last_error = None
    for _ in range(MAX_ATTEMPTS):
        try:
            return process_refund(order, gateway, store)
        except Exception as e:
            last_error = e
    raise last_error
