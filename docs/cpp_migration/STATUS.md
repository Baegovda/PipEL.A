# C++ migration — live status

**Single handoff doc** for conversion progress. Update this file when worker/core parity changes.

| Doc | Role |
|-----|------|
| **This file** | Worker + runtime cutover status (manual) |
| [`parity_matrix.md`](parity_matrix.md) | Python module → C++ file map (auto: `python tools/export_parity_matrix.py`) |
| [`COMPLETE.md`](COMPLETE.md) | Cutover gates before removing Python |
| [`README.md`](README.md) | Build / env quick start |

**Policy:** local commits OK; **no push/release** until full cutover (owner).

**Runtime:** `pipela_native.pyd` beside `main.py` → C++ workers auto-ON, Python `*_loop` threads skipped. Opt-out: `PIPELA_NATIVE_WORKERS=0`.

---

## Phase rollup

| Phase | Status | Blocker |
|-------|--------|---------|
| 0 Foundation | ✅ | — |
| 1 Core | ✅ | — |
| 2 Workers | 🟡 | 6/10 real logic; KC OCR + launcher TBD |
| 3 Native (DComp, hooks) | ✅ | — |
| 4 Qt UI | ⬜ scaffold | `control_main` parity |
| 5 Ship / cutover | ⬜ prep | parity sign-off |

---

## Worker loops (`main.py` → `cpp/src/core/workers/`)

| Worker | C++ file | Capture | Match | Input | FSM | Parity |
|--------|----------|---------|-------|-------|-----|--------|
| `ride_loop` | `ride_worker.cpp` | ✅ | ✅ | CapsLock | detect toggle | 🟡 |
| `hp_refill_loop` | `hp_refill_worker.cpp` | ✅ | ✅ | VK key | cooldown | 🟡 |
| `reload_loop` | `reload_worker.cpp` | ✅ | ✅ | dblclick+digits | nobullet→bullet | 🟡 no vault |
| `ammo_restock_loop` | `ammo_restock_worker.cpp` | ✅ | ✅ | click+4/5/Enter | 3-step | 🟡 |
| `call_merc_loop` | `call_merc_worker.cpp` | ✅ | ✅ | click/dblclick | 4-phase + FT | 🟡 |
| `flame_trigger_loop` | `flame_trigger_worker.cpp` | — | — | RMB+merc keys | center hold | 🟡 no ClipCursor |
| `left_click_loop` | `worker_loops.cpp` | — | — | L-click | state gate | 🟡 basic |
| `right_hold_loop` | `worker_loops.cpp` | — | — | R-down | state gate | 🟡 basic |
| `kill_counter_loop` | `worker_loops.cpp` | — | — | — | — | ⬜ OCR TBD |
| `start_game_launcher_loop` | `worker_loops.cpp` | — | — | — | — | ⬜ sleep |

**Next:** `start_game_launcher` FSM → `kill_counter` OCR.

---

## Shared infrastructure

| Area | Python | C++ | Status |
|------|--------|-----|--------|
| Registry snapshot | `registry_config_snapshot.py` | `registry/snapshot.cpp` | ✅ |
| Vision capture | `vision_capture.py` | `vision/capture.cpp` | ✅ BitBlt |
| ROI scale | `scale_geometry.py` | `vision/roi.cpp` | ✅ |
| Template match | `template_matching.py` | `vision/template_match.cpp` | ✅ |
| Template load | `image_registry.py` | pybind loader | ✅ |
| AppState | `app_state.py` | `state/app_state.cpp` | 🟡 ~45 keys |
| Worker runtime | `worker_runtime_bridge.py` | `worker_runtime.cpp` | ✅ auto pyd |

---

## Verification

```powershell
python tools\export_registry_snapshot_keys.py
python tools\golden_registry_snapshot_diff.py
.\scripts\build_native_core.bat
```

---

**Last updated:** 2026-07-20 — call_merc + flame_trigger C++ ports
