import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness import main, parse, same_except, untouched

TARGET = "app/messages.py"
EXPECTED = "구독이 완료되었습니다. 새 공연이 올라오면 바로 알려드립니다."


def verify(res, case_dir, work, orig, cur):
    if TARGET not in cur:
        res.check(False, f"{TARGET} is gone")
        return
    src = cur[TARGET]
    tree = parse(res, TARGET, src)
    if tree is None:
        return

    value = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and getattr(node.targets[0], "id", None) == "SUBSCRIBE_OK":
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                value = None
    res.check(value == EXPECTED,
              f"SUBSCRIBE_OK should read exactly {EXPECTED!r}, got {value!r}")

    # SUBSCRIBE_OK 말고는 docstring과 다른 상수까지 그대로여야 한다
    same_except(res, TARGET, orig[TARGET], src, skip={"assign:SUBSCRIBE_OK"})

    untouched(res, orig, cur, allowed={TARGET})


main(verify)
