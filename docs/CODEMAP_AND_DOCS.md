# CODEMAP & 문서 — 에이전트·인간 공용

**역할:** 저장소를 처음 보는 에이전트(또는 사람)가 **어느 파일에 무엇이 있는지** 빠르게 잡을 수 있게 한다.  
**최우선 인수인계(정책·이행·진행도)는** [`MIGRATION_HANDOFF.md`](MIGRATION_HANDOFF.md) — 본 문서는 **탐색 맵**과 **갱신 규칙**에 집중한다.

**마지막 갱신:** 2026-04-26 — **프로파일링** [`docs/PROFILING_AND_TROUBLESHOOTING.md`](PROFILING_AND_TROUBLESHOOTING.md) §2 · `tools/profile_pipela.ps1` (cProfile만)

- [`docs/DOCK_UI_PHASE_HANDOFF.md`](DOCK_UI_PHASE_HANDOFF.md) — **도킹 UI 페이즈**(`client`/`launcher`/`standby`), 상단 스트립(런처 외곽 맞춤), Intro Skip 템플릿① 런처 강제 ON, 런처에서 제어·킬 숨김, 복원 방지 — **인수인계 한 장**
- [`docs/PROFILING_AND_TROUBLESHOOTING.md`](PROFILING_AND_TROUBLESHOOTING.md) — **프로파일링·트러블슈팅 정책** (cProfile, AI `PIPELA_AI_DEBUG`, 에이전트 운용, 링크 허브)
- [`docs/UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md) — **UI 스터터링** 재현·환경·S0~S5, 결과 표 (1단계)

---

## 1. 한 눈에: 디렉터리

| 경로 | 내용(한 줄) |
|------|----------------|
| [`main.py`](../main.py) | 앱·`pipela_mod` 본체: 전역, 레지, **워커/매크로 루프**, pynput, `load`/`save`, Qt가 부르는 API |
| [`pipela_qt/`](../pipela_qt/) | **전 제품 UI** (PyQt6): 제어창, 설정 패널, 오버레이, 드래그 캡처, 트레이, 셸 기동 |
| [`pipela_core/`](../pipela_core/) | **UI와 무관한** 순수/Win32/레지/비전·템플릿·스냅샷 모듈 (모듈 표는 MIGRATION 본문) |
| [`Pipela.spec`](../Pipela.spec) | PyInstaller — `hiddenimports`·datas |
| [`requirements-dev.txt`](../requirements-dev.txt) | **선택** 개발 의존성(현재 비어 있음; 필요 시 추가) — `pip install -r requirements-dev.txt` |
| [`tools/profile_pipela.ps1`](../tools/profile_pipela.ps1) | **cProfile** 래퍼 → `profiling/pipela_cprofile_*.stats` |
| [`docs/MIGRATION_HANDOFF.md`](MIGRATION_HANDOFF.md) | 이행·축 A/B·`pipela_core` 모듈 표·**실시간 진행판** (작업 끝마다 갱신) |
| [`docs/PROFILING_AND_TROUBLESHOOTING.md`](PROFILING_AND_TROUBLESHOOTING.md) | **cProfile·AI 세션 로그** 환경·정책, [`UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md)와 역할 구분 |
| [`pipela_qt/roadmap.py`](../pipela_qt/roadmap.py) | Qt 기능 단계 체크리스트 P01–P15, `roadmap.summary()` |
| 루트 [`AGENTS.md`](../AGENTS.md) | 에이전트 **필독** 목록·작업 시 규칙 |
| [`docs/UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md) | **UI 끊김** 재현 S0~S5·결과 표 |

표준 `tkinter` / `pipela_legacy_tk` **미사용** (2026-04).

---

## 2. Qt UI — 주요 파일 (탐색용)

| 영역 | 파일 | 비고 |
|------|------|------|
| 기동 | `pipela_qt/shell.py` | `run_qt_application(pipela_mod, …)` — 오버레이·HUD·제어창·트레이; **`QApplication`**; **`pipela_mod._qt_control_main`**; **AI/지원 로그**(`pipela_core/ai_debug_session_log`) |
| 제어창(메인 윈도우) | `pipela_qt/control_main.py` | `PipelaQtMainWindow` — 토글·터미널·설정 스택, **앵커 클라이언트 왼 도킹**; **`_sync_launcher_phase_docked_chrome`** — **런처 UI 페이즈**에서 제어·킬 숨김(상단 스트립만); 설정 탭 **경로(`echBreadcrumbSeg`)** 클릭 → 허브/해당 패널 |
| 도킹 UI 페이즈·런처 START 효과 ON | `pipela_qt/dock_ui_phase.py` | `get_ui_dock_phase`, `get_dock_panel_wh_for_current_phase`, **`is_start_game_launcher_template1_effective_on`** — [`DOCK_UI_PHASE_HANDOFF.md`](DOCK_UI_PHASE_HANDOFF.md) |
| 설정 허브·카드 | `pipela_qt/main_window.py` | `HubCard`, `HUB_ENTRIES`, `configure_app` |
| 게임맞춤 투명 오버레이 | `pipela_qt/overlay.py` | `QtGameOverlay` |
| 게임 타이틀 덮는 상단 바 | `pipela_qt/game_title_bar_overlay.py` | `QtGameTitleBarStrip` — Win32 **소유 창**으로 앵커보다 위; **런처 페이즈**에서는 **앵커(런처) 외곽 가로**에만 맞춤; 그 외에는 제어창 **왼**~킬 **오른**(`GetWindowRect`, 킬이 보이면 `right` 확장) |
| 도킹 크롬 복원 | `pipela_qt/dock_chrome_restore.py` | `restore_pipela_docked_chrome_if_needed` — **런처 페이즈**에서는 복원 안 함(제어·킬이 런처에서 다시 뜨지 않게) |
| 커서 HUD / 플레임 배너 | `pipela_qt/cursor_hud.py` | `pipela_mod` 전역, `_format_flame_*` 는 **`main`** |
| 감지 펄스·킬/템플릿 디버그 | `pipela_qt/debug_pulse_overlay.py` | |
| 영역/템플릿 드래그 | `region_drag_overlay.py`, `template_drag_overlay.py` | `pipela_mod` 콜백 |
| ROI 미리보기 | `region_preview_overlay.py` | |
| 템플릿 캡처 확인 | `template_capture_confirm.py` | |
| 터미널·킬·설정 패널 | `pipela_qt/panels/*.py` | 패널별 `*SettingsPanel`, `kill_counter_panel` |
| 캡처 툴바 연동 | `pipela_qt/qt_capture.py` | `pipela_mod.start_region_select` 등 |
| 테마(색) | `pipela_qt/theme.py` | `main` `SETTINGS_*`와 숫자 맞출 것 |
| 셸 QSS(허브·제어창 공통) | `pipela_qt/app_shell.py` | `main_hub_window_qss`, `control_frameless_window_qss`, `settings_breadcrumb_chrome_qss`, `settings_hub_entry_button_qss` 등 — **메인 허브와 제어창 크롬 단일 출처** |
| 제어창 터미널/설정 탭바 | `pipela_qt/control_tab_chrome.py` + `app_shell` `control_frameless_window_qss` | `QTabWidget#pipelaMainTabs` — `SURFACE`·하단 1px 구분 + 선택 탭 2px 액센트, 패딩·`PairedControlTabBar` / `_ClusterTabLabelStyle` |
| 앱/실행 보조 | `pipela_qt/app.py`, `update_helpers.py`, **`dpi.py`** | `init_high_dpi()` — `QApplication` **앞**; `hub_window_size`·`dock_panel_size`; **`get_dock_panel_wh(pipela_mod)`** — 메인·킬 패널 공통 `qt_dock_panel_w/h`; **`win32_dpi_scale_for_hwnd`** |

---

## 3. `main` (`pipela_mod`) — 무엇을 보나

- **진입:** `main_qt()` → `pipela_qt.shell.run_qt_application` (파일 끝 `if __name__ == "__main__"`).
- **도킹 UI 런타임(레지 아님):** `pipela_mod.pipela_ui_dock_phase` — `standby` \| `launcher` \| `client` (`get_ui_dock_phase`와 동기). 구 `"none"` 은 `standby` 로 바뀜. 상세: [`docs/DOCK_UI_PHASE_HANDOFF.md`](DOCK_UI_PHASE_HANDOFF.md).
- **워커/루프(이름 힌트):** `left_click_loop`, `right_hold_loop`, `flame_trigger_loop`, `ride_loop`, `hp_refill_loop`, `reload_loop`, `ammo_restock_loop`, `call_merc_loop`, `kill_counter_loop`, `start_game_launcher_loop` … — `main.py`에서 `grep`으로 검색. *Start Game 런처(템플릿①):* 레지 `start_game_launcher_active` 또는 **런처 UI 페이즈**이면 `is_start_game_launcher_template1_effective_on` 으로 루프 **ON** (페이즈별 정책은 `dock_ui_phase`). 클릭·소멸·재시도: **1클릭** → `START_GAME_LAUNCHER_POST_CLICK_DISAPPEAR_WAIT_SEC`(5s) 내 런처 **소멸** 시 Intro Skip 무장; 아니면 **1회** 재클릭·동일 대기(2클릭 후에도 유지면 쿨다운, burst 없음).
- **레지/설정:** `load_config`, `save_config`, `schedule_save_config` / `flush_save_config_debounced` (Qt `QTimer` 경로).
- **HUD·오버레이가 읽는 전역/함수:** 예) `flame_trigger_*`, `get_window_rect`, `refresh_*_hwnd`, `_format_flame_trigger_runtime_hms` 등 — Qt는 **`import main as m`** / `pipela_mod`로 접근.
- **지원/AI 디버그(선택):** Qt 기동 후 `pipela_mod.AI_DEBUG_LOG_PATH` — `%LOCALAPPDATA%\\Pipela\\ai_debug\\` 세션 파일(`PIPELA_AI_DEBUG=0` 으로 끔).
- **Win32:** `pipela_core.win32_*` re-export 또는 `main`에서 쓰는 래퍼(실제는 코어).

새 **UI**는 `pipela_qt`에 두고, 백엔드만 `m.xxx` 또는 `pipela_core` 직접 import.

---

## 4. `pipela_core` — 상세 모듈 표

**단일 출처:** [`MIGRATION_HANDOFF.md` » «`pipela_core` 모듈»](MIGRATION_HANDOFF.md) 표를 본다. 여기에 모듈을 **추가**할 때는 그 표에 **같이** 한 줄 넣는다.

---

## 5. 갱신 규칙 (계속 쓸 것)

### 5.1 누가 갱신하나
- **코드/문서를 고친 사람**이, 해당 범위에 맞는 문서를 **같은 PR·같은 작업 단위**에서 갱신한다.

### 5.2 `docs/MIGRATION_HANDOFF.md` (필수 조건: 기존 규칙)
- **매 작업(또는 PR) 종료** 시 맨 위 **«실시간 진행판»** (최종 작업, 누적 %, TODO, 날짜).
- `pipela_core`에 **새 파일**이 생기면 본문 **«`pipela_core` 모듈»** 표에 **한 줄**.
- **전략/방향**이 바뀌면 «방향성」 절 수정.

### 5.3 본 문서 `CODEMAP_AND_DOCS.md` (구조·탐색이 바뀔 때)
다음이면 **반드시** 이 파일도 손볼 것:
- **새로운** `pipela_qt` 최상위 모듈·**새 설정 패널** 파일(탐색 표 §2).
- **기동 순서/역할**이 바뀜 (`shell` 연쇄, 새 창/오버레이).
- `main`의 **새 퍼블릭 `pipela_mod` API** (다른 모듈이 `m.xxx`로 쓰는 것) — §3에 **한 줄** 요약.
- **진입점**·PyInstaller spec **이름/역할** 변경.

**권장(작게라도):** UI·워커 **큰 이전**이 끝나면 §2/§3에 한 문장씩 반영.  
**맨 위 `마지막 갱신` 날짜**를 바꾼다.

### 5.4 `AGENTS.md` / `pipela_qt/roadmap.py`
- 루트 **AGENTS.md** — 새 **필독 문서**·금지/원칙이 생기면 여기 **링크**를 추가/수정.
- **기능 완료 단계**는 `pipela_qt/roadmap.py` `QT_MIGRATION_PHASES` (필요 시에만 Pxx 추가, 중복은 피할 것).

### 5.5 중복 방지
- **모듈 전체 나열**은 MIGRATION 한 곳(표)이 **마스터** — CODEMAP은 **빨리 찾는 길**과 **갱신 트리거**만.
- `killcount.md` 등 **참고용** 문서는 **코드 진실의 원천이 아님** — 수치/동작은 `main` / `pipela_qt` / `pipela_core` 기준.

### 5.6 [`PROFILING_AND_TROUBLESHOOTING.md`](PROFILING_AND_TROUBLESHOOTING.md)
- **cProfile·AI 세션 로그** 정책·환경 변수 요약·에이전트 운용은 이 문서가 **허브**.  
- `ai_debug_session_log` **동작·경로**를 바꾸면 본 문서 **§1 표**와 `AGENTS.md` 필독 목록을 같이 맞춘다.

---

## 6. 변경 이력 (요약, 최근만)

| 날짜 | 내용 |
|------|------|
| 2026-04-25 | **`DOCK_UI_PHASE_HANDOFF.md` 추가** — 도킹 페이즈(standby/명칭), 런처 스트립 가로, Intro Skip 템플릿①·런처에서 제어·킬 숨김, `dock_chrome_restore` 가드. §2·§6 표 보강. |
| 2026-04-25 | `PROFILING_AND_TROUBLESHOOTING.md` — §1 링크 + 표 + §5.6. |
| 2026-04-23 | 최초 작성 — 디렉터리·Qt 파일 표·`pipela_mod`·갱신 규칙. |
| 2026-04-23 | §7 추가 — 125% DPI 도킹 시 가로 축소·소실 버그 원인(물리/논리 혼용·`self.width()`) 및 해결(`_dock_w`, `win32_dpi_scale_for_hwnd`). |
| 2026-04-23 | §7 보강 — 125%에서 게임 모서리 **침범** 방지: `dock_outer_rect_touch_client_*` 끝점 스냅, 도킹 시 `setFixedWidth(w_log)`. |

(이 표는 **구조에 영향 주는** 변경이 있을 때마다 1~2문장으로 추가한다.)

---

## 7. Qt 제어창·킬패널 도킹과 Windows DPI (증상·원인·해결)

Windows 표시 배율을 **125%** 등으로 올린 뒤, 제어창이 게임 클라이언트에 붙으면서 **가로 폭이 점점 줄어들다가 안 보이게 되는** 문제가 있었다.

### 7.1 무엇이 문제였나

- 게임 창 위치는 Win32 `GetWindowRect` / `GetClientRect` + `ClientToScreen` 경로로 얻으며, 좌표는 **물리 화면 픽셀**(모니터 DPI 기준)이다.
- 도킹 폭을 **`self.width()`**(Qt 위젯 폭)로 잡으면, Per-Monitor DPI 인식 프로세스에서 이 값은 **논리(DIP)에 가까운** 해석과 Win32 `SetWindowPos`에 넘기는 **물리** 단위가 한 식 안에서 섞인다.
- `setGeometry`와 `win32_set_window_outer_rect`(`SetWindowPos`)를 짧은 주기로 반복할 때, 그 차이가 **매 프레임 폭을 조금씩 깎는 피드백**으로 이어질 수 있다. 배율이 100%에 가까울 땐 덜 드러나고, **125%**처럼 스케일이 커지면 증상이 뚜렷해진다.
- **모서리 침범(겹침)**: `clamp_rect_to_monitor_work_area`만 쓰거나 `round(논리폭×scale)`만 물리 폭으로 쓰면, 125%에서 **1px~수 px** 단위로 UI 외곽이 게임 **클라이언트** 안으로 들어가 보일 수 있다. 100%에서는 물리·논리가 거의 같아 덜 보인다.

### 7.2 어떻게 해결했나

1. **설계 폭 고정**  
   기동 시 `dock_panel_size()`로 정한 논리 폭을 **`self._dock_w`**에 저장하고, 도킹 계산에는 **`self.width()`를 쓰지 않는다.**

2. **앵커 모니터 DPI로 물리 ↔ 논리 분리**  
   [`pipela_qt/dpi.py`](../pipela_qt/dpi.py)의 **`win32_dpi_scale_for_hwnd(pipela_mod, anchor_hwnd)`** 로 앵커가 올라간 모니터의 effective DPI÷96(`scale`)을 구한다.
   - **목표 물리 폭** 후보: `fw_phys ≈ round(_dock_w * scale)` (하한 적용).
   - **끝점 스냅(침범 방지)**: [`pipela_core/win32_window_ops.py`](../pipela_core/win32_window_ops.py) **`dock_outer_rect_touch_client_left`** / **`dock_outer_rect_touch_client_right`** — 제어창은 Win32 **외곽 오른쪽** = 게임 클라 **왼**(물리), 킬패널은 **외곽 왼쪽** = 클라 **오른**이 되도록 `x = max(wl, snap−w_t); w = snap−x` 식으로 폭을 **역산**해 모서리를 정확히 맞춘다(`get_monitor_work_rect_phys`로 `rcWork` 사용).
   - Win32 최종 배치: `win32_set_window_outer_rect(hwnd, x_phys, y_phys, fw_phys, fh_phys)`.
   - Qt: `setFixedWidth(w_log)` 후 `setGeometry` — `w_log`·`h_log`는 `fw_phys/scale`, `fh_phys/scale` 등으로 **조정된 물리 크기**와 맞춘다(고정 폭이 스냅된 물리 폭과 어긋나지 않게).

3. **적용 위치**  
   - 제어창: [`pipela_qt/control_main.py`](../pipela_qt/control_main.py) `_dock_to_anchor`  
   - 킬 카운터: [`pipela_qt/kill_counter_window.py`](../pipela_qt/kill_counter_window.py) `dock_to_right_of_target_game` — 프레임리스 외곽 QSS는 [`app_shell.kill_counter_floater_window_qss`](../pipela_qt/app_shell.py)(`frameless_outer_window_qss("echKcFrameless")` = 제어창 `echFramelessMain` 과 동일 1px)

### 7.3 관련 (UI 적응형·고해상도)

- **`init_high_dpi()`**: `QApplication` 생성 **전**에 호출(`pipela_qt/shell.py`) — 분수 배율에서 반올림·흐림 완화.
- **스타일시트 글꼴**: `font-size` 는 `px` 대신 **`pt`** 로 통일해 DPI에 맞게 보이게 함(별도 작업).

듀얼 모니터·모니터별 배율이 다른 환경에서는, 앵커와 **같은 모니터** 기준으로 위 변환이 맞는 경우가 대부분이다. 이후 다른 증상이 있으면 그 환경을 기준으로 보강한다.

---

## 8. 빠른 grep

- **워커 루프:** `def .*_loop\(` in `main.py`
- **레지 키:** `pipela_core/config_registry_*`, `config_parse`
- **Qt가 호출:** `pipela_mod.`, `self._pl.`, `m.` in `pipela_qt/`
- **Flame HUD 포맷:** `main` `_format_flame_`
- **도킹·DPI:** `win32_dpi_scale_for_hwnd`, `dock_outer_rect_touch_client_left`, `dock_outer_rect_touch_client_right`, `_dock_to_anchor`, `dock_to_right_of_target_game`
