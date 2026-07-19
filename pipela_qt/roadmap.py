"""Qt 이전 로드맵 — 완료 여부와 남은 단계 수.

`python -c "from pipela_qt import roadmap; print(roadmap.summary())"`

아키텍처·분리 방향은 루트 `AGENTS.md` 를 본다. (이 파일은 UI 단계 체크리스트에 가깝다.)
"""

from __future__ import annotations

# (id, 제목, 완료)
QT_MIGRATION_PHASES: tuple[tuple[str, str, bool], ...] = (
    ("P01", "부트스트랩 공통·오버레이·제어 토글·설정 허브·시스템 트레이", True),
    ("P02", "설정: 터미널(Console) - 보존 분·절대/상대 시간", True),
    ("P03", "설정: 인터페이스(iface)", True),
    ("P04", "설정: 업데이트·테서렉트 설치 안내(단순)", True),
    ("P05", "설정: LeftClick", True),
    ("P06", "설정: Flame Trigger", True),
    ("P07", "설정: Reload / HP Refill (템플릿·미리보기)", True),
    ("P08", "설정: Ride / Ammo / Call Merc / START GAME", True),
    ("P09", "킬 카운터 패널·통계 UI", True),
    ("P10", "Qt 패널: ROI·템플릿 캡처·미리보기·부트스트랩(레거시 별도 UI 없음)", True),
    ("P11", "커서 아이콘·플레임 오버레이·Flame 시작 배너 (Qt HUD)", True),
    ("P12", "PyInstaller 기본 진입 Qt·레거시 `--tk` 등 CLI 정리", True),
    # 축 B — 남은 단계는 `roadmap.summary()` 참고
    ("P13", "축 B: 레거시 스텁 패키지 제거·표준 GUI 바인딩 미사용", True),
    ("P14", "축 B: 오버레이·제어·커서 main 슬림화", True),
    ("P15", "축 B: 레거시 CLI·spec·문서 정리", True),
)


def phases_done_count() -> int:
    return sum(1 for _a, _b, done in QT_MIGRATION_PHASES if done)


def phases_remaining_count() -> int:
    return sum(1 for _a, _b, done in QT_MIGRATION_PHASES if not done)


def phases_total_count() -> int:
    return len(QT_MIGRATION_PHASES)


def summary() -> str:
    d = phases_done_count()
    t = phases_total_count()
    r = phases_remaining_count()
    lines = [f"Qt 이전: 완료 {d}/{t}, 남은 단계 {r}개", ""]
    for pid, title, done in QT_MIGRATION_PHASES:
        mark = "[x]" if done else "[ ]"
        lines.append(f"  {mark} {pid}  {title}")
    return "\n".join(lines)
