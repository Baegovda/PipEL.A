# 프로파일링·트러블슈팅 — 에이전트 인수인계

**대상:** 다음 세션의 코드 에이전트·지원/디버그 담당.  
**역할:** *무엇을 켜서 어디를 보며*, *어떤 문제에 어떤 경로를 쓰는지* 를 한 번에 잡는다. 구현 세부·재현 절차는 링크된 문서·모듈이 진실(ground truth)이다.

**마지막 갱신:** 2026-04-26

---

## 1. 두 축으로 나누기 (정책)

| 축 | 목적 | 켜는 조건(대략) | 산출물 위치 |
|----|------|----------------|-------------|
| **A. AI/지원 세션 로그** | **콘솔 복제**·JSON 이벤트·예외·**하트비트**(HWND·창 크기 등) | 크래시·이상 동작·**원격 지원 시** 재현 맥락을 파일로 남길 때 | `%LOCALAPPDATA%\Pipela\ai_debug\` (`session_*.log`, `latest.log`) |
| **B. 재현 시나리오(사람/에이전트 공통)** | *언제* 끊기는지 S0~S5로 **좁힌 뒤** 로그·프로파일과 함께 읽기 | UI 끊김을 **이슈로 올릴 때** | [`UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md) |

**CPU·Python 호출 경로**를 보고 싶을 때는 아래 **§2 cProfile** (`python -m cProfile` 또는 `tools/profile_pipela.ps1`)을 쓴다. 저장소에 내장된 `PIPELA_UI_PERF` / `ui_perf_probe` 계측은 **제거됨**(2026-04).

---

## 2. cProfile (Python 호출 누적)

**언제:** 순수 Python에서 시간이 많이 드는 경로(메인 루프·Qt 슬롯·I/O)를 **호출 통계**로 넓게 볼 때.

**한 번에 켜기 (PowerShell, 저장소 루트)**

```powershell
.\tools\profile_pipela.ps1
```

`profile_pipela.ps1` 은 실행 시 기존 `profiling/pipela_cprofile_*.stats` 를 **먼저 지우고** 새 타임스탬프 파일 하나만 쓴다. 앱을 정상 종료하면 기록이 마무리된다. (`python -m cProfile -o ...` 를 직접 치면 이 정리는 적용되지 않는다.)

**직접 실행**

```text
python -m cProfile -o profiling\run.stats main.py
```

**결과 보기**

```text
python -m pstats profiling\pipela_cprofile_HHMMSS-YYYYMMDD.stats
```

프롬프트에서 `sort cumulative` 후 `stats 40` 등.

---

## 3. AI/지원 세션 로그(축 A) — 환경·내용

**구현:** `pipela_core/ai_debug_session_log.py` · Qt 셸에서 `pipela_mod.AI_DEBUG_LOG_PATH` 설정 · `install_stdio_tee` 등. 하트비트·shutdown JSON은 `shell.py`·관련 루프와 연동.

| 변수 | 의미 |
|------|------|
| `PIPELA_AI_DEBUG=1` (기본) | 세션 로그 **켬**. |
| `PIPELA_AI_DEBUG=0` (또는 false/no/off) | **끔** — 콘솔 미러·JSON·하트비트 파일 기록 **중단** 의도. |

**포함될 수 있는 것(개요):** `stdout`/`stderr` 미러, 처리되지 않은 예외·스레드 훅, `###AI JSON`…`###END` 블록, **주기 하트비트**(게임 HWND, 플래그, 창 크기 등). 자세한 목록은 디렉터리의 `README_AI_DEBUG.txt` 생성문구·모듈 docstring.

**에이전트 운용 정책**

- 재현/지원이 끝나고 로그에 **비밀·경로**가 문제되면 사용자에게 `PIPELA_AI_DEBUG=0` 권고.  
- **코어 동작을 바꾸지 않는** 트러블슈팅 루트는 `ai_debug` 경로·이벤트 **형식**을 맞출 것 — 파서·`grep "###AI JSON"`에 의존하는 흐름이 있음.

---

## 4. 문서·코드 링크(탐색)

| 항목 | 위치 |
|------|------|
| UI 끊김 **재현 S0~S5** | [`docs/UI_STUTTER_REPRO_SCENARIOS.md`](UI_STUTTER_REPRO_SCENARIOS.md) |
| 이행·진행도(매 작업 갱신) | [`docs/MIGRATION_HANDOFF.md`](MIGRATION_HANDOFF.md) |
| 파일 위치·`shell` 연쇄 | [`docs/CODEMAP_AND_DOCS.md`](CODEMAP_AND_DOCS.md) §1~3 |
| 에이전트 필독 | 루트 [`AGENTS.md`](../AGENTS.md) |

`pipela_core` 모듈 표에 `ai_debug_session_log.py`가 있으면 본 정책의 **AI 세션 로그**와 같이 읽는다.

---

## 5. “다음에 어떤 로그를 먼저 보나” (빠른 결정)

1. **한 번도 안 켰고** “왜 죽었는지 / 콘솔에 뭐가 나왔는지” → **AI 세션 로그** + 재현 절차.  
2. **UI가 버벅**이거나 CPU가 높음 → [UI_STUTTER](UI_STUTTER_REPRO_SCENARIOS.md)로 상황을 좁힌 뒤 **§2 cProfile**로 Python 쪽 병목을 본다.  
3. **둘 다** 병행해도 된다 — 로그는 동작 맥락, cProfile은 **어떤 함수가 비싼지**에 유리하다.

이 문서를 고쳤으면 `CODEMAP_AND_DOCS.md` 맨 위 날짜·필요 시 `MIGRATION_HANDOFF` 실시간 진행판을 규칙대로 갱신한다.
