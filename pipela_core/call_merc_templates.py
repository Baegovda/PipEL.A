"""Call Merc — 경로·쿨다운 반영 템플릿 일괄 로드(Reload 와 유사 패턴)."""

from __future__ import annotations

import os
from typing import Any, Mapping, NamedTuple

from pipela_core.call_merc_catalog import (
    CALL_MERC_KINDS,
    CALL_MERC_LOG_PREFIX,
    CALL_MERC_LOOP_LOG_TAG,
    CALL_MERC_PATH_KEY,
    CALL_MERC_REG_DATA_KEY,
)
from pipela_core.image_registry import load_image_data

# 동일 kind+경로에서 템플릿 로드 실패 시 — 1초 재시도마다 콘솔이 도배되지 않게 1회만 출력
_logged_merc_template_load_fail: set[str] = set()


def _merc_template_fail_key(kind: str, path: object) -> str:
    try:
        p = os.path.normcase(os.path.abspath(str(path or "")))
    except Exception:
        p = str(path or "")
    return f"{kind}\t{p}"


class CallMercTemplateLoadResult(NamedTuple):
    ok: bool
    templates: dict[str, Any] | None
    """전체 갱신 시에만; 캐시 히트면 None."""
    sync_last_paths: dict[str, str | None] | None
    """last_paths에 덮어쓸 전체 kind→path; 없으면 변경 없음."""
    reset_scaled_state: bool
    """True면 scaled·last_ratio 초기화 필요."""
    cooldown_until_mono: float


def call_merc_try_reload_templates(
    g: Mapping[str, Any],
    templates: Mapping[str, Any | None],
    last_paths: Mapping[str, str | None],
    *,
    now_mono: float,
    cooldown_until_mono: float,
    path_snap: Mapping[str, Any] | None = None,
) -> CallMercTemplateLoadResult:
    def _path(kind: str) -> Any:
        key = CALL_MERC_PATH_KEY[kind]
        if path_snap is not None:
            return path_snap.get(key, g[key])
        return g[key]

    paths = {k: _path(k) for k in CALL_MERC_KINDS}
    if all(
        templates.get(k) is not None and last_paths.get(k) == paths[k]
        for k in CALL_MERC_KINDS
    ):
        return CallMercTemplateLoadResult(
            True, None, None, False, cooldown_until_mono,
        )

    paths_unchanged = all(last_paths.get(k) == paths[k] for k in CALL_MERC_KINDS)
    if paths_unchanged and now_mono < cooldown_until_mono:
        return CallMercTemplateLoadResult(
            False, None, None, False, cooldown_until_mono,
        )

    new_t: dict[str, Any] = {}
    for kind in CALL_MERC_KINDS:
        path = paths[kind]
        tpl = load_image_data(path, CALL_MERC_REG_DATA_KEY[kind])
        if tpl is None:
            tag = CALL_MERC_LOOP_LOG_TAG.get(kind, kind)
            _fk = _merc_template_fail_key(kind, path)
            if _fk not in _logged_merc_template_load_fail:
                _logged_merc_template_load_fail.add(_fk)
                print(
                    f"{CALL_MERC_LOG_PREFIX} FAIL {tag} ({os.path.basename(str(path or ''))})",
                    flush=True,
                )
            sync = {k2: paths[k2] for k2 in CALL_MERC_KINDS}
            return CallMercTemplateLoadResult(
                False, None, sync, False, now_mono + 1.0,
            )
        new_t[kind] = tpl

    sync = {k: paths[k] for k in CALL_MERC_KINDS}
    _logged_merc_template_load_fail.clear()
    return CallMercTemplateLoadResult(True, new_t, sync, True, 0.0)
