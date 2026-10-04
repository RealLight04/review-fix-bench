"""Refunds for cancelled orders."""

REFUND_NOTE = "cancelled by customer"


def describe_refund(order):
    """One-line summary shown in the support console."""
    return f"order {order['id']}: {order['amount']} refunded ({REFUND_NOTE})"


def process_refund(order, gateway, store):
    """Refund the order's payment and record the refund id."""
    order_id = order["id"]
    if store.get_refund(order_id):
        # already refunded, or a refund is in flight
        return None
    store.save_refund(order_id, "pending:" + str(order["payment_id"]))
    refund_id = gateway.refund(order["payment_id"], order["amount"])
    store.save_refund(order_id, refund_id)
    return refund_id
