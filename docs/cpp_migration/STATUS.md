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
| 2 Workers | 🟡 | 4/10 real logic; OCR/FSM gaps |
| 3 Native (DComp, hooks) | ✅ | — |
| 4 Qt UI | ⬜ scaffold | `control_main` parity |
| 5 Ship / cutover | ⬜ prep | parity sign-off |

---

## Worker loops (`main.py` → `cpp/src/core/workers/`)

| Worker | C++ file | Capture | Match | Input | FSM | Parity |
|--------|----------|---------|-------|-------|-----|--------|
| `ride_loop` | `ride_worker.cpp` | ✅ | ✅ | CapsLock | detect toggle | 🟡 manual S0 |
| `hp_refill_loop` | `hp_refill_worker.cpp` | ✅ | ✅ | VK key | cooldown | 🟡 manual |
| `reload_loop` | `reload_worker.cpp` | ✅ | ✅ | dblclick+digits | nobullet→bullet | 🟡 no vault phase |
| `ammo_restock_loop` | `ammo_restock_worker.cpp` | ✅ | ✅ | click+4/5/Enter | 3-step seq | 🟡 new |
| `left_click_loop` | `worker_loops.cpp` | — | — | L-click | state gate | ⬜ scaffold |
| `right_hold_loop` | `worker_loops.cpp` | — | — | R-down | state gate | ⬜ scaffold |
| `flame_trigger_loop` | `worker_loops.cpp` | — | — | R-down | suppress flags | ⬜ partial |
| `call_merc_loop` | `worker_loops.cpp` | — | — | — | — | ⬜ sleep |
| `kill_counter_loop` | `worker_loops.cpp` | — | — | — | — | ⬜ OCR TBD |
| `start_game_launcher_loop` | `worker_loops.cpp` | — | — | — | — | ⬜ sleep |

**Next port order:** `call_merc` → `flame_trigger` (full) → `left_click`/`right_hold` → `kill_counter` OCR → `start_game_launcher`.

---

## Shared infrastructure

| Area | Python | C++ | Status |
|------|--------|-----|--------|
| Registry snapshot | `registry_config_snapshot.py` | `registry/snapshot.cpp` | ✅ keys + typed getters |
| Vision capture | `vision_capture.py` | `vision/capture.cpp` | ✅ BitBlt; no mss |
| ROI scale | `scale_geometry.py` | `vision/roi.cpp` | ✅ BASE_HEIGHT 1440 |
| Template match | `template_matching.py` | `vision/template_match.cpp` | ✅ ccoeff_normed |
| Template load | `image_registry.py` | pybind `set_template_bgr_loader` | ✅ registry base64 |
| AppState | `app_state.py` | `state/app_state.cpp` + pybind | 🟡 ~40 keys |
| Worker runtime | `worker_runtime_bridge.py` | `workers/worker_runtime.cpp` | ✅ auto pyd |
| Reload FSM helpers | `reload_sequence.py` | `reload/sequence.cpp` | 🟡 clamp ammo only |

---

## Verification

```powershell
python tools\export_registry_snapshot_keys.py
python tools\golden_registry_snapshot_diff.py
# After build_native_core.bat:
cmake --build cpp/build/native --target pipela_golden_tests
```

---

## Local git (not pushed)

Recent migration commits on `main` (local only until cutover): Phase 2 deepening, auto native workers, ammo_restock worker — see `git log --oneline -5`.

**Last updated:** 2026-07-20 (ammo_restock C++ port + STATUS doc)
