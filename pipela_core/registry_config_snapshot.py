"""레지스트리와 동기화되는 설정의 읽기용 스냅샷 — Qt·진단에서 `main` 전역 직접 훑기 완화."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from pipela_core.config_registry_tables import REGISTRY_CONFIG_SNAPSHOT_KEYS

_snapshot: dict[str, Any] = {}


def get_registry_config_snapshot() -> Mapping[str, Any]:
    """최근 `refresh_registry_config_snapshot` 이후의 얕은 복사 dict(값은 main 전역과 동일 객체일 수 있음)."""
    return _snapshot


def refresh_registry_config_snapshot(module_globals: MutableMapping[str, Any]) -> None:
    """`load_config` / `save_config` 성공 후(또는 초기 기본값 반영 후) 호출."""
    global _snapshot
    _snapshot = {
        k: module_globals[k]
        for k in REGISTRY_CONFIG_SNAPSHOT_KEYS
        if k in module_globals
    }


def sync_registry_snapshot_from_module(module: Any) -> None:
    """`main` 등 모듈 전역을 직접 수정한 직후 호출 — 레지 저장이 디바운스여도 스냅샷이 전역과 즉시 일치."""
    refresh_registry_config_snapshot(module.__dict__)


def registry_config_snapshot_key_names() -> tuple[str, ...]:
    """스냅샷에 포함되는 키 목록(고정 순서)."""
    return REGISTRY_CONFIG_SNAPSHOT_KEYS
