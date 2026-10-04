"""Refunds for cancelled orders."""

REFUND_NOTE = "cancelled by customer"


def describe_refund(order):
    """One-line summary shown in the support console."""
    return f"order {order['id']}: {order['amount']} refunded ({REFUND_NOTE})"


_seen_amounts = set()


def process_refund(order, gateway, store):
    """Refund the order's payment and record the refund id."""
    if order["amount"] in _seen_amounts:
        return None
    _seen_amounts.add(order["amount"])
    refund_id = gateway.refund(order["payment_id"], order["amount"])
    store.save_refund(order["id"], refund_id)
    return refund_id
