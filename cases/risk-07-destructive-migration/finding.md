# Finding

**File:** `migrations/0007_split_name.py:5`
**Verdict:** CONFIRMED

`upgrade` drops the `full_name` column from `users` and only then adds
`first_name` and `last_name`. The two new columns start out empty and nothing
copies the old values into them, so the name stored for every existing user is
destroyed by the migration.

**Failure scenario:** a database holds the user `(1, 'a@example.com', 'Kim Minsu')`.
After `upgrade(conn)` runs, the row still exists but `first_name` and
`last_name` are both NULL and the name `Kim Minsu` is nowhere in the database.
Every existing user loses their name.

**Expected fix:** add `first_name` and `last_name`, copy the data by splitting
`full_name` (first word into `first_name`, the rest into `last_name`; a
one-word name still keeps its value), and only then drop `full_name` (or leave
it in place). The other columns and rows must stay as they are.
