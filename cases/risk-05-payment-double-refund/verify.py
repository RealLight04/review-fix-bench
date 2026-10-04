import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/refunds.py"


class FakeGateway:
    """Counts every refund call; each call returns a new refund id."""

    def __init__(self):
        self.calls = []

    def refund(self, payment_id, amount):
        self.calls.append((payment_id, amount))
        return f"re_{len(self.calls)}"


class FakeStore:
    """One record per order id. The `fail_at`-th save_refund call raises, once."""

    def __init__(self, fail_at=None):
        self.rows = {}
        self.saves = 0
        self.fail_at = fail_at

    def get_refund(self, order_id):
        return self.rows.get(order_id)

    def save_refund(self, order_id, refund_id):
        self.saves += 1
        if self.saves == self.fail_at:
            raise RuntimeError("database is locked")
        self.rows[order_id] = refund_id


def order(order_id=1001, amount=49000):
    # a fresh dict each time, like an order reloaded from the database on every attempt
    return {"id": order_id, "payment_id": f"pay_{order_id}", "amount": amount}


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    if parse(res, TARGET, src) is None:
        return
    ns = run_module(res, TARGET, src)
    if ns is None:
        return
    process = ns.get("process_refund")
    if process is None:
        res.check(False, "process_refund was renamed or removed")
        return

    # 1) 어느 저장 단계에서 실패하든, 재시도와 재전달을 거쳐도 한 주문은 게이트웨이에 한 번만 간다
    for fail_at in (1, 2):
        gw, st = FakeGateway(), FakeStore(fail_at=fail_at)
        for _ in range(3):  # job retry after the failure, then queue re-delivery
            try:
                process(order(), gw, st)
            except Exception:
                pass
        res.check(len(gw.calls) == 1,
                  f"save failing at call {fail_at}: gateway was called {len(gw.calls)} times "
                  "for one order, expected exactly 1 (the customer is refunded twice)")
        res.check(st.get_refund(1001) is not None,
                  f"save failing at call {fail_at}: the order has no refund record afterwards")

    # 2) 이미 환불 기록이 있는 주문은 게이트웨이를 부르지 않는다
    gw, st = FakeGateway(), FakeStore()
    st.rows[1001] = "re_old"
    try:
        process(order(), gw, st)
        res.check(len(gw.calls) == 0, "an order that already has a refund was sent to the gateway again")
    except Exception as e:
        res.check(False, f"raises for an already refunded order: {type(e).__name__}: {e}")

    # 3) 정상 경로: 한 번 호출하고, 환불 번호를 돌려주고 기록한다
    gw, st = FakeGateway(), FakeStore()
    try:
        rid = process(order(), gw, st)
        res.check(gw.calls == [("pay_1001", 49000)], f"normal path gateway calls are wrong: {gw.calls!r}")
        res.check(rid == "re_1", f"normal path returned {rid!r}, expected the gateway's refund id 're_1'")
        res.check(st.get_refund(1001) == "re_1", f"refund id not recorded: {st.rows!r}")
    except Exception as e:
        res.check(False, f"broke the normal path: {type(e).__name__}: {e}")

    # 4) 같은 금액의 서로 다른 주문은 각각 환불된다
    gw, st = FakeGateway(), FakeStore()
    try:
        process(order(1, 30000), gw, st)
        process(order(2, 30000), gw, st)
        res.check(len(gw.calls) == 2 and st.get_refund(1) is not None and st.get_refund(2) is not None,
                  f"two different orders with the same amount were not both refunded: {gw.calls!r}")
    except Exception as e:
        res.check(False, f"raises on the same-amount probe: {type(e).__name__}: {e}")

    # process_refund 밖의 코드는 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"def:process_refund"}, imports="superset")
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
