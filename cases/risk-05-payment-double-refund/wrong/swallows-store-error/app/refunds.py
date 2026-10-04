"""Refunds for cancelled orders."""

REFUND_NOTE = "cancelled by customer"


def describe_refund(order):
    """One-line summary shown in the support console."""
    return f"order {order['id']}: {order['amount']} refunded ({REFUND_NOTE})"


def process_refund(order, gateway, store):
    """Refund the order's payment and record the refund id."""
    refund_id = gateway.refund(order["payment_id"], order["amount"])
    try:
        store.save_refund(order["id"], refund_id)
    except Exception:
        pass
    return refund_id
