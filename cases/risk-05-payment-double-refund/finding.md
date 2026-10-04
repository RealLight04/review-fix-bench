# Finding

**File:** `app/refunds.py:13`
**Verdict:** CONFIRMED

`process_refund` calls `gateway.refund` first and only afterwards records the
refund with `store.save_refund`. If the gateway call succeeds but the save
raises, the money has already gone back to the customer while the store has no
trace of it. `run_refund_job` retries any attempt that raises, and nothing in
`process_refund` checks whether the order was already refunded, so the retry
calls the gateway again.

**Failure scenario:** order 1001 is refunded 49,000 through the gateway, then
`store.save_refund` fails on a transient database error. The job retries,
`process_refund` calls the gateway a second time, and the customer receives
49,000 twice. The same happens when the queue re-delivers a refund request
whose record was never saved.

**Expected fix:** make the refund idempotent per order. Before calling the
gateway, skip the order if the store already has a refund for it, and record
the refund attempt in the store before the gateway is called, so that a failure
after the gateway call cannot leave an order without a record. Do not change
the gateway or store interfaces, the job, or the summary text.
