# review-fix-bench

Nine small cases for [review-fix](https://github.com/RealLight04/review-fix-skill), a Claude Code skill
that grades code review findings by risk and hands each fix to a model tier. Each case is a finding with a
known correct fix. They exist to test two things review-fix's README claims but has not measured:

1. **Grading.** Does the skill put each finding in the tier a careful reviewer would? Compare the tier it
   reports with `cases/<name>/expected.json`.
2. **Fixing.** At a given model tier, does the fix land and stay inside the finding's scope? `verify.py`
   checks both halves: did the intended change happen, and did anything else change.

It does **not** measure token cost, neither the grading overhead nor the savings from cheaper fix models.
Read those off `/cost` or your usage page for each run and write them into your results. The runner does not
collect them.

No results are published yet.

## Why this is a separate repository

The answers (`expected.json`, `reference/`, the verifiers) must not be readable by the session being tested.
review-fix installs by cloning its repository into `~/.claude/skills/review-fix`, and Claude Code tells a
running skill where that folder is. Keeping the benchmark here keeps the answers out of it.

For the same reason, never run the tested session inside this repository or in a folder whose path contains a
case name (`mech-`, `ord-` and `risk-` prefixes give away the expected tier).

## Requirements

Python 3.9 or later (developed and tested on 3.11) and git. Nothing to install: the fixtures import FastAPI or SQLAlchemy in places, but the
verifiers only read those as text.

## Safety

- `prepare` only writes into a directory that does not exist yet or is empty. It never deletes anything. It
  refuses a directory inside this repository (however the path is spelled), a network path, and a drive root.
  With no workdir it creates a fresh temporary directory.
- `verify` runs code that a model edited. **This is not sandboxed.** The verifier imports the edited file with
  a short allow-list of pure standard modules (`re`, `datetime`, `typing`, `collections`, `itertools`,
  `functools`, `hashlib`, `math`, `string`, `enum`, `dataclasses`); anything else, including `logging`,
  `sqlite3`, `os` and `importlib`, is replaced by an inert stand-in. It also blocks `open`, gives each run 60
  seconds and an empty temporary folder as its working directory, and counts a run as a pass only if it prints
  `PASS`, so a fix that calls `exit()` does not slip through. That stops accidents and lazy shortcuts. It does
  not stop code that is trying to escape or cheat: Python has too many routes from an allowed module back to
  `os`, and code in the same process can also forge the verdict (for example by printing `PASS` and exiting).
  Treat a PASS as meaningful only for code from a model that is not adversarial, run `verify` in a throwaway
  VM or container, and only on workdirs you prepared yourself.

## Commands

```
python run.py selftest                   # check every case: see "Self-test" below
python run.py prepare <case> [workdir]   # copy a case's starting files into a fresh git repo
python run.py show <case>                # print the finding to hand over
python run.py verify <case> <workdir>    # PASS, or FAIL with reasons
```

## Protocol

1. Install review-fix the normal way (`git clone` it into `~/.claude/skills/review-fix`, or `npx skills add`).
2. `python run.py prepare <case>` and note the workdir it prints. The workdir is a git repository with the
   starting state committed, because the skill begins by reading `git status`.
3. Open Claude Code in that workdir and measure one of:
   - **Grading.** Run `/review-fix` with the output of `show <case>` as the argument, and add "treat this as a
     batch of one: state the tier you chose before fixing". A single finding is normally a reason not to use
     the skill, so the instruction is what makes it report a tier. Record the tier and the model it used.
   - **Fixing at one tier.** Start the session on that model (for example `claude --model haiku`), paste the
     output of `show <case>`, and ask for that fix only.
4. `python run.py verify <case> <workdir>`.
5. Record the result. Run each case several times per model, because one run says little.

A results table can be as simple as:

| date | case | mode | model | tier reported | verify | tokens (optional) | notes |
|---|---|---|---|---|---|---|---|

## Cases

| Case | What the finding is about |
|---|---|
| `mech-01-dead-file` | A template nothing routes to anymore |
| `mech-02-unused-import` | Two imports the module never uses |
| `mech-03-typo-constant` | A typo in one user-facing message |
| `ord-01-wrong-operator` | One comparison in a filter reversed |
| `ord-02-missing-none-check` | An unparseable date crashes the whole run |
| `ord-03-unstable-key` | Rows without a date collide on the same key |
| `risk-01-swallowed-exception` | An alert goes out before the commit that records it |
| `risk-02-kill-by-path` | Test cleanup kills the production server on another port |
| `risk-03-paired-schema` | A column change that `CLAUDE.md` says must touch two files |

## How the verifiers judge

Most verifiers load the edited file, call the function the finding is about, and check behavior at the
edges the finding names (the `mech-*` cases and the model half of `risk-03` are only parsed, never run). It also compares every other top-level definition and statement in the file with the
original structurally (parsed code, docstrings included), so a fix that renames a variable or rewrites a
docstring outside the fixed function fails. Inside the fixed function, the checks are the behavior probes plus,
where the finding names exact things to keep (`ord-01`'s other seven checks and their thresholds), a structural
comparison of the rest of that function. Keys that must be stable are also checked for calls that differ
between runs (`hash()`, `id()`, clocks, random, uuid). Files your tools create on their own (`.git`,
`.claude`, `__pycache__`, tool caches) are ignored.

These are heuristics. A very different but valid fix can be rejected, and a bad fix the checks did not
anticipate can pass. When you find one, add it as an `alt/` or `wrong/` variant (below) and fix the verifier.

## Self-test

`python run.py selftest` runs every case against:

- the untouched starting state, which must FAIL;
- `reference/`, the intended fix, which must PASS;
- each `alt/<name>/`, another correct fix, which must PASS;
- each `wrong/<name>/`, a plausible fix that is not good enough, which must FAIL.

Run it after adding or editing a case. It also rejects a `finding.md` that mentions a tier.

## Adding a case

```
cases/<name>/
  files/          the starting state, copied into the workdir
  finding.md      what the reviewer reported; never the expected tier
  expected.json   {"tier": "mechanical" | "ordinary" | "high-risk"}
  verify.py       uses harness.main; checks the fix landed and nothing else changed
  reference/      the intended fix, overlaid on files/; a DELETE file lists paths to remove
  alt/<name>/     other correct fixes, same overlay format
  wrong/<name>/   plausible but insufficient fixes, same overlay format
```

## License

[MIT](LICENSE)
