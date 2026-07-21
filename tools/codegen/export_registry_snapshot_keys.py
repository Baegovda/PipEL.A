#!/usr/bin/env python3
"""Export REGISTRY_CONFIG_SNAPSHOT_KEYS for C++ RegistrySnapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipela_core.config_registry_tables import REGISTRY_CONFIG_SNAPSHOT_KEYS  # noqa: E402


def main() -> int:
    out = ROOT / "registry" / "snapshot_keys.json"
    payload = {"key_count": len(REGISTRY_CONFIG_SNAPSHOT_KEYS), "keys": list(REGISTRY_CONFIG_SNAPSHOT_KEYS)}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({payload['key_count']} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
