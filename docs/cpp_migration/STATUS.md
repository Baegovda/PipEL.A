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
| 2 Workers | ✅ | 10/10 real logic; OCR via Python pybind bridge |
| 3 Native (DComp, hooks) | ✅ | — |
| 4 Qt UI | 🟡 scaffold | `PIPELA_QT_NATIVE=1` → C++ `Pipela.exe`; full `control_main` parity TBD |
| 5 Ship / cutover | 🟡 prep | parity sign-off + owner release |

---

## Worker loops (`main.py` → `cpp/src/core/workers/`)

| Worker | C++ file | Capture | Match | Input | FSM | Parity |
|--------|----------|---------|-------|-------|-----|--------|
| `ride_loop` | `ride_worker.cpp` | ✅ | ✅ | CapsLock | detect toggle | 🟡 |
| `hp_refill_loop` | `hp_refill_worker.cpp` | ✅ | ✅ | VK key | cooldown | 🟡 |
| `reload_loop` | `reload_worker.cpp` | ✅ | ✅ | dblclick+digits | nobullet→bullet+vault | 🟡 |
| `ammo_restock_loop` | `ammo_restock_worker.cpp` | ✅ | ✅ | click+4/5/Enter | 3-step | 🟡 |
| `call_merc_loop` | `call_merc_worker.cpp` | ✅ | ✅ | click/dblclick | 4-phase + FT | 🟡 |
| `flame_trigger_loop` | `flame_trigger_worker.cpp` | — | — | RMB+merc+ClipCursor | center hold | 🟡 |
| `left_click_loop` | `worker_loops.cpp` | — | — | L-click | in-window gate | 🟡 |
| `right_hold_loop` | `worker_loops.cpp` | — | — | R-down | in-window gate | 🟡 |
| `kill_counter_loop` | `kill_counter_worker.cpp` | ✅ | — | — | OCR pybind | 🟡 |
| `start_game_launcher_loop` | `start_game_launcher_worker.cpp` | ✅ | ✅ | click | 3-phase FSM | 🟡 |

---

## Shared infrastructure

| Area | Python | C++ | Status |
|------|--------|-----|--------|
| Registry snapshot | `registry_config_snapshot.py` | `registry/snapshot.cpp` | ✅ |
| Vision capture | `vision_capture.py` | `vision/capture.cpp` | ✅ BitBlt |
| ROI scale | `scale_geometry.py` | `vision/roi.cpp` | ✅ |
| Template match | `template_matching.py` | `vision/template_match.cpp` | ✅ |
| Template load | `image_registry.py` | pybind loader | ✅ |
| Kill counter OCR | `kill_counter_read_digits` | pybind `set_kill_counter_ocr_loader` | ✅ |
| Smart updater HWND | `win32_game_windows.py` | `win32/game_windows.cpp` | ✅ |
| ClipCursor | `win32_window_ops.py` | `win32/clip_cursor.cpp` | ✅ |
| AppState | `app_state.py` | `state/app_state.cpp` | 🟡 ~55 keys |
| Worker runtime | `worker_runtime_bridge.py` | `worker_runtime.cpp` | ✅ auto pyd |

---

## Verification

```powershell
python tools\export_registry_snapshot_keys.py
python tools\golden_registry_snapshot_diff.py
python tools\compare_native_python_workers.py --seconds 5
.\scripts\build_native_core.bat
```

---

**Last updated:** 2026-07-20 — workers 10/10 + launcher/KC/vault/FT/input polish
