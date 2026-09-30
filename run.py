"""Benchmark runner. Python 3.9+, standard library only (git is used by `prepare`).

    python run.py prepare <case> [workdir]   # copy the starting files into a fresh git repo
    python run.py show    <case>             # print the finding to hand over
    python run.py verify  <case> <workdir>   # judge the result
    python run.py selftest                   # sanity-check every case

`prepare` only writes into a directory that does not exist yet or is empty, and
never deletes anything. Without a workdir it makes a fresh temporary one. The
workdir must not sit inside this repository, because the answers live here.

`selftest` is the one to run after adding or editing a case. For every case it
checks that the verifier
  - FAILS on the untouched starting state,
  - PASSES on `reference/` (the intended fix),
  - PASSES on every `alt/<name>/` (other correct fixes), and
  - FAILS on every `wrong/<name>/` (plausible fixes that are not good enough).
A case with none of the last two is untested for false accepts and false rejects.

The fix step itself is not scripted: the point is to measure Claude Code
sessions and subagents at a given model tier. See README.md.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"

TIERS = ("mechanical", "ordinary", "high-risk")
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
VERIFY_TIMEOUT = 60


def case_dir(name: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        sys.exit(f"no such case: {name}")
    d = CASES / name
    if not (d / "files").is_dir():
        sys.exit(f"no such case: {name}")
    return d


def real(path: str | Path) -> Path:
    """Absolute path with links resolved, case folded, and Windows extended-length
    prefixes removed, so two spellings of one folder compare equal."""
    p = os.path.realpath(os.path.abspath(str(path)))
    for prefix in ("\\\\?\\UNC\\", "\\\\?\\"):
        if p.startswith(prefix):
            p = ("\\\\" if "UNC" in prefix else "") + p[len(prefix):]
    return Path(os.path.normcase(p))


def is_inside(path: Path, parent: Path) -> bool:
    try:
        real(path).relative_to(real(parent))
        return True
    except ValueError:
        return False


def prepare(name: str, workdir: str | None = None) -> int:
    src = case_dir(name) / "files"
    if workdir is None:
        dst = Path(tempfile.mkdtemp(prefix="scratch-"))
    else:
        spelled = str(workdir).replace("/", "\\")
        dst = Path(workdir).resolve()
        # `real` also unwraps the \\?\UNC\host\share spelling, so a network path cannot
        # hide behind an extended-length prefix.
        if str(real(spelled)).startswith("\\\\") or str(real(dst)).startswith("\\\\"):
            sys.exit("refusing: network paths are not accepted; use a local directory")
        if dst.parent == dst:
            sys.exit(f"refusing: {dst} is a drive or filesystem root")
        if is_inside(dst, ROOT):
            sys.exit(f"refusing: {dst} is inside this repository, next to the answers")
        if dst.exists() and (not dst.is_dir() or any(dst.iterdir())):
            sys.exit(f"refusing: {dst} already exists and is not empty. "
                     "Pass a new or empty directory, or omit it for a temporary one.")
    shutil.copytree(src, dst, dirs_exist_ok=True)
    # The skill under test starts by reading `git status`, so give it a repo whose
    # starting state is committed. A throwaway identity keeps this off your git config,
    # and signing is switched off so a global gpgsign setting cannot block the commit.
    git = ["git", "-C", str(dst), "-c", "user.name=dev", "-c", "user.email=dev@example.invalid",
           "-c", "commit.gpgsign=false"]
    try:
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "starting state"]):
            subprocess.run(git + cmd, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"warning: could not create a git repo in the workdir: {e}", file=sys.stderr)
    print(f"prepared {name} -> {dst}")
    return 0


def show(name: str) -> int:
    print((case_dir(name) / "finding.md").read_text(encoding="utf-8"))
    return 0


def run_verifier(name: str, work: Path) -> subprocess.CompletedProcess:
    """Run the case's verifier in a child process whose working directory is a fresh
    empty folder. A run counts as a pass only if it says PASS (see `passed`): an exit
    code of 0 alone can be forged by code that calls exit()."""
    with tempfile.TemporaryDirectory(prefix="review-fix-verify-") as cwd:
        try:
            return subprocess.run(
                [sys.executable, str(case_dir(name) / "verify.py"), str(work)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=CHILD_ENV, timeout=VERIFY_TIMEOUT, cwd=cwd, stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess([], 1, f"FAIL: verifier did not finish in {VERIFY_TIMEOUT}s\n", "")


def passed(proc: subprocess.CompletedProcess) -> bool:
    return proc.returncode == 0 and any(l.strip() == "PASS" for l in proc.stdout.splitlines())


def verify(name: str, workdir: str) -> int:
    proc = run_verifier(name, Path(workdir).resolve())
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode == 0 and not passed(proc):
        print("FAIL: the verifier exited without reporting PASS")
        return 1
    return proc.returncode


def apply_overlay(overlay: Path, work: Path) -> None:
    """Copy overlay/ onto work. overlay/DELETE lists relative paths to remove."""
    for f in overlay.rglob("*"):
        if f.is_file() and f.name != "DELETE":
            target = work / f.relative_to(overlay)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
    delete = overlay / "DELETE"
    if delete.is_file():
        for line in delete.read_text(encoding="utf-8").splitlines():
            if line.strip():
                (work / line.strip()).unlink()


def last_line(proc: subprocess.CompletedProcess) -> str:
    return (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]


def first_fail(proc: subprocess.CompletedProcess) -> str:
    return next((l for l in proc.stdout.splitlines() if l.startswith("FAIL:")), last_line(proc))


def with_overlay(name: str, overlay: Path | None) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(case_dir(name) / "files", work)
        if overlay is not None:
            apply_overlay(overlay, work)
        return run_verifier(name, work)


def check_case(name: str) -> list[str]:
    """Everything wrong with a case, or an empty list."""
    d = case_dir(name)
    problems: list[str] = []
    try:
        tier = json.loads((d / "expected.json").read_text(encoding="utf-8")).get("tier")
    except (OSError, ValueError) as e:
        return [f"expected.json missing or unreadable: {e}"]
    if tier not in TIERS:
        problems.append(f"expected.json tier {tier!r} is not one of {TIERS}")
    finding = (d / "finding.md").read_text(encoding="utf-8")
    if re.search(r"\btier\b", finding, re.I):
        problems.append("finding.md mentions a tier; the expected answer must stay in expected.json")
    if not (d / "reference").is_dir():
        return problems + ["no reference/ fix"]

    proc = with_overlay(name, None)
    if passed(proc):
        problems.append("verifier passes before any fix")
    elif "FAIL:" not in proc.stdout:
        # A crash also exits non-zero. Counting it as a proper FAIL would hide a broken case.
        problems.append(f"crashed on the starting state instead of reporting FAIL: {last_line(proc)}")

    proc = with_overlay(name, d / "reference")
    if not passed(proc):
        problems.append(f"verifier rejects the reference fix: {first_fail(proc)}")

    for kind, want_pass in (("alt", True), ("wrong", False)):
        base = d / kind
        for variant in sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []:
            proc = with_overlay(name, variant)
            if want_pass and not passed(proc):
                problems.append(f"alt/{variant.name} is a correct fix but was rejected: {first_fail(proc)}")
            if not want_pass and passed(proc):
                problems.append(f"wrong/{variant.name} is not a good fix but passed")
            if not want_pass and not passed(proc) and "FAIL:" not in proc.stdout:
                problems.append(f"wrong/{variant.name} crashed the verifier: {last_line(proc)}")
    return problems


def selftest() -> int:
    names = sorted(p.name for p in CASES.iterdir() if p.is_dir())
    print(f"self-testing {len(names)} cases\n")
    bad = []
    for name in names:
        problems = check_case(name)
        d = case_dir(name)
        extra = sum(len(list((d / k).iterdir())) for k in ("alt", "wrong") if (d / k).is_dir())
        if problems:
            bad.append(name)
            print(f"  BROKEN  {name}")
            for p in problems:
                print(f"            {p}")
        else:
            print(f"  ok      {name}  (+{extra} alt/wrong variants)")
    print()
    if bad:
        print(f"{len(bad)} broken case(s): {', '.join(bad)}")
        return 1
    print("all cases behave: fail unfixed, pass the reference and alternatives, fail the wrong fixes")
    return 0


def usage() -> int:
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args == ["selftest"]:
        raise SystemExit(selftest())
    if len(args) in (2, 3) and args[0] == "prepare":
        raise SystemExit(prepare(*args[1:]))
    if len(args) == 2 and args[0] == "show":
        raise SystemExit(show(args[1]))
    if len(args) == 3 and args[0] == "verify":
        raise SystemExit(verify(args[1], args[2]))
    raise SystemExit(usage())
