# CLAUDE.md

## 컬럼을 추가할 때

새 컬럼은 두 군데에 같이 넣는다. `app/models.py`의 모델과 `app/database.py`의 `MIGRATIONS`다.
앱이 뜰 때 `init_db()`가 `MIGRATIONS`를 보고 기존 DB에 빠진 컬럼을 ALTER로 채운다.

모델에만 넣으면 새로 만든 DB에서는 문제가 안 보인다. 그런데 이미 쓰던 DB에서는 `no such column`으로
깨지고 테스트로는 잘 안 잡힌다. 그래서 두 파일은 항상 함께 고친다.

## 커밋

- 사용자가 요청할 때만 커밋한다.
