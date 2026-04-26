<!--
  에이전트 규칙: 작업(커밋/PR) 끝날 때마다 **이 블록을 맨 위에 유지**하고 아래를 갱신한다.
  - 최종 작업: 이번에 한 일 1~3문장
  - 누적 완료 %: **축을 둘로 나눠** 표기(아래 진행판). 축 A=코어·스냅샷·워커 정렬, 축 B=**제품 UI·레거시 제거(Qt 단일·스텁 없음)**.
  - 남은 TODO: 체크리스트, 끝난 항목은 제거하거나 [x]
  - 남은 %: (100 − 누적 완료) 한 줄 + 아래 «남은 구성비」는 참고용
-->
## 실시간 진행판

| | |
|:---|:---|
| **최종 작업** | **클라이언트 페이즈 상단 스트립:** 킬창 끄면 가로 `right` 를 게임 **외곽** `o_right`로 두어 DWM 프레임만큼 오른으로 살짝 나왔음 → **클라이언트** `cr[2]` 기준(킬 켤 때는 기존처럼 `kr` 확장). `PIPELA_STRIP_DISPLAY_VERSION` **0.9.12**. |
| **누적 완료 (축 A)** | **`main` 슬림화·`pipela_core`·레지 스냅샷·워커 정렬** 기준 **100%** *(아래 완료 기준 참조)* |
| **누적 완료 (축 B)** | **제품 UI·import·빌드: 레거시 GUI 없음** (2026-04-23). (선택) `main`→`pipela_core` **추가 이전**. |
| **남은 TODO** | `[x]` **P01–P15** · `[x]` **소스/문서 Tk 흔적 정리(이번)** · `[ ]` (선택) **`main` 대형 로직 `pipela_core` 이전** |
| **남은 비중** | **축 A·B 핵심 완료** — (선택) 코어 이전·유지보수. |

**마지막 갱신:** 2026-04-26 (클라 스트립 가로: 클라이언트 오른끝 `cr[2]`; strip 0.9.12)

### 이번 인수인계 요약 (2026-04-25 — 도킹/런처/Intro Skip)

- **한 장 요약:** [`docs/DOCK_UI_PHASE_HANDOFF.md`](DOCK_UI_PHASE_HANDOFF.md) (페이즈 문자열, API 표, 런처 스트립·템플릿①·제어·킬 숨김, 외부 `"none"` → `"standby"`).
- **페이즈:** `pipela_mod.pipela_ui_dock_phase` = `standby` \| `launcher` \| `client` — `get_ui_dock_phase` = 게임(비최소) 우선 → 런처 → 대기. 상수: `UI_DOCK_PHASE_STANDBY` / `…_LAUNCHER` / `…_CLIENT` (`pipela_qt/dock_ui_phase.py`).
- **런처 상단 스트립 가로:** `game_title_bar_overlay._compute_strip_geometry` — `launcher`면 앵커 **클라이언트** `cr` (가로·`x`), 제어창 `GetWindowRect` 왼쪽 사용 안 함(왼으로 삐짐 방지).
- **클라이언트 상단 스트립 가로:** 같은 함수 — `right` 는 **`cr[2]`**(클라이언트 오른끝); 킬 패널이 보이면 `max(…, kr)` 로 킬 오른쪽까지. 킬 끄면 **외곽** `o_right`만 쓰지 않음(DWM만큼 안 나옴).
- **Intro Skip / 런처 START(템플릿①):** `is_start_game_launcher_template1_effective_on` — `start_game_launcher_active` (스냅) **또는** `launcher` 페이즈. `start_game_launcher_loop`·`_wait_…`·설정 토글·`control_main` `style_state` 연동. 런처면 설정 스위치 **고정·비활성** (`start_game_settings.py`).
- **런처에서 UI:** `_sync_launcher_phase_docked_chrome`, `_sync_kill_counter_window` 선행, `restore_pipela_docked_chrome_if_needed`에서 런처 **즉시 return**, `_bring_qt_control_to_front`는 `isHidden` 시 no-op, 기동 `show` 직후 동기 1회.

### 이번 인수인계 요약 (2026-04-23 세션)

- **설정 패널:** `pipela_qt/panels/settings_chrome.py`로 타이포·구분선·가로 유동 행(`add_settings_field_row` 등) 통일. Ammo/Call Merc/Intro Skip/Tesseract/업데이트·기타 패널 반영. Tesseract는 허브 **맨 아래**·도움말 콜아웃 UI.
- **제어창:** 터미널 탭 아이콘 `UI_ICON_TERMINAL_PATH` → `icon/terminal.png`. 설정 허브·경로는 `main_window.HUB_ENTRIES` / `control_main._update_settings_breadcrumb`. 로그 뷰는 `ResizableTerminalLog` + `pipela_qt/terminal_log_html.py` (실제 `stdout` 문자열은 기존처럼 `[태그]` 유지).
- **스트립 버전:** `PIPELA_STRIP_DISPLAY_VERSION` **0.6.19** (탭 패인). **0.6.18** DPI 간격. **0.6.17** 스트립 `·` 제거.
- **제어창 해상도 줄:** **클라** / **템플릿** / **DPI**. 한 줄·DPI 분리 2줄 후에도 넘치면 **플로우 줄바꿈**(`_res_flow_wrap`). 가용 폭은 `echBody` 레이아웃 기준(라벨 width로 축소하지 않음), `setMaximumWidth`·`setWordWrap(True)`·도킹 후 `QTimer`로 재맞춤.
- **대표 아이콘:** `PIPELA_APP_ICON_PATH` = `icon/vaultboy.png`. `pipela_qt/qt_icons.py`, `shell.py`에서 `qt_application_icon()` + `app.setWindowIcon`. 루트 **`Pipela.ico`** 는 vaultboy 기준으로 재생성(PyInstaller `Pipela.spec` 의 `icon=`). **`shell.py`** 에서 `_app_icon` 미정의로 트레이 크래시 나던 부분은 `configure_app` 직후 아이콘 할당으로 복구됨.
- **킬 카운터 패널:** 소제목 `settings_section_heading_style`, 상단 `margin-top` 은 `scale_px(4)`. ROI 한 줄 툴바는 `apply_panel_toolbar_button_chrome`(`panel_toolbar_button_qss` + 폭 연동 패딩). 랩·세션은 `panel_secondary_button_qss` / `panel_primary_button_qss`. `qt_capture.attach_kill_counter_region_toolbar`·`attach_template_toolbar` 동일.
- **버그픽스:** `pipela_qt/scrub_spinboxes.py` — PyQt6 에서 `stepBy(QAbstractSpinBox.StepType.StepUp)` 대신 **`stepBy(1)` / `stepBy(-1)`**. `hp_refill_settings`(및 유사) **`DragDoubleSpinBox`** import 누락 시 `NameError` — `pipela_qt.scrub_spinboxes` 에서 import.
- **프레임리스·아이콘:** `FramelessWindowHint` 를 쓰는 **제어창**(`pipela_qt/control_main.py`, `kill_counter_window.py`)은 **`setWindowIcon` 을 플래그 설정 전에** 호출 — OS 타이틀바에는 아이콘이 없을 수 있어도 **작업 표시줄·전환기** 등은 앱/창 아이콘을 따른다. `QApplication.setWindowIcon` 은 `pipela_qt/shell.py` (`configure_app` 직후). **오버레이·Tool 전용** 창은 작업 표시줄에 안 뜨는 경우가 많음 — 메인·제어창 쪽이 기준.
- **빌드:** 대표 PNG(`PIPELA_APP_ICON_PATH`)를 바꾸면 루트 **`Pipela.ico`** 를 그에 맞게 재생성하고 **`Pipela.spec`** 의 `EXE(..., icon=['Pipela.ico'])`·`datas` 포함을 확인한다.

### 다음 에이전트용 프롬프트 (새 채팅에 붙여 넣기)

아래 전체를 복사해 사용하면 된다.

```
Pipela 저장소(루트 AGENTS.md, docs/MIGRATION_HANDOFF.md 실시간 진행판) 기준으로 작업한다.

맥락:
- 프로파일·트러블슈트: `docs/PROFILING_AND_TROUBLESHOOTING.md` — **cProfile** + `PIPELA_AI_DEBUG`(세션 로그), `docs/UI_STUTTER_REPRO_SCENARIOS.md` 재현.
- Qt 단일 UI(`pipela_qt` + `pipela_mod`). 설정 패널 공통은 `pipela_qt/panels/settings_chrome.py`.
- 대표 아이콘: `pipela_core/paths.py` 의 `PIPELA_APP_ICON_PATH`(현재 icon/vaultboy.png), `pipela_qt/qt_icons.py`, `shell.py` 에서 앱/트레이 아이콘. EXE 아이콘은 루트 Pipela.ico(스펙 Pipela.spec).
- 드래그 스크럽 스핀박스: `pipela_qt/scrub_spinboxes.py` — stepBy는 정수 1/-1만 사용(PyQt6). 새 패널에서 DragDoubleSpinBox 쓰면 반드시 `from pipela_qt.scrub_spinboxes import DragDoubleSpinBox`.
- 스트립 표시 버전은 AGENTS.md 빈도 규칙 준수; 묶음당 과도한 patch 올리지 말 것.

할 일(우선순위는 요청에 맞게 조정):
1) 변경 전 docs/MIGRATION_HANDOFF.md 맨 위 진행판·날짜 갱신(AGENTS.md 규칙).
2) UI 추가 시 settings_chrome 패턴·scale_px·T.spt 유지. 툴바 버튼은 panel_*_button_qss 재사용 또는 동일 체계로 확장.
3) 프레임리스 제어창은 OS 타이틀바 아이콘이 없을 수 있음 — 작업 표시줄·setWindowIcon 기준.
4) PyInstaller 빌드 시 아이콘 바꾸면 Pipela.ico 재생성 후 스펙 확인.

지금부터: [여기에 구체적 요청을 적는다]
```

---

# Pipela — Qt 단일 UI·코어 분리 인수인계

**마지막 업데이트:** 2026-04-23 (스크롤바·진행판)  
**이 문서를 고친 사람은 맨 위 «실시간 진행판»과 본문 표·날짜를 함께 갱신할 것.**

---

## 누가 읽나

- Cursor / Codex 등 **코드 에이전트**: `main.py`, `pipela_qt/`, `pipela_core/`를 건드리기 **전에** 이 파일을 읽는다. **코드가 어디 있는지(탐색):** [`CODEMAP_AND_DOCS.md`](CODEMAP_AND_DOCS.md). **프로파일링/트러블슈팅 흐름(환경·로그·역할):** [`PROFILING_AND_TROUBLESHOOTING.md`](PROFILING_AND_TROUBLESHOOTING.md) (UI 스터터 재현은 [`UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md)).
- 사람: 리팩터·빌드·인수인계 시 참고.

루트 **`AGENTS.md`**가 이 문서·CODEMAP을 가리킨다.

---

## 방향성 (잊지 말 것)

0. **최종 목표: UI는 Qt만** *(2026-04-23: 레거시 GUI·스텁 제거됨)*  
   메인 패널, 설정, **오버레이**, **드래그 영역 선택**, 트레이는 **`pipela_qt` + `pipela_mod`**. **새 UI·캡처·설정은 Qt에만** 추가한다.

1. **조각 이관 + 조각 삭제**  
   Qt로 옮긴 뒤 남는 데드 경로·문자열은 **같은 청크에서** 정리한다.

2. **`main.py` 슬림화**  
   UI와 **무관한** 상수·순수 함수·Win32 유틸은 **`pipela_core`**로 옮긴다.  
   `main`에는 런타임 전역, 워커/후킹, **`pipela_mod`로 노출하는 얇은 래퍼**가 중심(별도 **표준 GUI 바인딩** 없음).

3. **의존 적은 것부터 코어로**  
   … → **`config_registry_*` + `console_log_constants`**까지 반영(`load`/`save` 본체는 코어 함수 연결).  
   다음은 **스냅샷을 쓰기 소스로 승격**(전역 ↔ dict 단일화), 이어 **템플릿 적용/매칭 루프·워커** 코어화.

4. **Qt와 `pipela_mod`**  
   앱은 **`main`을 `pipela_mod`로 한 번만 로드**하는 패턴을 유지한다. Qt 코드는 `m.some_api`로 main에 붙거나, **`pipela_core`를 직접 import**해 의존을 줄인다.

5. **문서 유지**  
   - **매 작업 종료 시** 이 문서 **맨 위 «실시간 진행판»**을 갱신한다. (최종 작업 요약, 누적 완료 %, 남은 TODO, 남은 %)  
   - 코어에 **새 모듈**을 추가하면 아래 «`pipela_core` 모듈» 표에 한 줄 추가.  
   - **전략 변경**이 있으면 «방향성» 절을 수정.  
   - 본문 «추정 진행도»표는 큰 이정표에서 실시간 판과 맞춰 조정.  
   - **탐색 맵·갱신 루틴** 전체: [`CODEMAP_AND_DOCS.md`](CODEMAP_AND_DOCS.md) — 구조/진입/새 UI 파일이 바뀌면 그 문서 **§5** 도 함께.

6. **축 A·축 B** *(현재: 제품 UI는 Qt·레거시 스텁 제거 완료)*  
   - **축 A** = `pipela_core`·레지 스냅샷·워커 단일 상태, `main` 슬림화(비 UI 이탈).  
   - **축 B** = **UI·import·빌드에서 레거시 GUI 흔적 제거** — 2026-04-23 기준 **핵심 완료**; (선택) `main`→코어 이전.  
   - **병행**해도 된다. 기본 진입은 `main_qt`.

7. **「100%」의 뜻**  
   - **축 A 100%** = **«축 A 완료 기준»** 충족.  
   - **제품·저장소 관점 100%** = **축 A + 축 B(제품 Qt 단일·스텁 없음)**. `main` 줄 수·코어 이전은 **계속 정리 가능(선택)**.

---

## 축 A 완료 기준 *(100% 선언용)*

다음을 **축 A 완료**로 본다 (2026-04-23 기준).

1. **`pipela_core`** 에 본 문서 표의 레지·비전·템플릿·리로드·용병·스냅샷 읽기 등 **비 UI 로직**이 모이고, `load_config` / `save_config` / `schedule_save_config` 경로에서 **`refresh_registry_config_snapshot`** 이 유지된다.  
2. **워커 루프**가 레지에 실리는 값은 **`get_registry_config_snapshot` + `snapshot_*`** 로 읽는 패턴과 맞고, 같은 틱에서 **불필요한 중복 `get`** 은 제거되었다(예: `reload_loop` `snap_once`, `call_merc_loop`, START GAME burst 제외 구간 등).  
3. **Qt 제어창 / 설정 패널** 갱신과 워커·스냅샷이 **같은 틱·단위**로 맞는 정리(역사적: 레거시 제어창에서 시작).  
4. **Win32** 게임/런처 HWND **캐시 갱신**은 `pipela_core.win32_game_windows` 의 순수 헬퍼로 모였다.  
5. **`main.py` 대형 덩어리**는 **워커·비전·입력 훅·`pipela_mod`**가 중심; UI는 `pipela_qt` — 추가 슬림화는 (선택) **코어 이전**.

`registry_snapshot_read.coalesce_registry_snapshot` 으로 패널·틱에 **선택 `snap` 인자**를 붙일 때 한 줄로 합류시킬 수 있다.

---

## 앱 진입점 (현재 구현)

| 경로 | 동작 |
|------|------|
| `python main.py` *(인자 없음)* / PyInstaller 기본 | **`main_qt()`** → `pipela_qt.shell.run_qt_application` — 제어창·트레이·`QtGameOverlay` 등 **Qt만**. |
| *(삭제됨)* `--tk` | 옛 **별도 UI 프로세스** 경로 — **제거**됨. |

**`main` 모듈:** **표준 GUI 바인딩·스텁 패키지 없음** (2026-04-23). 영역 선택·템플릿 캡처·오버레이는 **Qt** (`pipela_qt.*_drag_overlay`, `pipela_mod` API).

---

## 축 B 로드맵 *(레거시 UI 제거 — 진행용)*

**진행 상황 (2026-04-23):** **옛 `--tk` / 스텁 패키지 / 중복 UI** 정리 · `main` **주석·문서** 갱신 · **`roadmap` P01–P15** · **PyInstaller `Pipela.spec`** 로 빌드 검증.

**남은 것 (선택, 비 UI):** `main` 의 **워커·비전** 대형 덩어리 **`pipela_core` 이전** — **제품 «레거시 UI 없음»**과는 별도의 **아키텍처 슬림화**다.

코드 체크리스트: **`pipela_qt/roadmap.py`** — `roadmap.summary()` (**P01–P15 완료**).

---

## Qt UI 단계 로드맵 (코드)

기능 단위 Qt 이전 **체크리스트**는 코드에 있다:

- `pipela_qt/roadmap.py` — `QT_MIGRATION_PHASES`, `roadmap.summary()`

이것은 «어떤 설정 패널을 Qt로 만들었는지»에 가깝고, **`main.py` 줄 수 감소·`pipela_core` 분리**와는 별 축이다. 둘 다 문서/로드맵을 함께 본다.

---

## `pipela_core` 모듈 (역할 요약)

| 모듈 | 내용 |
|------|------|
| `paths.py` | `SCRIPT_DIR`, 템플릿/아이콘 경로, `migrate_legacy_bundle_template_path`, `pipela_user_data_dir`, `template_capture_user_storage_dir`, PyInstaller/소스 루트 |
| `version_info.py` | `PIPELA_APP_VERSION`, 업데이트 manifest URL, 재설치 EXE URL |
| `display_timing.py` | 주사율, `display_tick_ms`, `display_aligned_wall_ms` |
| `win32_game_windows.py` | 이터널시티/스마트업데이터 HWND 탐색, **캐시 갱신**(`refresh_eternalcity_hwnd_cached`, `refresh_smart_updater_hwnd_cached`), `get_window_rect`, `get_window_size` |
| `win32_window_ops.py` | TOPMOST, `SetWindowPos`, DPI, `clamp_rect_to_monitor_work_area`, `center_outer_window_on_monitor_work_area` 등 |
| `scale_geometry.py` | `BASE_HEIGHT`, `get_scale_ratio`, `get_region_pixels` |
| `primary_monitor.py` | mss 주 모니터 dict, 정규화 ROI → 픽셀, 높이 스케일 비율 |
| `registry_constants.py` | `REGISTRY_PATH` |
| `win32_input_constants.py` | 마우스/키 상수, `vk_to_display_name` |
| `ui_fonts.py` | `FONT_UI_KO`, `FONT_UI_MONO`, `FONT_UI` |
| `vision_lazy.py` | `ensure_cv2_numpy_mss()` — cv2/numpy/mss 지연 로드 |
| `vision_capture.py` | `capture_window`, `capture_region`, `get_region_pixels_primary_monitor`, `capture_region_primary_monitor` |
| `config_parse.py` | `reg_parse_bool`, `clamp_match_threshold_01` |
| `config_registry_tables.py` | `CONFIG_LOAD_JSON_REGIONS`, 저장 필드 튜플 등 load/save 매핑, `REGISTRY_CONFIG_SNAPSHOT_KEYS` |
| `config_registry_query.py` | `try_query_float`, `try_query_int` (열린 레지 키) |
| `config_registry_load.py` | JSON ROI·템플릿 경로·이미지 데이터 플래그 로드, vault 레거시 마이그레이션 |
| `config_registry_save.py` | 동일 키/ (레지, 전역) 쌍 REG_SZ 저장, `save_json_region_optional`, 레거시 키 삭제 |
| `config_registry_extended.py` | bool·optional float/int, reload 묶음, 좌클릭 타이밍, 탄약/용병 임계값, 콘솔·영역 미리보기 레지 입출력 |
| `config_registry_kill_counter.py` | 킬카운터 그래프·행·랩 레지 로드/저장(행·일시정지 정규화는 호출부 콜백) |
| `console_log_constants.py` | `CONSOLE_LOG_RETENTION_*`, `CONSOLE_LOG_TIME_MODE_*` |
| `ai_debug_session_log.py` | **지원/AI** 세션 파일(`%LOCALAPPDATA%\\Pipela\\ai_debug\\`), stdout/stderr 미러·예외·45s JSON 하트비트, `PIPELA_AI_DEBUG=0` 끔 |
| `kill_counter_layout.py` | 킬 통계 행 기본 키·레거시 맵·`kill_counter_stat_row_order_normalize`, 랩 일시정지 구간 정규화 |
| `region_dispatch.py` | `REGION_TYPE_TO_GLOBAL_NAME`, `CAPTURE_KIND_TO_REGION_TYPE`, `REGION_PREVIEW_PERSIST_VALID`, UI 라벨 쌍 |
| `registry_config_snapshot.py` | `get_registry_config_snapshot`, `refresh_registry_config_snapshot`, `sync_registry_snapshot_from_module`, `REGISTRY_CONFIG_SNAPSHOT_KEYS`(테이블에서 조합) |
| `registry_snapshot_read.py` | `snapshot_float` / `snapshot_int` / `snapshot_bool`; **`coalesce_registry_snapshot`** (이미 들고 있는 dict 또는 최신 스냅샷) |
| `template_capture_catalog.py` | `get_template_capture_kind_meta`, `TEMPLATE_CAPTURE_KIND_PATH_BINDING`, `AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND` |
| `ammo_restock_catalog.py` | Ammo Restock 종류·경로/임계/점수/ROI/레지 키·로그 태그 등 |
| `ammo_restock_templates.py` | `ammo_restock_sync_templates`, `ammo_restock_load_templates_from_globals` (`path_snap` 선택) |
| `call_merc_catalog.py` | Call Merc 4단계 경로·임계·점수·ROI·파일 대화상자·미리보기 속성명 |
| `image_registry.py` | PNG ↔ 레지 base64 `save_image_to_registry`, `load_image_from_registry`, `load_image_data`, `load_image_data_if_path_changed` |
| `template_matching.py` | `scale_template`, `match_template_ccoeff_normed_max`, `find_image`, `find_image_location`, `match_template_max_score`, `extract_match_patch`, `match_patch_if_ok`, `rescale_if_ratio_changed`, `refresh_scaled_map_if_ratio_changed`, `match_tl_to_center_xy` |
| `template_match_config.py` | `TEMPLATE_MATCH_THRESHOLD_GLOBAL_BY_KIND`, `template_match_threshold_for_globals` |
| `template_apply.py` | `apply_template_capture_png`, `template_capture_load_existing_pil`, `template_capture_output_path_for_kind`, `write_pil_rgb_to_png_cv2` |
| `template_roi.py` | `region_roi_from_globals`, `region_roi_set_in_globals`, `template_roi_for_kind`, `match_center_in_client`, `match_center_to_screen_xy` |
| `template_debug_match.py` | `debug_sample_template_match`, `START_GAME_LAUNCHER_TEMPLATE_SCALE_RATIO` |
| `template_capture_region.py` | `normalized_roi_xywh_from_drag_rect`, `drag_rect_exceeds_min_size`, `capture_drag_rect_to_pil_rgb`, `capture_normalized_roi_to_pil_rgb` |
| `reload_nobullet_bullet.py` | `reload_try_reload_nobullet_bullet_templates`, `reload_rescale_nobullet_bullet_if_needed` |
| `reload_idle_secondary.py` | `reload_idle_update_bullet_vault_scores` |
| `reload_sequence.py` | `reload_clamp_ammo_count`, `reload_move_sleep_double_click`, `reload_send_digit_keys_and_return`, `reload_match_bullet_on_screen`, `reload_match_vault_on_screen` |
| `flame_trigger_automation.py` | `automation_disable_flame_trigger_if_active`, `automation_reenable_flame_trigger_after_success` (Reload·Call Merc FT) |
| `call_merc_match.py` | `call_merc_match_one_kind` (선택 `match_threshold`, `roi_override`) |
| `call_merc_templates.py` | `call_merc_try_reload_templates` (`path_snap` 선택), `CallMercTemplateLoadResult` |

---

## 추정 진행도 (전체 이관·슬림화)

의미: «`main`을 부트스트랩+레거시 최소로 만들고, 로직은 코어/Qt에 두는 작업» 기준 **대략치**.  
**축 A**(코어·스냅샷·워커)는 진행판 기준 **100%**; 아래 «남은 비중」은 **축 B·통합 슬림화**까지 넣은 **전체 저장소** 관점이다.

| 구간 | 누적 완료(참고) | 남은 덩어리(전체 관점 대략 비중) |
|------|-----------------|-------------------------------------|
| **축 A** 코어·스냅샷·워커(위 완료 기준) | **100%** | — |
| Win32·제어창·레이아웃(유지보수) | | 소량 |
| 설정·레지스트리·스냅샷 엣지 | | 소량 |
| 캡처·템플릿·워커 루프(`main`·코어) | | (선택) **추가 코어 이전** |
| 입력·후킹·상태 | | `main` 중심 |
| **UI 단일·레거시 제거(축 B)** | **완료** (2026-04) | — |

---

## 다음 작업 후보 (우선순위)

1. (선택) **`main` 대형 로직 `pipela_core` 이전** — 워커·비전·순수 유틸, `pipela_mod` 래퍼만 유지.  
2. (선택) **레지/스냅샷** 단일 소스·중복 get 추가 정리.  
3. **회귀 방지**: `py_compile` / `import main` / 필요 시 `Pipela.spec` PyInstaller.

---

## 빠른 명령

```bash
python -c "from pipela_qt import roadmap; print(roadmap.summary())"
python -m py_compile main.py
```

---

## 변경 이력 (요약)

| 날짜 | 내용 |
|------|------|
| 2026-04-26 | **UI perf:** `ui_perf_bootstrap` frozen 시 LocalAppData 로그·기동 한 줄·`spike_log_file`·스트립 HUD·`PROFILING`/`UI_STUTTER`/`CODEMAP`. |
| 2026-04-26 | **프로파일링:** `requirements-dev.txt`(py-spy)·`tools/profile_pipela.ps1`·`PROFILING_AND_TROUBLESHOOTING` §2.5·`CODEMAP` 표 행. 진행판. |
| 2026-04-23 | **문서 `docs/CODEMAP_AND_DOCS.md`** (코드맵 + 갱신 규칙), `AGENTS`·MIGRATION 연동. |
| 2026-04-23 | **Tk 흔적 정리**: `pipela_qt`·`pipela_core` **docstring/주석/사용자 문구**·`roadmap` P10–P15·`MIGRATION_HANDOFF` 방향/추정표/다음 작업. |
| 2026-04-23 | **축 B 마무리**: `main` **Tk/레거시 주석** 정리 · **`pipela_legacy_tk/` 삭제** · `AGENTS`·`roadmap` P13·`Pipela.spec` · **`py_compile` / `import` / PyInstaller** 검증. 진행판·«앱 진입점»·«축 B». |
| 2026-04-23 | **`main`**: `qt_stub_tk` import 제거·데드 Tk/Win32 헬퍼(`place_toplevel…`, `tk_native_root_hwnd` 등) 삭제; **`Pipela.spec`** 주석·`hiddenimports` 정리; `AGENTS`·진행판·«앱 진입점»·«축 B». |
| 2026-04-23 | **`main`**: 데드 Tk 커서/영역 Canvas 드로잉·`tkfont` 제거; Flame 상수 슬림화. |
| 2026-04-23 | **`main`**: Tk 설정 허브 덩어리·임베드 스크롤·테마/Toplevel·저장 디바운스 Tk 분기 제거(수백 줄). |
| 2026-04-23 | **`main`**: `PIL.ImageTk`·데드 템플릿 Tk 패널 조각·`_region_preview_draw_*` 제거; 진행판·`roadmap` P13 문구 갱신. |
| 2026-04-23 | **축 B**: Qt 경로 tkinter 미로드(`qt_stub_tk`), `roadmap` P13 완료·P14–P15. |
| 2026-04-23 | **축 B**: `pipela_legacy_tk` 골격, «축 B 로드맵» 절·진행판. |
| 2026-04-23 | **축 A 100%** 선언: 완료 기준 §·방향성 **7**·`coalesce_registry_snapshot`·진행판/추정 표 정리. |
| 2026-04-23 | Tk `update_gui`: `_update_gui_layout_tick`/`_widgets_tick`에 동일 스냅샷 전달. |
| 2026-04-23 | Tk 제어창: Reload/Merc/Ride·HP 버튼 갱신에 스냅샷 인자 전달(중복 get 제거). |
| 2026-04-23 | `reload_loop`: `snap_once`·`load_templates(path_snap)`로 틱당 스냅샷 공유. |
| 2026-04-23 | `call_merc_loop`: 스냅샷 단일화·`call_merc_active`를 `snapshot_bool`로 판별. |
| 2026-04-23 | `win32_game_windows`: HWND 캐시 갱신 헬퍼; `main` `refresh_*_hwnd_if_needed` 슬림. |
| 2026-04-23 | 방향성 **6**: 축 A 우선·축 B 후속(병행 가능) 작업 순서 명시. |
| 2026-04-23 | `region_preview_sync_persist_from_live`: live 없으면 저장값 유지; Qt `aboutToQuit` 선동기화. |
| 2026-04-23 | Qt `shell`: 저장 영역 미리보기 `region_preview_try_restore_saved` 지연 복원(Tk 오버레이와 동일 타이밍). |
| 2026-04-23 | `qt_capture` 템플릿 툴바 「해제」(매칭 영역)·`on_applied` 연동. |
| 2026-04-23 | `debug_pulse_overlay`·Qt 패널 「감지」버튼(템플릿·킬카운터 디버그 큐). |
| 2026-04-23 | `shell`에서 `tk_aux` 제거·`schedule_save_config` Qt 디바운스/스레드 마샬. |
| 2026-04-23 | `region_drag_overlay`·`start_region_select` Qt 분기·`qt_capture`에서 `ensure_tk_aux` 제거(영역 선택만). |
| 2026-04-23 | 앱 진입점 절(`main_qt` 기본·`--tk` 레거시·`tk_aux` 잔존). `main`/`AGENTS` 주석. |
| 2026-04-23 | 진행판 **축 A / 축 B** 이중 %: 코어·스냅샷 vs **제품(Tk 0)**. 후자는 재추정 범위 명시. |
| 2026-04-23 | **전략**: 최종 **Tk 없음·UI 전부 Qt**(오버레이·캡처 포함), Tk 흔적 제거 목표. 방향성·진행판·AGENTS 반영. |
| 2026-04-23 | START GAME 런처 burst 루프 스냅샷 `active` 검사. 진행판·표 갱신. |
| 2026-04-23 | Reload/Call Merc Tk 버튼 표시 스냅샷(`reload_ammo_count`, `call_merc_active`). 진행판·표 갱신. |
| 2026-04-23 | 제어창 위젯 틱·`update_buttons`·Ride/HP·Reload FT 재활성 스냅샷. 진행판·표 갱신. |
| 2026-04-23 | Ammo Restock `ammo_restock_sync_templates`·루프 스냅샷 경로. 진행판·표 갱신. |
| 2026-04-23 | Call Merc `path_snap`; START GAME 루프 템플릿 캐시. 진행판·표 갱신. |
| 2026-04-23 | `ride_loop`/`hp_refill_loop` 스냅샷 경로·`load_image_data_if_path_changed`. 진행판·표 갱신. |
| 2026-04-23 | `reload_loop` 템플릿 경로 스냅샷; `_update_gui_layout_tick` 게임창 중앙 옵션 스냅샷. 진행판·표 갱신. |
| 2026-04-23 | `kill_counter_loop` 스냅샷(활성·ROI). 진행판·표 갱신. |
| 2026-04-23 | LeftClick/RightHold/Flame Trigger 워커 루프 스냅샷 읽기. 진행판·표 갱신. |
| 2026-04-23 | Ride/HP/Ammo/Call Merc 루프 + `call_merc_match` 오버라이드. 진행판·표 갱신. |
| 2026-04-23 | `schedule_save_config` 선행 스냅샷 갱신; `reload_loop` 스냅샷 읽기. 진행판·표 갱신. |
| 2026-04-23 | Qt Kill Counter 패널 스냅샷 연동(3차). 진행판·표 갱신. |
| 2026-04-23 | Qt Ammo·Call Merc·START GAME·LeftClick·Flame·Console 스냅샷 연동(2차). 진행판·표 갱신. |
| 2026-04-23 | `sync_registry_snapshot_from_module`; Qt Reload/Ride/HP 패널 스냅샷 읽기·커밋 시 동기화. 진행판·표 갱신. |
| 2026-04-23 | `template_capture_region` 드래그→PIL·최소 크기 공통화; `start_region_select`/`start_template_image_capture` 슬림. 진행판·표 갱신. |
| 2026-04-23 | `flame_trigger_automation`; Reload/`call_merc_loop` FT 해제·복귀 코어화, spec·진행판·표 갱신. |
| 2026-04-22 | `reload_move_sleep_double_click`, `registry_snapshot_read`; spec·진행판·표 갱신. |
| 2026-04-22 | `ammo_restock_catalog`, `call_merc_catalog`, `image_registry`; Qt 탄약/용병 패널 코어 맵; spec·진행판 갱신. |
| 2026-04-22 | `template_capture_catalog`, Qt 탄약 패널 `AMMO_UI_KIND_*` 코어 import, spec·진행판 갱신. |
| 2026-04-22 | `REGISTRY_CONFIG_SNAPSHOT_KEYS`, `registry_config_snapshot`, load/save `finally` 갱신. 진행판·spec 갱신. |
| 2026-04-22 | `kill_counter_layout`, `region_dispatch`, Qt `CAPTURE_KIND` 직접 import, `config_registry_kill_counter` 기본 정규화. 진행판·spec 갱신. |
| 2026-04-22 | `config_registry_extended`, `config_registry_kill_counter`, `console_log_constants`, `save_json_region_optional`; 레지 `_config_*` 제거. 진행판·표·spec 갱신. |
| 2026-04-22 | `config_registry_load`/`config_registry_save`, `paths.migrate_legacy_bundle_template_path`, `load_config`/`save_config` 슬림. 진행판·표 갱신. |
| 2026-04-22 | `config_registry_tables`/`config_registry_query`, spec 보강, 진행판·표 갱신. |
| 2026-04-22 | `vision_lazy`/`vision_capture`/`config_parse`, `Pipela.spec` hiddenimports. 진행판·표 갱신. |
| 2026-04-22 | 맨 위 «실시간 진행판» 추가. 매 작업 후 갱신 규칙 명시. |
| 2026-04-22 | 문서 신설. `pipela_core` 표·방향성·진행도·다음 작업 정리. |
