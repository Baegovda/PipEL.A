<p align="center">
  <img src="assets/vaultboy.png" alt="Pipela" width="96" />
</p>

<h1 align="center">Pipela</h1>

<p align="center">
  <strong>폐허 거리용 게임 도킹형 자동화·킬 카운터</strong><br/>
  Windows · Qt6 C++ · 게임 창 옆 제어 패널 · 템플릿 비전 · 커서 HUD
</p>

<p align="center">
  <a href="https://github.com/Baegovda/PipEL.A/releases/latest">
    <img src="https://img.shields.io/github/v/release/Baegovda/PipEL.A?label=release&style=flat-square" alt="Latest release" />
  </a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
</p>

<p align="center">
  <a href="#-다운로드">다운로드</a> ·
  <a href="#-주요-기능">기능</a> ·
  <a href="#-빠른-시작">빠른 시작</a> ·
  <a href="#-개발">개발</a>
</p>

---

## ✨ 한 줄 요약

**Pipela**는 사냥터 창 옆에 도킹되는 제어 패널로, 리로드·탄약·라이드·용병·플레임 등 반복 동작을 템플릿 매칭으로 돕고, OCR **킬 카운터**로 사냥 통계를 추적합니다.

---

## 🎯 주요 기능

| 영역 | 내용 |
|------|------|
| **도킹 UI** | 게임/런처 옆 제어창·킬 패널·상단 스트립 |
| **자동화** | Left Click, Right Hold, Flame, Reload, Ammo, Ride, HP, Call Merc, Start Game |
| **킬 카운터** | OCR, 등급·일일 캘린더·차트 |
| **비전** | ROI 템플릿 캡처·매칭 |
| **커서 HUD** | DirectComposition 네이티브 오버레이 |

---

## 📥 다운로드

1. [**Releases**](https://github.com/Baegovda/PipEL.A/releases/latest) 에서 최신 **`Pipela-cpp-<버전>-win64.zip`**
2. 압축 해제 후 **`Pipela.exe`** 실행
3. 앱 **설정 → 업데이트**에서도 새 버전 확인 가능

**선택:** 킬 카운터 OCR용 [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 설치.

---

## 🚀 빠른 시작

1. 이터널시티(또는 런처) 실행
2. Pipela 실행 → 제어창이 게임 옆에 도킹되는지 확인
3. 필요한 기능 ON → 설정에서 템플릿·ROI 캡처

| 키 | 동작 |
|----|------|
| **F5** / **F6** | Reload / Ammo Restock 토글 (앱 내 설정) |
| **F8** | 종료 |
| **트레이** | 백그라운드·종료 |

---

## 🛠 개발

**Windows 10/11** · **Cursor / VS Code** 권장.

```powershell
git clone https://github.com/Baegovda/PipEL.A.git
cd PipEL.A
```

| 동작 | 방법 |
|------|------|
| **빌드** | **Ctrl+Shift+B** 또는 `빌드.bat` |
| **실행** | **F5** → 증분 빌드 후 `Pipela.exe` (디버거 없음) |
| **복구** | `scripts\recover-ide-build.ps1` → Reload Window |

에이전트·릴리스·아키텍처: **[`AGENTS.md`](AGENTS.md)** (개발자용 단일 문서).

```
cpp/src/app/     Qt6 UI
cpp/src/core/    워커·비전·레지스트리
scripts/         build-release.ps1 (증분 빌드)
```

> `main.py` / `pipela_qt/` 는 마이그레이션 잔여(Phase 6 삭제 예정). 일상 개발은 **C++ exe**만 사용.

---

## 📋 변경 이력

[`UpdateLog/update_log.md`](UpdateLog/update_log.md)

---

## ⚠️ 면책

게임 이용약관·운영정책 준수는 **사용자 책임**입니다. Pipela는 제3자와 무관한 개인 편의 도구입니다.

---

<p align="center"><sub>폐허 사냥꾼을 위해 · Pipela</sub></p>
