import ast
import builtins
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

MODELS = "app/models.py"
DB = "app/database.py"

# SQLite column types that fit each SQLAlchemy type; a mismatch is a real bug.
SQLITE_FOR = {"String": {"TEXT", "VARCHAR"}, "Text": {"TEXT"}, "Integer": {"INTEGER"},
              "Boolean": {"BOOLEAN"}, "Date": {"DATE"}}


def targets(stmt):
    if isinstance(stmt, ast.Assign):
        return [t.id for t in stmt.targets if isinstance(t, ast.Name)]
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return [stmt.target.id]
    return []


def show_class(tree):
    """(poster_url value node or None, dumps of every other statement in class Show)."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Show":
            poster, others = None, [ast.dump(b) for b in node.bases]
            for stmt in node.body:
                if "poster_url" in targets(stmt):
                    poster = stmt.value
                else:
                    others.append(ast.dump(stmt))
            return poster, others
    return None, None


def unresolved_names(tree):
    """Names that class Show reads but nothing in the module defines or imports.
    models.py is never executed here, so a missing import would otherwise go unnoticed."""
    bound = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
    missing = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Show":
            missing = {n.id for n in ast.walk(node)
                       if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound}
    return missing


def column_type_name(value):
    """SQLAlchemy type name in Column(String) / mapped_column(String(200)), or None."""
    if isinstance(value, ast.Call) and getattr(value.func, "id", None) in ("Column", "mapped_column"):
        for arg in value.args:
            node = arg.func if isinstance(arg, ast.Call) else arg
            if isinstance(node, ast.Name):
                return node.id
    return None


def verify(res, case_dir, work, orig, cur):
    for f in (MODELS, DB):
        if f not in cur:
            res.check(False, f"{f} is gone")
            return

    # ① models.py: Show에 poster_url 컬럼이 실제 코드로 들어갔는가 (주석 처리된 건 안 셈)
    mtree = parse(res, MODELS, cur[MODELS])
    if mtree is None:
        return
    poster, others = show_class(mtree)
    o_poster, o_others = show_class(ast.parse(orig[MODELS]))
    if others is None:
        res.check(False, "class Show was renamed or removed")
        return
    res.check(poster is not None, "poster_url column not added to Show in models.py")
    missing = unresolved_names(mtree)
    res.check(not missing, f"models.py uses names it never imports or defines: {sorted(missing)}")
    res.check(others == o_others, "something else in class Show was changed (a column, __tablename__, or the base)")
    type_name = column_type_name(poster) if poster is not None else None

    # ② database.py의 MIGRATIONS에도 같이 들어갔는가: 이게 짝 규칙의 핵심
    if parse(res, DB, cur[DB]) is None:
        return
    ns = run_module(res, DB, cur[DB])
    if ns is None:
        return
    shows = ns.get("MIGRATIONS", {}).get("shows", {})
    res.check("poster_url" in shows,
              "poster_url missing from MIGRATIONS['shows']; CLAUDE.md requires both files to change together")
    decl = str(shows.get("poster_url", ""))
    res.check(not ("NOT NULL" in decl.upper() and "DEFAULT" not in decl.upper()),
              f"migration {decl!r} fails on an existing table: SQLite cannot add a NOT NULL column without a default")
    if type_name in SQLITE_FOR and decl:
        base = decl.split()[0].split("(")[0].upper()
        res.check(base in SQLITE_FOR[type_name],
                  f"migration type {decl!r} does not match the model's {type_name} column")
    for keep, want in (("venue", "TEXT"), ("start_date", "DATE"), ("is_upcoming", "BOOLEAN DEFAULT 1")):
        res.check(shows.get(keep) == want, f"existing migration entry `{keep}` was changed or removed")

    # 나머지 코드는 그대로여야 한다. models.py의 import는 새 컬럼 타입 때문에 늘 수 있다.
    same_except(res, MODELS, orig[MODELS], cur[MODELS], skip={"def:Show"}, imports="superset")
    same_except(res, DB, orig[DB], cur[DB], skip={"assign:MIGRATIONS"})
    # CLAUDE.md는 읽으라고 준 것이지 고치라고 준 게 아니다
    untouched(res, orig, cur, allowed={MODELS, DB})


main(verify)
