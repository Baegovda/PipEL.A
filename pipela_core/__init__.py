"""백엔드·Qt 공통 참조 — main.py 에서 점진 이전.

UI와 무관한 상수·경로·순수 로직을 여기로 옮기고,
main 은 런타임 전역·매크로 루프·Qt/`pipela_mod` 공유 백엔드를 유지한다.

인수인계·이관 방향·모듈 목록: docs/MIGRATION_HANDOFF.md
에이전트 진입: 루트 AGENTS.md

최근 추가: vision_lazy, vision_capture, config_parse, config_registry_* (맨 위 실시간 진행판 참고).
"""

from __future__ import annotations
