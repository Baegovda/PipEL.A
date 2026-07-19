"""콘솔 로그 UI·레지스트리에서 공유하는 보존/시간 모드 상수."""

from __future__ import annotations

# 분 스핀 허용 범위 (0이면 초만으로 1초~59초 등 설정 가능)
CONSOLE_LOG_RETENTION_MIN_MIN = 0
CONSOLE_LOG_RETENTION_MAX_MIN = 10080  # 7일(분 단위 상한)
CONSOLE_LOG_RETENTION_MAX_SECONDS = 59  # 추가 초
CONSOLE_LOG_RETENTION_MIN_TOTAL_SEC = 1
CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC = CONSOLE_LOG_RETENTION_MAX_MIN * 60

# 로그 보존 UI: 시간·분·초 스핀 (분·초는 각 0~59, 시간 상한은 총 상한 초에서 유도).
CONSOLE_LOG_RETENTION_UI_MAX_CLOCK_MINUTE = 59
CONSOLE_LOG_RETENTION_UI_MAX_HOURS = max(
    0,
    CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC // 3600,
)
CONSOLE_LOG_TIME_MODE_ABSOLUTE = "absolute"
CONSOLE_LOG_TIME_MODE_RELATIVE = "relative"


def console_log_retention_total_sec(minutes: int, seconds: int) -> int:
    """분+초 합산 보존 시간(초). 레지·UI에서 공통 클램프."""
    total = int(minutes) * 60 + int(seconds)
    return max(
        int(CONSOLE_LOG_RETENTION_MIN_TOTAL_SEC),
        min(int(CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC), total),
    )


def console_log_retention_total_sec_from_hms(
    hours: int,
    clock_minutes: int,
    seconds: int,
) -> int:
    """시·분·초(분·초는 시계처럼 0~59) → 합산 보존 시간(초)."""
    total = int(hours) * 3600 + int(clock_minutes) * 60 + int(seconds)
    return max(
        int(CONSOLE_LOG_RETENTION_MIN_TOTAL_SEC),
        min(int(CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC), total),
    )


def console_log_retention_split_total(total_sec: int) -> tuple[int, int]:
    """총 초 → (분, 초) 정규화(초는 0~59)."""
    t = max(
        int(CONSOLE_LOG_RETENTION_MIN_TOTAL_SEC),
        min(int(CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC), int(total_sec)),
    )
    return t // 60, t % 60


def console_log_retention_split_total_to_hms(total_sec: int) -> tuple[int, int, int]:
    """총 초 → (시, 분, 초) 각 0~59 분·초, 시는 최대 ``CONSOLE_LOG_RETENTION_UI_MAX_HOURS``."""
    t = max(
        int(CONSOLE_LOG_RETENTION_MIN_TOTAL_SEC),
        min(int(CONSOLE_LOG_RETENTION_MAX_TOTAL_SEC), int(total_sec)),
    )
    h = t // 3600
    rem = t % 3600
    m = rem // 60
    s = rem % 60
    return h, m, s
