# AGENTS.md — Pipela

코드 에이전트·IDE 보조 AI는 **`main.py`**, **`pipela_qt/`**, **`pipela_core/`** 를 수정하기 전에 아래를 읽는다.

## 필수

- **[`docs/MIGRATION_HANDOFF.md`](docs/MIGRATION_HANDOFF.md)** — **UI는 Qt만·레거시 GUI 제거**, `pipela_core` 목록, 진행도, 다음 작업, **실시간 진행판** 갱신 규칙.
- **[`docs/DOCK_UI_PHASE_HANDOFF.md`](docs/DOCK_UI_PHASE_HANDOFF.md)** — **도킹 UI 페이즈**(`client`/`launcher`/`standby`), 상단 스트립·Intro Skip(템플릿①) 런처 정책, **런처에서 제어·킬만 숨김**·복원 (`dock_chrome_restore`) — 2026-04 인수인계.
- **[`docs/CODEMAP_AND_DOCS.md`](docs/CODEMAP_AND_DOCS.md)** — **코드 위치(탐색 맵)**·`pipela_mod`/Qt/코어 **어디를 볼지**·문서 **갱신 규칙**(구조 변경 시 이 파일도 함께).
- **[`docs/PROFILING_AND_TROUBLESHOOTING.md`](docs/PROFILING_AND_TROUBLESHOOTING.md)** — **cProfile**, **AI·지원 세션 로그**, **트러블슈팅** 시 어떤 환경·로그를 쓰는지 (`PIPELA_AI_DEBUG`, [`UI_STUTTER_REPRO_SCENARIOS.md`](docs/UI_STUTTER_REPRO_SCENARIOS.md) 와의 역할 분담).
- Qt UI 단계 체크리스트: **`pipela_qt/roadmap.py`** (`roadmap.summary()`).

## 작업 시

- **진입은 Qt만** (`main_qt`). `main` 은 **표준 GUI 바인딩 미사용**; `pipela_legacy_tk` **패키지 없음(2026-04)**.
- **제품 UI는 `pipela_qt` + `pipela_mod`**. 새 UI·오버레이·캡처·설정은 **이 경로에만** 추가; 코드·문서에 **남은 레거시 창/툴킷 이름**은 정리할 것.
- UI와 무관한 로직은 **`pipela_core`**로 옮긴다.
- `main`은 앱 진입점이자 **`pipela_mod`** 단일 인스턴스로 쓰인다. Qt는 `m.xxx` 호환을 깨지 않도록 하거나, 코어를 직접 import한다.
- **문서**  
  - **매 작업(또는 PR) 끝** → `docs/MIGRATION_HANDOFF.md` **맨 위 «실시간 진행판»** (요약, %, TODO, 날짜). `pipela_core` **새 모듈**이면 본문 표 + **[`CODEMAP_AND_DOCS.md`](docs/CODEMAP_AND_DOCS.md) §5.3** 에 따라 탐색 표·날짜.  
  - **구조/진입/새 퍼블릭 `m.xxx` API** 가 바뀌면 `CODEMAP_AND_DOCS.md` (§1–3, §5.3) 를 같이 갱신한다. 상세는 해당 문서 **«갱신 규칙»** 절.

## 상단바(UI 크롬) 표시 버전 — `PIPELA_STRIP_DISPLAY_VERSION`

- **공식 앱 버전** `PIPELA_APP_VERSION`(`pipela_core/version_info.py`)은 **현재 1.0.0 고정** — 배포·manifest·업데이트 비교용. **일상적인 UI/동작 수정만으로는 올리지 않는다.**
- **상단 스트립 등에 보이는 `v…` 숫자**는 같은 파일의 **`PIPELA_STRIP_DISPLAY_VERSION`** 만 올린다 (의미적 **SemVer** `X.Y.Z`). 릴리스 시점에 공식 버전과 맞출지는 별도 결정(지금은 미적용).
- **한 번 올릴 때** 바뀐 **요소 수·영향 범위·비중**을 보고 아래 중 **한 단계만** 올린다. 여러 등급이 겹치면 **가장 큰 쪽 하나만** 적용한다.

| 규모 | 올리는 자리 | 예시 |
|------|-------------|------|
| **소** — patch `Z` | `Z + 1` (Y·X 유지) | 문구·색·폰트 크기·여백·단일 위젯·QSS만, 상수 한두 개 |
| **중** — minor `Y` | `Y + 1`, `Z = 0` | 설정 패널·탭·허브 블록 추가, 도킹/레이아웃 규칙 변경, 폴링·타이밍 정책 조정 |
| **대** — major `X` | `X + 1`, `Y = Z = 0` | 진입점·프로세스 모델·창/오버레이 아키텍처 전면, 핵심 루프·보안 경계 변경 |

- **갱신 빈도 (과도한 patch 방지)**  
  - **같은 PR·같은 논리적 작업 묶음**에서는 strip을 **한 번만** 올린다 (파일 여러 개를 고쳐도 마지막 커밋에서 한 단계).  
  - **이미 올린 버전으로 출고할 작은 후속**(탭 아이콘 1개, 도움말 문구, 여백 몇 px)만 추가된 경우 **숫자를 또 올리지 않아도 된다** — 다음에 **눈에 띄는** UI/도킹 변경이 있을 때 함께 patch/minor로 반영한다.  
  - **연속된 에이전트 세션**에서 소규모만 이어지면, 사용자에게 보이는 변화를 묶어 **patch 한 번**이 적절한지 먼저 판단한다.

- 에이전트는 **사용자에게 보이는** UI·제어창·스트립·도킹·크롬을 바꿨고, 위 **빈도**에 따라 새 숫자가 **정당할 때만** `PIPELA_STRIP_DISPLAY_VERSION`을 갱신한다. 커밋 메시지에 `strip 0.2.1`처럼 적어도 좋다.
- **순수 코어 로직만** 고치고 화면/스트립에 영향이 없으면 strip 버전은 **그대로** 둬도 된다.

## 단일 행 정보 라인 (전역)

- **상태·메트릭·요약 숫자**를 한 줄에 넣는 UI는 **줄바꿈 없이** 유지한다. 가로 폭이 좁아지면 **자간(letter-spacing) 축소 → 필요 시 글자 크기(pt) 축소** 순으로 맞춘다 (제어창 해상도 행: `pipela_qt/control_main.py` 의 `_apply_resolution_label_fit` 참고).
- 새로 비슷한 한 줄 정보를 추가할 때도 동일 원칙을 따른다. `setWordWrap(False)` 와 `white-space:nowrap` 를 기본으로 검토한다.

## Typography (글꼴 방침)

- **라틴/영문(ASCII)**: 항상 **모노스페이스** 계열. Qt·스타일시트는 `FONT_QT_FAMILY_STACK` / `pipela_qt.theme.FONT_CSS_UI` 순서(예: Cascadia Mono → … → Consolas)로 후보를 둔다.
- **한글**: 항상 **맑은 고딕(Malgun Gothic)** 을 우선한다. 시스템에 없으면 스택의 **Gulim** 등으로 폴백한다.
- **단일 출처**: 패밀리 이름·순서는 **`pipela_core/ui_fonts.py`** (`FONT_FAMILY_KO`); Qt 위젯 기본 폰트는 **`pipela_qt/qt_fonts.app_default_qfont`**, 앱 전역은 **`pipela_qt/main_window.configure_app`**. 새 UI는 하드코딩 대신 이 경로를 쓴다.
