#!/usr/bin/env python3
"""Export HKCU registry key schema for C++ parity (one-shot / CI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipela_core.config_registry_tables import (  # noqa: E402
    CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS,
    CONFIG_CALL_MERC_THRESHOLD_KEYS,
    CONFIG_LOAD_BOOLS_PRE_KC,
    CONFIG_LOAD_IMAGE_DATA_PRESENCE,
    CONFIG_LOAD_JSON_REGIONS,
    CONFIG_LOAD_OPTIONAL_FLOATS,
    CONFIG_LOAD_TEMPLATE_IMAGE_PATHS,
    CONFIG_SAVE_BOOLS_FLAME,
    CONFIG_SAVE_LEFTCLICK_FIELDS,
    CONFIG_SAVE_MERC_FIRE_FIELDS,
    CONFIG_SAVE_SZ_FIELDS,
    REGISTRY_CONFIG_SNAPSHOT_KEYS,
)
from pipela_core.registry_constants import REGISTRY_PATH  # noqa: E402


def _entries() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def add(key: str, *, value_type: str, global_name: str | None = None, default=None) -> None:
        if key in seen:
            return
        seen.add(key)
        row: dict = {"registry_key": key, "value_type": value_type}
        if global_name:
            row["global_name"] = global_name
        if default is not None:
            row["default"] = default
        rows.append(row)

    for reg_key, global_name, default in CONFIG_LOAD_BOOLS_PRE_KC:
        add(reg_key, value_type="bool", global_name=global_name, default=default)
    for reg_key in CONFIG_SAVE_BOOLS_FLAME:
        add(reg_key, value_type="bool", global_name=reg_key, default=True)
    for reg_key, global_name, _ in CONFIG_LOAD_JSON_REGIONS:
        add(reg_key, value_type="json_region", global_name=global_name)
    for reg_key, global_name in CONFIG_LOAD_OPTIONAL_FLOATS:
        add(reg_key, value_type="float", global_name=global_name)
    for reg_key, global_name in CONFIG_SAVE_SZ_FIELDS:
        add(reg_key, value_type="string_or_number", global_name=global_name)
    for reg_key, global_name in CONFIG_LOAD_TEMPLATE_IMAGE_PATHS:
        add(reg_key, value_type="path", global_name=global_name)
    for reg_key, global_name in CONFIG_LOAD_IMAGE_DATA_PRESENCE:
        add(reg_key, value_type="base64_image", global_name=global_name)
    for reg_key in CONFIG_AMMO_RESTOCK_THRESHOLD_KEYS:
        add(reg_key, value_type="float_threshold", global_name=reg_key)
    for reg_key in CONFIG_CALL_MERC_THRESHOLD_KEYS:
        add(reg_key, value_type="float_threshold", global_name=reg_key)
    for reg_key in CONFIG_SAVE_LEFTCLICK_FIELDS:
        add(reg_key, value_type="string_or_number", global_name=reg_key)
    for reg_key in CONFIG_SAVE_MERC_FIRE_FIELDS:
        add(reg_key, value_type="string_or_number", global_name=reg_key)
    for name in REGISTRY_CONFIG_SNAPSHOT_KEYS:
        add(name, value_type="snapshot", global_name=name)
    rows.sort(key=lambda r: r["registry_key"])
    return rows


def main() -> int:
    out_path = ROOT / "registry" / "schema.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "registry_path": REGISTRY_PATH,
        "schema_version": 1,
        "entry_count": 0,
        "entries": _entries(),
    }
    payload["entry_count"] = len(payload["entries"])
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({payload['entry_count']} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
