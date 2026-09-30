"""로컬 스모크 테스트 — 서버를 띄우고 엔드포인트를 확인한다."""

VENV_MARKER = "myapp/venv"
DEFAULT_PORT = 9000


def list_processes():
    """[(pid, exe_path)] — 실행 중인 파이썬 프로세스."""
    raise NotImplementedError  # 런타임에 주입된다


def list_listeners():
    """[(port, pid)] — 지금 LISTEN 중인 포트와 그 소유 프로세스."""
    raise NotImplementedError  # 런타임에 주입된다


def kill(pid):
    raise NotImplementedError  # 런타임에 주입된다


def stop_previous(port=DEFAULT_PORT):
    """이 스크립트가 띄웠던 이전 인스턴스를 정리한다."""
    killed = []
    for pid, exe in list_processes():
        if VENV_MARKER in exe:
            kill(pid)
            killed.append(pid)
    return killed
