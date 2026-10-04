"""목록 화면용 페이지 나누기."""


def paginate(items, page, per_page):
    """1부터 세는 page의 항목들. 범위 밖이거나 per_page가 0 이하면 빈 리스트."""
    if per_page <= 0 or page < 1:
        return []
    start = (page - 1) * per_page
    return list(items[start:start + per_page])


def page_count(total, per_page):
    """전체 total건을 per_page건씩 나눴을 때의 페이지 수. 항목이 없거나 per_page가 0 이하면 0."""
    if total <= 0 or per_page <= 0:
        return 0
    return (total + per_page - 1) // per_page
