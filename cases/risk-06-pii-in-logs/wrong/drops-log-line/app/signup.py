"""회원 가입 처리."""
import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^01\d-?\d{3,4}-?\d{4}$")
_BIRTH = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED = ("name", "email", "phone", "birth_date")


def validate_form(form):
    """검증에 실패한 필드 이름 목록. 통과하면 빈 리스트."""
    failed = []
    for field in REQUIRED:
        value = (form.get(field) or "").strip()
        if not value:
            failed.append(field)
        elif field == "email" and not _EMAIL.match(value):
            failed.append(field)
        elif field == "phone" and not _PHONE.match(value):
            failed.append(field)
        elif field == "birth_date" and not _BIRTH.match(value):
            failed.append(field)
    return failed


def register(user, db, logger):
    """가입 폼을 검증하고 저장한다."""
    failed = validate_form(user)
    if failed:
        return {"ok": False, "errors": failed}
    user_id = db.insert_user(user)
    logger.info("signup ok: user_id=%s", user_id)
    return {"ok": True, "user_id": user_id}
