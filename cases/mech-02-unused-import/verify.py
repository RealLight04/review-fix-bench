import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import import_bindings, main, parse, same_except, untouched

TARGET = "app/collector.py"


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    tree = parse(res, TARGET, src)
    if tree is None:
        return

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.asname or a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(a.asname or a.name for a in node.names)

    res.check("json" not in imported, "unused import `json` still present")
    res.check("timedelta" not in imported, "unused import `timedelta` still present")
    # 실제로 쓰이는 것은 남아 있어야 한다 (과잉 삭제 방지)
    for keep in ("logging", "date", "datetime"):
        res.check(keep in imported, f"removed `{keep}`, which is actually used")

    # 남은 import는 원래 것에서 두 개만 뺀 것과 정확히 같아야 한다 (`import datetime`으로 바꾸거나 별칭을 붙이면 안 된다)
    expected = import_bindings(ast.parse(orig[TARGET])) - {(None, "json", None), ("datetime", "timedelta", None)}
    res.check(import_bindings(tree) == expected,
              f"the imports should be exactly the original minus json and timedelta, got {sorted(map(str, import_bindings(tree)))}")

    # import 밖의 코드는 docstring까지 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip=set(), imports="skip")

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
