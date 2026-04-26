"""앱 버전·업데이트 manifest URL — Qt·main 공통 (환경 변수로 오버라이드 가능)."""

from __future__ import annotations

import os

# 앱 표시·업데이트 비교용 버전 — 고정 1.0.0 (빌드마다 올리지 않음). manifest 의 version 과 맞추면 됨.
PIPELA_APP_VERSION = "1.0.0"

# 작업 표시줄·창 제목·로그 접두 등 사용자에게 보이는 제품 이름 (내부 패키지명 pipela_*·경로 Pipela 와 별개).
PIPELA_APP_DISPLAY_NAME = "Pipela"

# 상단 스트립·크롬 등 **개발 중 표시용** 개정 번호 (SemVer). 공식 릴리스 번호와 별개 — 갱신 빈도·등급은 AGENTS.md 참고.
PIPELA_STRIP_DISPLAY_VERSION = "0.9.12"

PIPELA_UPDATE_MANIFEST_URL = (
    os.environ.get("PIPELA_UPDATE_MANIFEST_URL", "").strip()
    or "https://raw.githubusercontent.com/Baegovda/Pipela/refs/heads/main/version.json"
).strip()

# 동일 버전·테스트용 EXE 재설치: 비우면 manifest 의 download_url 사용 (version.json 수정 없이 릴리스의 exe만 갈아끼울 때)
PIPELA_REINSTALL_EXE_URL = os.environ.get("PIPELA_REINSTALL_EXE_URL", "").strip()
