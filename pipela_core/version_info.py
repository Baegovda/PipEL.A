"""앱 버전·업데이트 manifest URL — Qt·main 공통 (환경 변수로 오버라이드 가능)."""

from __future__ import annotations

import os

# 정식 SemVer — 루트 `version.json` 의 `version` 과 항상 동일. 릴리스 시 둘 다 갱신.
PIPELA_APP_VERSION = "0.9.13"

# 작업 표시줄·창 제목·로그 접두 등 사용자에게 보이는 제품 이름 (내부 패키지명 pipela_*·경로 Pipela 와 별개).
PIPELA_APP_DISPLAY_NAME = "Pipela"

# 상단 스트립 등 UI 개정 표시 — 원칙적으로 PIPELA_APP_VERSION 과 같게 둠.
PIPELA_STRIP_DISPLAY_VERSION = "0.9.13"

PIPELA_UPDATE_MANIFEST_URL = (
    os.environ.get("PIPELA_UPDATE_MANIFEST_URL", "").strip()
    or "https://raw.githubusercontent.com/Baegovda/PipEL.A/refs/heads/main/version.json"
).strip()

# 동일 버전·테스트용 EXE 재설치: 비우면 manifest 의 download_url 사용 (version.json 수정 없이 릴리스의 exe만 갈아끼울 때)
PIPELA_REINSTALL_EXE_URL = os.environ.get("PIPELA_REINSTALL_EXE_URL", "").strip()
