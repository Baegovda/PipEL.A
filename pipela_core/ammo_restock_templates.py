"""Ammo Restock — globals()에서 3종 템플릿 로드."""

from __future__ import annotations

import os
from typing import Any, Mapping

from pipela_core.ammo_restock_catalog import (
    AMMO_PATH_GLOBAL_BY_KIND,
    AMMO_REGISTRY_DATA_KEY_BY_KIND,
    AMMO_RESTOCK_KINDS,
)
from pipela_core.image_registry import load_image_data, load_image_data_if_path_changed


def ammo_restock_load_templates_from_globals(
    g: Mapping[str, Any],
    *,
    path_snap: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """성공 시 buybutton/inven/bank 템플릿 dict, 실패 시 None."""
    templates: dict[str, Any] = {}
    for kind in AMMO_RESTOCK_KINDS:
        key = AMMO_PATH_GLOBAL_BY_KIND[kind]
        path = path_snap.get(key, g[key]) if path_snap is not None else g[key]
        reg_key = AMMO_REGISTRY_DATA_KEY_BY_KIND[kind]
        t = load_image_data(path, reg_key)
        if t is None:
            print(
                f"[Ammo Restock] FAIL {kind} ({os.path.basename(str(path or ''))})",
            )
            return None
        templates[kind] = t
    return templates


def ammo_restock_sync_templates(
    g: Mapping[str, Any],
    templates: dict[str, Any | None],
    last_paths: dict[str, str | None],
    *,
    path_snap: Mapping[str, Any] | None = None,
) -> tuple[bool, bool]:
    """
    경로(스냅샷 우선)에 맞춰 3종 템플릿을 갱신. templates·last_paths 를 제자리에서 수정.
    반환: (세 종 모두 로드 성공, 이번 호출에서 경로 변경으로 인한 갱신 발생).
    """
    any_path_changed = False
    for kind in AMMO_RESTOCK_KINDS:
        key = AMMO_PATH_GLOBAL_BY_KIND[kind]
        path = path_snap.get(key, g[key]) if path_snap is not None else g[key]
        prev_lp = last_paths.get(kind)
        tpl, new_lp = load_image_data_if_path_changed(
            path,
            AMMO_REGISTRY_DATA_KEY_BY_KIND[kind],
            prev_lp,
            templates.get(kind),
        )
        if new_lp != prev_lp:
            any_path_changed = True
        last_paths[kind] = new_lp
        templates[kind] = tpl
    all_ok = all(templates[k] is not None for k in AMMO_RESTOCK_KINDS)
    return all_ok, any_path_changed
