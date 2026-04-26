"""구조화 성능 로그 — 매칭·캡처 grab·OCR 시간, Kill Counter OCR 스킵 비율.

환경 변수:
  PIPELA_METRICS=1|true|yes — 수집·주기 로그 활성화
  PIPELA_METRICS_INTERVAL_SEC — 요약 출력 주기(초, 기본 45)
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

_lock = threading.Lock()
_match_n = 0
_match_sum_ms = 0.0
_match_max_ms = 0.0
_cap_n = 0
_cap_sum_ms = 0.0
_cap_max_ms = 0.0
_ocr_n = 0
_ocr_sum_ms = 0.0
_ocr_max_ms = 0.0
_kc_frames = 0
_kc_skips = 0
_kc_ocr_runs = 0
_emitter_lock = threading.Lock()
_emitter_started = False


def telemetry_metrics_enabled() -> bool:
    return os.environ.get("PIPELA_METRICS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def telemetry_metrics_interval_sec() -> float:
    try:
        v = float(os.environ.get("PIPELA_METRICS_INTERVAL_SEC", "45"))
        return max(5.0, min(v, 3600.0))
    except (TypeError, ValueError):
        return 45.0


def telemetry_record_match_sec(dt: float) -> None:
    if not telemetry_metrics_enabled() or dt < 0:
        return
    global _match_n, _match_sum_ms, _match_max_ms
    ms = dt * 1000.0
    with _lock:
        _match_n += 1
        _match_sum_ms += ms
        if ms > _match_max_ms:
            _match_max_ms = ms


def telemetry_record_capture_grab_sec(dt: float) -> None:
    """mss 클라이언트 전체 grab(+BGR 변환) 1회 — 캐시 미스 시에만 호출."""
    if not telemetry_metrics_enabled() or dt < 0:
        return
    global _cap_n, _cap_sum_ms, _cap_max_ms
    ms = dt * 1000.0
    with _lock:
        _cap_n += 1
        _cap_sum_ms += ms
        if ms > _cap_max_ms:
            _cap_max_ms = ms


def telemetry_record_ocr_sec(dt: float) -> None:
    if not telemetry_metrics_enabled() or dt < 0:
        return
    global _ocr_n, _ocr_sum_ms, _ocr_max_ms
    ms = dt * 1000.0
    with _lock:
        _ocr_n += 1
        _ocr_sum_ms += ms
        if ms > _ocr_max_ms:
            _ocr_max_ms = ms


def telemetry_kc_frame(*, skipped: bool, ran_ocr: bool) -> None:
    """Kill Counter: 유효 캡처 1틱. skipped=동일 화면으로 OCR 생략, ran_ocr=OCR 실행."""
    if not telemetry_metrics_enabled():
        return
    global _kc_frames, _kc_skips, _kc_ocr_runs
    with _lock:
        _kc_frames += 1
        if skipped:
            _kc_skips += 1
        if ran_ocr:
            _kc_ocr_runs += 1


def _agg(n: int, sum_ms: float, max_ms: float) -> dict[str, Any]:
    return {
        "n": int(n),
        "sum_ms": round(float(sum_ms), 3),
        "avg_ms": round(float(sum_ms / n), 4) if n else 0.0,
        "max_ms": round(float(max_ms), 4),
    }


def _snapshot_and_reset() -> dict[str, Any] | None:
    global _match_n, _match_sum_ms, _match_max_ms
    global _cap_n, _cap_sum_ms, _cap_max_ms
    global _ocr_n, _ocr_sum_ms, _ocr_max_ms
    global _kc_frames, _kc_skips, _kc_ocr_runs
    with _lock:
        if (
            _match_n == 0
            and _cap_n == 0
            and _ocr_n == 0
            and _kc_frames == 0
        ):
            return None
        out = {
            "evt": "ech_metrics",
            "ts": time.time(),
            "interval_sec": telemetry_metrics_interval_sec(),
            "template_match_ms": _agg(_match_n, _match_sum_ms, _match_max_ms),
            "capture_grab_ms": _agg(_cap_n, _cap_sum_ms, _cap_max_ms),
            "ocr_ms": _agg(_ocr_n, _ocr_sum_ms, _ocr_max_ms),
            "kill_counter": {
                "frames": int(_kc_frames),
                "ocr_skipped": int(_kc_skips),
                "ocr_runs": int(_kc_ocr_runs),
                "skip_ratio": round(_kc_skips / _kc_frames, 4) if _kc_frames else 0.0,
            },
        }
        _match_n = 0
        _match_sum_ms = 0.0
        _match_max_ms = 0.0
        _cap_n = 0
        _cap_sum_ms = 0.0
        _cap_max_ms = 0.0
        _ocr_n = 0
        _ocr_sum_ms = 0.0
        _ocr_max_ms = 0.0
        _kc_frames = 0
        _kc_skips = 0
        _kc_ocr_runs = 0
    return out


def _emitter_loop() -> None:
    interval = telemetry_metrics_interval_sec()
    while True:
        time.sleep(interval)
        if not telemetry_metrics_enabled():
            continue
        snap = _snapshot_and_reset()
        if snap is None:
            continue
        try:
            print(json.dumps(snap, ensure_ascii=False), flush=True)
        except Exception:
            pass


def telemetry_start_periodic_emitter() -> None:
    """백그라운드에서 주기적 JSON 한 줄 출력. idempotent."""
    global _emitter_started
    if not telemetry_metrics_enabled():
        return
    with _emitter_lock:
        if _emitter_started:
            return
        _emitter_started = True
    try:
        print(
            f"[Pipela] metrics: PIPELA_METRICS=1, interval={telemetry_metrics_interval_sec():g}s (JSON lines)",
            flush=True,
        )
    except Exception:
        pass
    th = threading.Thread(target=_emitter_loop, name="ech-telemetry", daemon=True)
    th.start()
