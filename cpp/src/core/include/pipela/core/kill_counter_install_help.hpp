#pragma once

#include <string_view>

namespace pipela::core {

// AGENT: Keep in sync with main.py::_kill_counter_install_help_text().
inline constexpr std::string_view killCounterInstallHelpText() {
    return
        "# Kill Counter — 감지 영역 화면 변화 시에만 숫자 OCR (Tesseract eng)\n"
        "# 감지 영역: `현재킬/목표` 형태 OCR (예: 3/10) — 카운트는 앞 숫자(현재 킬)만 사용\n"
        "# OCR 영역: 설정에서 선택 영역 지정 필수(미지정 시 OCR 안 함)\n"
        "\n"
        "# PATH에 tesseract 없으면 환경변수로 직접 지정 가능:\n"
        "# TESSERACT_CMD=C:\\\\Program Files\\\\Tesseract-OCR\\\\tesseract.exe\n"
        "\n"
        "# pytesseract + Windows Tesseract (eng.traineddata)\n"
        "pip install pytesseract\n"
        "https://github.com/UB-Mannheim/tesseract/wiki\n";
}

}  // namespace pipela::core
