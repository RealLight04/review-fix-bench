# First measurement

Run between 30 September and 2 October 2026. Every number below comes from `raw.json` in this folder, one row
per run.

## What was run

Nine cases, three models (Haiku, Sonnet, Opus), three runs each, in two separate experiments.

Fixing. 81 runs. Each run was a fresh subagent on one model, started in a freshly prepared workdir, given the
output of `show <case>` and told to fix that finding only. Then `verify` judged the workdir. This is the
"fixing at one tier" mode from the README, so it measures whether each model can do the work, not the skill's
orchestration.

Grading. 81 runs. Each run was a fresh subagent on one model, given the skill's rubric table verbatim, the
finding (plus the quoted `CLAUDE.md` for `risk-03`), told not to read any files and to answer with one tier.
The answer was compared with `expected.json`. The model column below is the model that did the grading.

Neither experiment ran the full skill. Grading here is the rubric alone, so it does not test the skill's
filtering, grouping, or its habit of reading `CLAUDE.md` itself.

## Fixing: did the fix land and stay in scope

| case | Haiku | Sonnet | Opus |
|---|---|---|---|
| mech-01-dead-file | 3/3 | 1/3 | 3/3 |
| mech-02-unused-import | 3/3 | 3/3 | 3/3 |
| mech-03-typo-constant | 3/3 | 3/3 | 3/3 |
| ord-01-wrong-operator | 3/3 | 3/3 | 3/3 |
| ord-02-missing-none-check | 3/3 | 3/3 | 3/3 |
| ord-03-unstable-key | 3/3 | 3/3 | 3/3 |
| risk-01-swallowed-exception | 0/3 | 2/3 | 3/3 |
| risk-02-kill-by-path | 3/3 | 3/3 | 3/3 |
| risk-03-paired-schema | 3/3 | 3/3 | 3/3 |
| total | 24/27 | 24/27 | 27/27 |

The six failures, with the verifier's message:

- Haiku, `risk-01`, three runs. One persisted `alerted=True` even though sending raised. Two sent the same alert
  twice after a failed commit. These are real behavior failures, and this is the one case where the cheap model
  clearly could not do the work.
- Sonnet, `risk-01`, one run. The only failure was the scope rule: it added a top-level helper `_rollback` the
  finding did not ask for. The behavior probes were not what failed. A reviewer might accept that fix, so treat
  this as a verifier that is stricter than a human, not as a broken fix.
- Sonnet, `mech-01`, two runs. `templates/watchlist.html` still existed in both. In one run the permission
  classifier in the subagent's session denied the delete twice, on the first attempt and on the rerun. In the
  other the rerun's subagent reported success while the file was still there, and I did not investigate why. The
  first says more about the harness than about whether Sonnet can delete a file. The second is the reason the
  skill verifies at every tier: a subagent's self-report is not evidence.

Four `mech-01` runs (three Sonnet, one Opus) were denied the delete the first time and were rerun once. The
table counts the rerun. Leaving out the run that was denied twice, Sonnet would be 24/26 overall. The table
shows the raw count.

## Grading: does the rubric put each case in the expected tier

| case | expected | Haiku | Sonnet | Opus |
|---|---|---|---|---|
| mech-01-dead-file | Mechanical | 3/3 | 3/3 | 3/3 |
| mech-02-unused-import | Mechanical | 3/3 | 3/3 | 3/3 |
| mech-03-typo-constant | Mechanical | 3/3 | 3/3 | 3/3 |
| ord-01-wrong-operator | Ordinary | 2/3 | 3/3 | 3/3 |
| ord-02-missing-none-check | Ordinary | 3/3 | 3/3 | 1/3 |
| ord-03-unstable-key | Ordinary | 0/3 | 2/3 | 0/3 |
| risk-01-swallowed-exception | High-risk | 3/3 | 3/3 | 3/3 |
| risk-02-kill-by-path | High-risk | 0/3 | 0/3 | 3/3 |
| risk-03-paired-schema | High-risk | 1/3 | 0/3 | 1/3 |
| total | | 18/27 | 20/27 | 20/27 |

Agreement was 58 of 81 overall. By expected tier: Mechanical 27/27, Ordinary 17/27, High-risk 14/27.

The mistakes ran both ways. High-risk graded as Ordinary 13 times (`risk-02` six, `risk-03` seven). Ordinary
graded as High-risk 9 times (`ord-03` seven, `ord-02` two, both of the latter from Opus). Ordinary graded as
Mechanical once. Grading up only costs money. Grading down is the direction the skill is meant to avoid, and it
happened in 13 of 27 high-risk gradings.

## What this does and does not show

On these nine cases, the cheaper models did the work wherever the rubric would have sent them. Mechanical
findings were graded Mechanical every time and Haiku fixed all of them. The one case where Haiku failed
(`risk-01`) was graded High-risk in all nine grading runs, so the skill would have sent it to Opus, which passed
3/3.

Taking each grader's answer, picking the model its tier maps to, and using that model's pass rate on that case
gives an expected 81 of 81 passes. Counting each finding at the mean tokens of its assigned model times the price
ratio (1 : 2 : 4, taken from the list input prices of $1, $2 and $4 per million tokens), the routed total is 54% of sending everything to Opus (56% on the price ratio alone). That is
an estimate built from the tables above, not an end-to-end run, and it never exercises the retry and escalation
path.

Reasons not to read more into it:

- The grading mistakes may say as much about the rubric and the labels as about the graders. Graders called
  `risk-03` Ordinary because it is a column addition with a documented two-file procedure, which is close to the
  rubric's own Ordinary example "schema-safe column addition". `risk-02` is Ordinary to most graders for a
  similar reason, and all three models fixed both cases correctly. The expected tiers for those two are my
  judgment, and these results are some evidence they are set too high. The tier table remains a hypothesis.
- Nine synthetic cases, three runs per cell, written by the person who wrote the verifiers. One failure moves a
  cell by a third.
- The verifiers are heuristics (see the README) and the fix prompt is a stand-in for the skill's real
  delegation prompt.

## Tokens

Mean subagent tokens per run:

| | Haiku | Sonnet | Opus |
|---|---|---|---|
| fixing | 33.9k | 41.2k | 41.6k |
| grading | 35.5k | 44.5k | 45.8k |

These are close to each other because each subagent carries roughly 30k tokens of fixed startup context (system
prompt and tool definitions) before it reads the finding. Almost all of the grading number is that overhead.
Grading inside the orchestrating session, as the skill does, adds only the finding and the rubric. So these
numbers cannot answer the first open question in review-fix's README, whether grading each finding costs more
than the cheaper fix models save. That is still open, and a fair measurement has to grade in-session.

## Raw data

`raw.json` has one row per fixing run, each carrying the grading answer from the matched grading run (same case,
same model, same slot): case, model, run number, verifier pass/fail and first failure message, fix tokens, tier
the grader gave, grading tokens.
