from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def index():
    return {"page": "dashboard"}


@router.get("/reports")
def reports():
    return {"page": "reports"}
