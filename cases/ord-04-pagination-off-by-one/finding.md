# Finding

**File:** `app/listing.py:17`
**Verdict:** CONFIRMED

`page_count` divides the item count by the page size with floor division, so
a last page that is only partly filled is not counted. The list view uses
`page_count` to decide how many page links to show, so the items on that last
page can never be reached.

**Failure scenario:** a result list has 21 items and the page size is 10.
`page_count(21, 10)` returns 2, so the view offers pages 1 and 2 only and the
21st item, which `paginate(items, 3, 10)` would return, is not reachable.
The same happens with fewer items than one page: 5 items with a page size of
10 gives 0 pages, so the list looks empty.

**Expected fix:** `page_count` should count a partly filled last page as a
page, and still return 0 when there are no items. Keep the existing handling
of a page size of 0 or less, and keep `paginate` as it is.
