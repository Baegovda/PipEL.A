# 도킹 UI 페이즈·상단 스트립·Intro Skip — 인수인계 (2026-04-25)

**대상:** 다음에 `pipela_qt` / `main` / 도킹·런처·스트립을 다루는 에이전트·개발자.  
**관련:** [`CODEMAP_AND_DOCS.md`](CODEMAP_AND_DOCS.md) §2·§3 — 구현: `pipela_qt/dock_ui_phase.py`.

---

## 1. UI 도킹 페이즈 (문자열·의미)

| 값 | 상수 | 의미 |
|----|------|------|
| `client` | `UI_DOCK_PHASE_CLIENT` | 이터널시티 **타겟** HWND가 있고 최소화 아님 — 앵커·패널 폭은 **게임** 기준. |
| `launcher` | `UI_DOCK_PHASE_LAUNCHER` | 게임이 없/비활·**스마트업데이터 런처**만 — 앵커·일부 UI 정책은 **런처** 기준. |
| `standby` | `UI_DOCK_PHASE_STANDBY` | 둘 다 없음·대기 — 문서/주석에서 **「대기 페이즈」**로 부름. (구 `"none"`은 제거.) |

- **실행:** `get_ui_dock_phase(pipela_mod)` — **순서: 클라 먼저 → 런처 → 대기.**
- **런타임 캐시:** `pipela_mod.pipela_ui_dock_phase` (`main.py` 기본값 **`"standby"`** + 주석) — `get_dock_panel_wh_for_current_phase` 등에서 갱신.
- **앵커(도킹 HWND):** `qt_dock_anchor.resolve_dock_anchor_hwnd` — **게임 우선**, 없으면 런처. (`resolve_game_only_anchor_hwnd` 는 게임만.)
- **호환:** 외부·구 코드가 `pipela_ui_dock_phase == "none"` 이면 **`"standby"`** 로 마이그레이션 필요.

**동시에 게임+런처가 둘 다 잡힌 경우:** `get_ui_dock_phase`는 **항상 `client`**. (게임 창이 유효·비최소화면 런처는 페이즈 판정에 쓰이지 않음.) 앵커도 **게임 HWND**.

---

## 2. `pipela_qt/dock_ui_phase.py` — API 요약

| 심볼 | 역할 |
|------|------|
| `get_ui_dock_phase` | 위 표의 문자열 반환, `pipela_ui_dock_phase` 갱신(일부 API에서). |
| `get_dock_panel_wh_for_current_phase` | `launcher` → 좁·낮은 상한 `_launcher_dock_ui_wh`, 그 외 `dock_panel_size` 기반. |
| `is_start_game_launcher_template1_effective_on(pipela_mod, snap=None)` | **Intro Skip / 런처 START(템플릿①)** “감지·루프 ON”인지. `snap`이 있으면 레지 `start_game_launcher_active` + 페이즈, `None`이면 **모듈 값만** + 페이즈(제어창 `style_state` 등 경량 경로). `True` = 설정 ON **또는** `launcher` 페이즈(런처에 붙은 동안 **항시 감지**). |

---

## 3. 런처 페이즈 — 상단 스트립 가로·캡션 버튼 (게임 타이틀 바 `QtGameTitleBarStrip`)

**문제:** 제어창이 클라이언트 왼쪽에 스냅되면, 스트립 **왼 끝**이 런처 **외곽 왼**보다 더 왼쪽으로 나갈 수 있음.  
**해결:** `_compute_strip_geometry`에서 `get_ui_dock_phase(m) == launcher`이면 **제어창/킬/kill 확장/스냅 보정 없이** 런처 **외곽** `[ol, o_right]` 만 사용해 `(x, y, width, bar_h)` 반환.  
**파일:** `pipela_qt/game_title_bar_overlay.py`.

**캡션:** 런처 페이즈에서는 **최대화** 대신 **설정** 아이콘(`icon/gear.png`) 버튼을 쓴다(`_sync_strip_max_vs_settings_buttons`). 클릭 시 `PipelaQtMainWindow.open_settings_from_launcher_title_strip()` — 설정 탭·허브 스택은 클라이언트와 동일(`_on_breadcrumb_goto_hub`). 킬 float 없이 제어만 런처에 도킹하려면 `_launcher_strip_settings_mode` 로 런처 전용 숨김 정책을 예외 처리한다(`_sync_launcher_phase_docked_chrome`).

---

## 4. 런처 페이즈 — Intro Skip / 템플릿①(런처 START) “항시 감지”

- **백엔드 루프:** `main.start_game_launcher_loop` — `start_game_launcher_active` 스냅이 꺼져 있어도 **`is_start_game_launcher_template1_effective_on(_pipela_mod, snap)`** 이 True면 루프 지속(대기·aborted·2차 클릭 전 점검 동일). **런처만 있는 기동**이면 `_pipela_bootstrap_pre_ui`에서 `start_game_launcher_active`를 True로 맞추고 스냅샷을 갱신하며, 루프 스레드는 **`main_qt`에서 Qt `exec` 전**에 `_ensure_start_game_launcher_loop_thread()`로 올려 기동 직후부터 매칭한다.  
- **UI:** `pipela_qt/panels/start_game_settings.py` — 토글을 **효과적 ON**(`is_…_effective_on`)에 맞춤; **런처 페이즈**에서는 **켜진 상태**로 보이고 **스위치 비활성**(끄면 `_commit_cb`에서 저장 안 함 + 재동기).  
- **제어창 토글 스타일 갱신:** `control_main` `style_state`에 `m.start_game_launcher_active` 대신 **`is_start_game_launcher_template1_effective_on(m, None)`** 사용.

---

## 5. 런처 페이즈 — 제어창·킬 창 숨김 (상단 스트립만)

**요구:** 런처에 붙은 동안 **상단 스트립만** 보이고, **메인 제어창**(`PipelaQtMainWindow`)·**킬 float** 는 숨김.

| 위치 | 동작 |
|------|------|
| `PipelaQtMainWindow._sync_launcher_phase_docked_chrome` | `launcher` → kc `hide`, 메인 `hide`. 아니고 ×로 닫지 않았으면 숨겨 있으면 `show`/`showNormal` + `raise_` + `dock` 타이머. |
| `_refresh` | `get_ui_dock_phase` / `_resync_dock_w_for_ui_phase` 직후 **`_sync_launcher_phase_docked_chrome()`** 호출. |
| `__init__` (非 tray) | `self.show()` 직후 **`_sync_launcher_phase_docked_chrome()`** — 런처만 있을 때 첫 프레임 깜빡임 완화. |
| `_sync_kill_counter_window` | **맨 앞**에서 `launcher`면 kc `hide` 후 `return` (이터널시티 킬 도킹 경로 미실행). |
| `_bring_qt_control_to_front` | `isHidden()` 이면 return (런처로 숨긴 뒤 `singleShot` 이 앞으로 못 끌어올림). |
| `pipela_qt/dock_chrome_restore.py` | `restore_pipela_docked_chrome_if_needed` — `get_ui_dock_phase == launcher` **즉시 False** (스트립/게임 복원이 제어·킬을 런처에서 다시 띄우지 않게). |

**트레이 «제어창 표시»:** `win.show` 후 다음 틱 `_refresh`가 다시 `_sync_launcher_phase_docked_chrome` → 런처면 **또 숨김** (의도: 런처 붙은 동안은 본체만 띄우지 않음).

**미조정 (의도):** `QtGameOverlay` 등 다른 오버레이는 이 정책에 포함하지 **않음** — “메인+킬”만.

**대기(standby):** 게임·런처 HWND가 모두 없어지면 상단 스트립은 숨김(`game_title_bar_overlay._move_hidden`). 제어창은 `PipelaQtMainWindow._dock_to_anchor`가 앵커 없을 때 `_dock_to_standby_centered`로 주 모니터 작업 영역 **중앙**에 두어, 런처 도킹 잔상 좌표에 “덜렁” 남지 않게 한다.

**런처→클라이언트:** `control_main._refresh`에서 `pipela_ui_dock_phase`가 바뀔 때 **`_sync_launcher_phase_docked_chrome`(메인 `show`) → 스트립 `invalidate_chrome_layout` → `_resync_dock_w_for_ui_phase`** 순서(예전: resync가 먼저라 히든 채 dock 스케줄·스트립이 제어 HWND 없이 기하 계산). 복원 분기에서 `pipela_qt_control_win_hwnd` 갱신 후 즉시 `_dock_to_anchor(force=True)`. 스트립 `_tick`은 앵커 HWND가 바뀌면 `_last_geom_sig`를 지워 전환 직후 엉성한 폭/위치가 남지 않게 한다.

---

## 6. 체크리스트(변경 시)

- [ ] `dock_ui_phase`에 페이즈·`is_start_game_…` 시그니처 바꾸면: `main` 루프, `start_game_settings`, `control_main`, `dock_chrome_restore` **동시** 확인.
- [ ] 스트립 기하(런처)는 **외곽** 기준; 게임+킬·제어창 `GetWindowRect` 는 **다른** 페이즈.
- [ ] `PIPELA_STRIP_DISPLAY_VERSION` — AGENTS.md 정책(묶음당 한 단계 등) 준수.

---

## 7. 변경 이력 (이 문서)

| 날짜 | 내용 |
|------|------|
| 2026-04-25 | 최초: 대기(standby) 명칭, 런처 스트립 폭, 템플릿① 런처 강제 ON, 런처에서 제어·킬 숨김, 게임vs런처 우선순위 메모. |
