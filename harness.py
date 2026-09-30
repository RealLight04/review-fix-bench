"""Shared helpers for benchmark case verifiers.

Each case ships a pristine `files/` directory (the starting state) and a
`verify.py`. A run copies `files/` to a scratch workdir, lets one model fix the
finding there, then runs `verify.py <workdir>`.

A verifier answers two questions, and both matter:

  1. Did the intended fix land?
  2. Did anything ELSE change?

Question 2 is half the point. A model that fixes the bug and also "helpfully"
reformats three other files has not done the job: the skill under test tells
subagents to fix one finding only, so scope creep is a failure, not a bonus.

Running model-edited code is NOT sandboxed. `run_module` below narrows what that
code can import and call, which stops accidents and lazy shortcuts, but a
determined program can still escape it. Run verifiers in a throwaway VM or
container.
"""
from __future__ import annotations

import ast
import builtins
import logging
import sys
from pathlib import Path

# Things a session or its tools create on their own. They are not part of the fix.
IGNORED_DIRS = {".git", ".claude", "__pycache__", ".pytest_cache", ".ruff_cache",
                ".mypy_cache", ".venv", "node_modules"}
IGNORED_FILES = {"review-fix-pending.md"}


class Result:
    def __init__(self) -> None:
        self.problems: list[str] = []

    def check(self, ok: bool, msg: str) -> None:
        if not ok:
            self.problems.append(msg)

    def finish(self) -> None:
        if self.problems:
            for p in self.problems:
                print(f"FAIL: {p}")
            sys.exit(1)
        print("PASS")
        sys.exit(0)


def read_text(path: Path) -> str:
    """utf-8, tolerating the BOM that PowerShell 5.1 writes by default."""
    return path.read_text(encoding="utf-8-sig")


def read_tree(root: Path) -> dict[str, str]:
    """{relative path: text} for every relevant file under root."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.name in IGNORED_FILES or f.suffix == ".pyc":
            continue
        rel = f.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        try:
            out[rel.as_posix()] = read_text(f)
        except UnicodeDecodeError:
            out[rel.as_posix()] = "<binary>"
    return out


def paths(case_dir: Path, work: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(original, current) as {relative path: text}. Missing files are absent."""
    return read_tree(case_dir / "files"), read_tree(work)


def untouched(res: Result, orig: dict[str, str], cur: dict[str, str],
              allowed: set[str]) -> None:
    """Every file outside `allowed` must be identical and present, and no new
    files may appear. Line endings are normalized so a CRLF checkout doesn't
    read as scope creep."""
    def norm(s: str) -> str:
        return s.replace("\r\n", "\n")

    for rel, text in orig.items():
        if rel in allowed:
            continue
        if rel not in cur:
            res.check(False, f"deleted a file it was not asked to touch: {rel}")
        elif norm(cur[rel]) != norm(text):
            res.check(False, f"modified a file it was not asked to touch: {rel}")
    for rel in cur:
        if rel not in orig and rel not in allowed:
            res.check(False, f"added an unrequested file: {rel}")


# --- comparing code structurally ------------------------------------------

def _top_key(node: ast.stmt, index: int) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return f"def:{node.name}"
    if isinstance(node, ast.Assign) and len(node.targets) == 1 \
            and isinstance(node.targets[0], ast.Name):
        return f"assign:{node.targets[0].id}"
    return f"stmt:{index}"


def parse(res: Result, name: str, src: str) -> ast.Module | None:
    try:
        return ast.parse(src)
    except SyntaxError as e:
        res.check(False, f"{name} no longer parses: {e}")
        return None


def import_bindings(tree: ast.Module) -> set[tuple]:
    """Every (module, name, alias) an import statement binds, at any depth."""
    out: set[tuple] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update((None, a.name, a.asname) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.update((node.module, a.name, a.asname) for a in node.names)
    return out


def same_except(res: Result, name: str, orig_src: str, cur_src: str,
                skip: set[str], imports: str = "exact") -> None:
    """Every top-level statement whose key is not in `skip` must be structurally
    identical to the original. Keys: `def:<name>`, `assign:<name>`; comments and
    formatting may differ, docstrings and code may not.

    Top-level imports are handled apart from the other statements. With
    `imports="exact"` they must not change; with `"superset"` a fix may add imports
    but must keep every original one; with `"skip"` they are not compared."""
    a, b = ast.parse(orig_src), parse(res, name, cur_src)
    if b is None:
        return

    def index(mod: ast.Module) -> dict[str, str]:
        out: dict[str, str] = {}
        for i, node in enumerate(mod.body):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                out[_top_key(node, i)] = ast.dump(node)
        return out

    ia, ib = index(a), index(b)
    for key, dump in ia.items():
        if key in skip:
            continue
        if key not in ib:
            res.check(False, f"{name}: `{key}` was removed or renamed")
        elif ib[key] != dump:
            res.check(False, f"{name}: `{key}` was changed but the finding did not ask for that")
    for key in ib:
        if key not in ia and key not in skip:
            res.check(False, f"{name}: added top-level `{key}` that the finding did not ask for")

    before, after = import_bindings(a), import_bindings(b)
    if imports == "exact":
        res.check(before == after, f"{name}: the imports changed")
    elif imports == "superset":
        res.check(before <= after, f"{name}: an existing import was removed or changed")


_NONDETERMINISTIC_NAMES = {"hash", "id", "input"}
_NONDETERMINISTIC_ATTRS = {"uuid1", "uuid4", "today", "now", "utcnow", "random", "randint",
                           "randrange", "token_hex", "time", "monotonic", "perf_counter"}


def nondeterministic_calls(src: str, fn_name: str) -> list[str]:
    """Calls inside `fn_name` whose result differs between runs or between equal
    inputs (hash() is salted per process, id() is per object, clocks, random, uuid).
    A key built from any of them is not stable."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    found: list[str] = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == fn_name:
            for node in ast.walk(fn):
                if isinstance(node, ast.Call):
                    f = node.func
                    if isinstance(f, ast.Name) and f.id in _NONDETERMINISTIC_NAMES:
                        found.append(f"{f.id}()")
                    elif isinstance(f, ast.Attribute) and f.attr in _NONDETERMINISTIC_ATTRS:
                        found.append(f".{f.attr}()")
    return found


# --- running model-edited code, with guard rails ---------------------------

# Only what the fixtures actually import. `logging` and `sqlite3` are replaced by
# stand-ins below because the real modules expose `os` and can create files.
_ALLOWED_IMPORTS = {"re", "datetime", "typing", "__future__", "collections", "itertools",
                    "functools", "hashlib", "math", "string", "enum", "dataclasses"}
_real_import = builtins.__import__


class _Inert:
    """Stand-in for anything the code under test is not allowed to import."""

    def __getattr__(self, name):
        return _Inert()

    def __call__(self, *args, **kwargs):
        return _Inert()

    def __iter__(self):
        return iter(())


def _guarded_import(name, *args, **kwargs):
    if name.split(".")[0] in _ALLOWED_IMPORTS:
        return _real_import(name, *args, **kwargs)
    return _Inert()  # logging, sqlite3, os, importlib, subprocess, and everything else


def _no_open(*args, **kwargs):
    raise PermissionError("file access is disabled while verifying")


def _safe_builtins() -> dict:
    b = dict(vars(builtins))
    b["__import__"] = _guarded_import
    b["open"] = _no_open
    return b


def run_module(res: Result, name: str, src: str,
               extra: dict | None = None) -> dict | None:
    """exec `src` in a fresh namespace with the guard rails above. `extra` is
    merged in first (for injected stubs). Returns the namespace, or None after
    recording a failure."""
    ns: dict = {"__builtins__": _safe_builtins(), "__name__": "under_test"}
    ns.update(extra or {})
    try:
        exec(compile(src, name, "exec"), ns)
    except KeyboardInterrupt:
        raise
    except BaseException as e:  # includes SystemExit from exit() at import time
        res.check(False, f"{name} failed to execute: {type(e).__name__}: {e}")
        return None
    return ns


def main(verify) -> None:
    """verify(res, case_dir, work, orig, cur)"""
    # FAIL messages are partly Korean; a piped stdout on a non-UTF-8 locale
    # would otherwise crash the verifier instead of reporting.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # The code under test logs its own warnings; they are noise next to PASS/FAIL.
    logging.disable(logging.CRITICAL)
    if len(sys.argv) != 2:
        print("usage: verify.py <workdir>")
        sys.exit(2)
    work = Path(sys.argv[1]).resolve()
    case_dir = Path(sys.argv[0]).resolve().parent
    res = Result()
    orig, cur = paths(case_dir, work)
    try:
        verify(res, case_dir, work, orig, cur)
    except KeyboardInterrupt:
        raise
    except BaseException as e:  # e.g. SystemExit from exit() inside the code under test
        res.check(False, f"verification aborted: {type(e).__name__}: {e}")
    res.finish()
