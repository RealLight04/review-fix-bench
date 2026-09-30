import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, run_module, same_except, untouched

TARGET = "app/screener.py"
FN = "passes_trend_template"
FIXED_INDEX = 2  # the ma150-vs-ma200 comparison, third entry of `checks`

# 정상 상승추세: 통과해야 한다
UPTREND = dict(price=120, ma50=115, ma150=110, ma200=100,
               ma200_slope=1, high_52w=130, low_52w=80)
# 150일선이 200일선 아래: 떨어져야 한다
DOWNTREND = dict(price=120, ma50=115, ma150=95, ma200=100,
                 ma200_slope=1, high_52w=130, low_52w=80)


def function_and_checks(tree):
    """(the function node, the `checks` list node) or (None, None)."""
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == FN:
            for stmt in ast.walk(fn):
                if isinstance(stmt, ast.Assign) and any(
                        getattr(t, "id", None) == "checks" for t in stmt.targets) \
                        and isinstance(stmt.value, ast.List):
                    return fn, stmt.value
    return None, None


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    tree = parse(res, TARGET, src)
    if tree is None:
        return

    ns = run_module(res, TARGET, src)
    if ns is None:
        return
    fn = ns.get(FN)
    if fn is None:
        res.check(False, f"{FN} was renamed or removed")
        return

    try:
        res.check(fn(UPTREND) is True, "a genuine uptrend (ma150 > ma200) is still rejected")
        res.check(fn(DOWNTREND) is False, "a downtrend (ma150 < ma200) still passes")
        # 경계 바로 아래도 떨어져야 한다 (여유 계수를 붙인 비교를 잡는다)
        res.check(fn(dict(UPTREND, ma150=99.5)) is False, "ma150 just below ma200 still passes")
    except Exception as e:
        res.check(False, f"function raised on valid input: {type(e).__name__}: {e}")
        return

    # 고친 건 세 번째 조건 하나뿐이어야 한다. 조건 몇 개는 서로를 함축해서 값으로는
    # 삭제를 알아챌 수 없으니 구조로 비교한다: 그 항목만 원래 것으로 되돌려 놓고
    # 함수 전체(반환문 포함)가 원본과 똑같은지 본다.
    o_fn, o_checks = function_and_checks(ast.parse(orig[TARGET]))
    c_fn, c_checks = function_and_checks(tree)
    if c_checks is None:
        res.check(False, f"the `checks` list in {FN} was restructured")
    elif len(c_checks.elts) != len(o_checks.elts):
        res.check(False, f"`checks` has {len(c_checks.elts)} entries; it had {len(o_checks.elts)} and must keep them")
    else:
        c_checks.elts[FIXED_INDEX] = o_checks.elts[FIXED_INDEX]
        res.check(ast.dump(c_fn) == ast.dump(o_fn),
                  f"something in {FN} other than check #{FIXED_INDEX + 1} was changed "
                  "(another check, a threshold, the return statement, or the docstring)")

    same_except(res, TARGET, orig[TARGET], src, skip={f"def:{FN}"})
    untouched(res, orig, cur, allowed={TARGET})


main(verify)
