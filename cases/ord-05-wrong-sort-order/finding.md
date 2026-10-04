# Finding

**File:** `app/feed.py:7`
**Verdict:** CONFIRMED

`latest_posts(posts, limit)` is meant to return the newest posts first, but it
sorts by `created_at` in ascending order and then takes the first `limit`
entries. The result is the oldest posts, oldest first, so the home feed shows
the stalest content.

**Failure scenario:** a feed has posts created at 100, 200, 300, 400 and 500
(epoch seconds). `latest_posts(posts, 3)` returns the posts created at 100, 200
and 300. The feed should show 500, 400 and 300, in that order.

**Expected fix:** sort descending by `created_at` so the newest comes first, then
take `limit`. Posts with the same `created_at` should keep their original relative
order. Leave `pinned_first` and every other function as they are.
