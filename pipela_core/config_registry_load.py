"""레지스트리에서 JSON ROI·템플릿 경로·이미지 데이터 플래그 로드 — target Mapping에 반영."""

from __future__ import annotations

import json
import winreg
from collections.abc import Callable, MutableMapping
from typing import Any


def load_json_regions_from_registry(
    key: Any,
    target: MutableMapping[str, Any],
    regions: tuple[tuple[str, str, str | None], ...],
) -> None:
    for reg_key, global_key, log_msg in regions:
        try:
            region_data = winreg.QueryValueEx(key, reg_key)[0]
            target[global_key] = json.loads(region_data) if region_data else None
            if log_msg and target[global_key]:
                print(log_msg)
        except FileNotFoundError:
            pass


def migrate_reload_vault_match_region(key: Any, target: MutableMapping[str, Any]) -> None:
    if target.get("reload_vault_match_region") is not None:
        return
    try:
        old = winreg.QueryValueEx(key, "reload_bullet_miss_match_region")[0]
        target["reload_vault_match_region"] = json.loads(old) if old else None
    except FileNotFoundError:
        pass


def load_template_image_paths_from_registry(
    key: Any,
    target: MutableMapping[str, Any],
    path_pairs: tuple[tuple[str, str], ...],
    migrate_path: Callable[[Any], Any],
) -> None:
    for reg_key, gv in path_pairs:
        try:
            saved_path = winreg.QueryValueEx(key, reg_key)[0]
            if saved_path:
                target[gv] = migrate_path(saved_path)
        except (FileNotFoundError, ValueError):
            pass


def migrate_reload_vault_image_path(
    key: Any,
    target: MutableMapping[str, Any],
    migrate_path: Callable[[Any], Any],
) -> None:
    try:
        winreg.QueryValueEx(key, "reload_vault_image_path")
    except FileNotFoundError:
        try:
            saved = winreg.QueryValueEx(key, "reload_bullet_miss_image_path")[0]
            if saved:
                target["RELOAD_VAULT_IMAGE_PATH"] = migrate_path(saved)
        except FileNotFoundError:
            pass


def load_image_data_presence_from_registry(
    key: Any,
    target: MutableMapping[str, Any],
    pairs: tuple[tuple[str, str], ...],
) -> None:
    for reg_key, gv in pairs:
        try:
            winreg.QueryValueEx(key, reg_key)
            target[gv] = True
        except FileNotFoundError:
            target[gv] = False


def migrate_reload_vault_image_data_flag(key: Any, target: MutableMapping[str, Any]) -> None:
    if target.get("RELOAD_VAULT_IMAGE_DATA"):
        return
    try:
        winreg.QueryValueEx(key, "reload_bullet_miss_image_data")
        target["RELOAD_VAULT_IMAGE_DATA"] = True
    except FileNotFoundError:
        pass
