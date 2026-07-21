#include "pipela/core/win32/game_windows.hpp"

#include "pipela/core/vision/roi.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <algorithm>
#include <chrono>
#include <cwctype>
#include <functional>
#include <string>
#include <vector>

namespace pipela::core::win32 {

namespace {

#ifdef _WIN32
std::wstring windowText(HWND hwnd) {
    const int len = GetWindowTextLengthW(hwnd);
    if (len <= 0) {
        return {};
    }
    std::wstring out(static_cast<size_t>(len) + 1u, L'\0');
    const int got = GetWindowTextW(hwnd, out.data(), len + 1);
    if (got <= 0) {
        return {};
    }
    out.resize(static_cast<size_t>(got));
    return out;
}

std::wstring toLower(std::wstring s) {
    std::transform(s.begin(), s.end(), s.begin(), [](wchar_t c) { return static_cast<wchar_t>(std::towlower(c)); });
    return s;
}

bool containsInsensitive(const std::wstring& hay, const std::wstring& needle) {
    if (needle.empty()) {
        return false;
    }
    const auto h = toLower(hay);
    const auto n = toLower(needle);
    return h.find(n) != std::wstring::npos;
}

struct EnumCtx {
    std::vector<HWND> visible;
    std::vector<HWND> any;
    std::function<bool(const std::wstring&)> title_ok;
};

BOOL CALLBACK enumWindowsProc(HWND hwnd, LPARAM lparam) {
    auto* ctx = reinterpret_cast<EnumCtx*>(lparam);
    const std::wstring title = windowText(hwnd);
    if (!ctx->title_ok(title)) {
        return TRUE;
    }
    ctx->any.push_back(hwnd);
    if (IsWindowVisible(hwnd)) {
        ctx->visible.push_back(hwnd);
    }
    return TRUE;
}

std::intptr_t findWindowByTitle(const std::function<bool(const std::wstring&)>& title_ok) {
    EnumCtx ctx{};
    ctx.title_ok = title_ok;
    EnumWindows(enumWindowsProc, reinterpret_cast<LPARAM>(&ctx));
    if (!ctx.visible.empty()) {
        return reinterpret_cast<std::intptr_t>(ctx.visible.front());
    }
    if (!ctx.any.empty()) {
        return reinterpret_cast<std::intptr_t>(ctx.any.front());
    }
    return 0;
}

double nowMono() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

constexpr double kEtGwtRevalidateMin = 0.55;
constexpr double kSuGwtRevalidateMin = 1.35;
constexpr double kEtEnumMinInterval = 0.72;
constexpr double kSuEnumMinInterval = 0.72;

double g_last_et_gwt_mono = 0.0;
std::intptr_t g_last_et_gwt_hwnd = 0;
double g_last_et_enum_mono = 0.0;
double g_last_su_gwt_mono = 0.0;
std::intptr_t g_last_su_gwt_hwnd = 0;
double g_last_su_enum_mono = 0.0;
#endif

}  // namespace

bool isWindow(std::intptr_t hwnd) {
#ifdef _WIN32
    return hwnd != 0 && IsWindow(reinterpret_cast<HWND>(hwnd)) != FALSE;
#else
    (void)hwnd;
    return false;
#endif
}

bool isWindowMinimized(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return true;
    }
    return IsIconic(reinterpret_cast<HWND>(hwnd)) != FALSE;
#else
    (void)hwnd;
    return true;
#endif
}

bool isForegroundWindow(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return false;
    }
    return GetForegroundWindow() == reinterpret_cast<HWND>(hwnd);
#else
    (void)hwnd;
    return false;
#endif
}

std::optional<std::pair<int, int>> getScreenCursorPos() {
#ifdef _WIN32
    POINT pt{};
    if (!GetCursorPos(&pt)) {
        return std::nullopt;
    }
    return std::pair<int, int>{pt.x, pt.y};
#else
    return std::nullopt;
#endif
}

bool isMouseInClientWindow(std::intptr_t hwnd) {
    if (!isForegroundWindow(hwnd)) {
        return false;
    }
    const auto rect = getClientRectScreen(hwnd);
    const int left = std::get<0>(rect);
    const int top = std::get<1>(rect);
    const int right = std::get<2>(rect);
    const int bottom = std::get<3>(rect);
    if (right <= left || bottom <= top) {
        return false;
    }
    const auto pos = getScreenCursorPos();
    if (!pos) {
        return false;
    }
    return pos->first >= left && pos->first <= right && pos->second >= top && pos->second <= bottom;
}

std::tuple<int, int, int, int> getClientRectScreen(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return {0, 0, 0, 0};
    }
    RECT cr{};
    if (!GetClientRect(reinterpret_cast<HWND>(hwnd), &cr)) {
        return {0, 0, 0, 0};
    }
    POINT tl{cr.left, cr.top};
    POINT br{cr.right, cr.bottom};
    ClientToScreen(reinterpret_cast<HWND>(hwnd), &tl);
    ClientToScreen(reinterpret_cast<HWND>(hwnd), &br);
    return {tl.x, tl.y, br.x, br.y};
#else
    (void)hwnd;
    return {0, 0, 0, 0};
#endif
}

std::tuple<int, int, int, int> getWindowOuterRectScreen(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return {0, 0, 0, 0};
    }
    RECT wr{};
    if (!GetWindowRect(reinterpret_cast<HWND>(hwnd), &wr)) {
        return {0, 0, 0, 0};
    }
    return {wr.left, wr.top, wr.right, wr.bottom};
#else
    (void)hwnd;
    return {0, 0, 0, 0};
#endif
}

std::vector<unsigned char> captureClientBgr(std::intptr_t hwnd, int* out_w, int* out_h) {
    std::vector<unsigned char> out;
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return out;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    RECT cr{};
    if (!GetClientRect(who, &cr)) {
        return out;
    }
    const int w = cr.right - cr.left;
    const int h = cr.bottom - cr.top;
    if (w < 2 || h < 2) {
        return out;
    }
    HDC hwnd_dc = GetDC(who);
    if (!hwnd_dc) {
        return out;
    }
    HDC mem_dc = CreateCompatibleDC(hwnd_dc);
    HBITMAP bmp = CreateCompatibleBitmap(hwnd_dc, w, h);
    HGDIOBJ old = SelectObject(mem_dc, bmp);
    // AGENT: SRCCOPY only — never CAPTUREBLT (Python vision_lazy MSS patch parity; §14 CURSOR_FLICKER).
    const BOOL ok = BitBlt(mem_dc, 0, 0, w, h, hwnd_dc, 0, 0, SRCCOPY);
    if (!ok) {
        SelectObject(mem_dc, old);
        DeleteObject(bmp);
        DeleteDC(mem_dc);
        ReleaseDC(who, hwnd_dc);
        return out;
    }
    BITMAPINFO bmi{};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = w;
    bmi.bmiHeader.biHeight = -h;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 24;
    bmi.bmiHeader.biCompression = BI_RGB;
    out.resize(static_cast<size_t>(w) * static_cast<size_t>(h) * 3u);
    if (GetDIBits(mem_dc, bmp, 0, static_cast<UINT>(h), out.data(), &bmi, DIB_RGB_COLORS) == 0) {
        out.clear();
    }
    SelectObject(mem_dc, old);
    DeleteObject(bmp);
    DeleteDC(mem_dc);
    ReleaseDC(who, hwnd_dc);
    if (out_w) {
        *out_w = w;
    }
    if (out_h) {
        *out_h = h;
    }
#else
    (void)hwnd;
    (void)out_w;
    (void)out_h;
#endif
    return out;
}

bool eternalcityTitleMatches(const std::wstring& title) {
    if (title.empty()) {
        return false;
    }
    return containsInsensitive(title, L"\uc774\ud130\ub110\uc2dc\ud2f0") ||
           containsInsensitive(title, L"EternalCity");
}

bool smartUpdaterTitleMatches(const std::wstring& title, const std::wstring& korean_substr) {
    if (title.empty()) {
        return false;
    }
    if (!korean_substr.empty() && title.find(korean_substr) != std::wstring::npos) {
        return true;
    }
    const std::wstring t = toLower(title);
    if (t.find(L"smart updater") != std::wstring::npos) {
        return true;
    }
    if (t.find(L"smartupdater") != std::wstring::npos || t.find(L"smartupdate") != std::wstring::npos) {
        return true;
    }
    if (t.find(L"smart") == std::wstring::npos) {
        return false;
    }
    std::wstring compact;
    compact.reserve(t.size());
    for (wchar_t ch : t) {
        if (iswalnum(ch)) {
            compact.push_back(ch);
        }
    }
    return compact.find(L"smartupdater") != std::wstring::npos ||
           compact.find(L"smartupdate") != std::wstring::npos;
}

std::intptr_t findEternalcityWindow() {
#ifdef _WIN32
    return findWindowByTitle([](const std::wstring& t) { return eternalcityTitleMatches(t); });
#else
    return 0;
#endif
}

std::intptr_t findSmartUpdaterWindow(const std::wstring& korean_substr) {
#ifdef _WIN32
    return findWindowByTitle([&korean_substr](const std::wstring& t) {
        return smartUpdaterTitleMatches(t, korean_substr);
    });
#else
    (void)korean_substr;
    return 0;
#endif
}

std::intptr_t refreshEternalcityHwndCached(std::intptr_t prev_hwnd) {
#ifdef _WIN32
    const double now = nowMono();
    if (prev_hwnd && isWindow(prev_hwnd)) {
        if (kEtGwtRevalidateMin > 0.0 && g_last_et_gwt_hwnd == prev_hwnd &&
            (now - g_last_et_gwt_mono) < kEtGwtRevalidateMin) {
            return prev_hwnd;
        }
        const std::wstring title = windowText(reinterpret_cast<HWND>(prev_hwnd));
        g_last_et_gwt_mono = now;
        g_last_et_gwt_hwnd = prev_hwnd;
        if (eternalcityTitleMatches(title)) {
            return prev_hwnd;
        }
    }
    if (!prev_hwnd && (now - g_last_et_enum_mono) < kEtEnumMinInterval) {
        return 0;
    }
    g_last_et_gwt_hwnd = 0;
    g_last_et_gwt_mono = 0.0;
    const std::intptr_t found = findEternalcityWindow();
    g_last_et_enum_mono = nowMono();
    if (found) {
        g_last_et_gwt_hwnd = found;
        g_last_et_gwt_mono = nowMono();
    }
    return found;
#else
    (void)prev_hwnd;
    return 0;
#endif
}

std::intptr_t refreshSmartUpdaterHwndCached(std::intptr_t prev_hwnd, const std::wstring& korean_substr) {
#ifdef _WIN32
    const double now = nowMono();
    if (prev_hwnd && isWindow(prev_hwnd)) {
        if (kSuGwtRevalidateMin > 0.0 && g_last_su_gwt_hwnd == prev_hwnd &&
            (now - g_last_su_gwt_mono) < kSuGwtRevalidateMin) {
            return prev_hwnd;
        }
        const std::wstring title = windowText(reinterpret_cast<HWND>(prev_hwnd));
        g_last_su_gwt_mono = now;
        g_last_su_gwt_hwnd = prev_hwnd;
        if (smartUpdaterTitleMatches(title, korean_substr)) {
            return prev_hwnd;
        }
    }
    if (!prev_hwnd && (now - g_last_su_enum_mono) < kSuEnumMinInterval) {
        // AGENT: Throttle re-enumeration but still return last known launcher HWND (capture UI
        // often calls with prev=0; returning 0 here caused flaky Start Game launcher capture).
        if (g_last_su_gwt_hwnd && isWindow(g_last_su_gwt_hwnd)) {
            const std::wstring title = windowText(reinterpret_cast<HWND>(g_last_su_gwt_hwnd));
            if (smartUpdaterTitleMatches(title, korean_substr)) {
                return g_last_su_gwt_hwnd;
            }
        }
        return 0;
    }
    g_last_su_gwt_hwnd = 0;
    g_last_su_gwt_mono = 0.0;
    const std::intptr_t found = findSmartUpdaterWindow(korean_substr);
    g_last_su_enum_mono = nowMono();
    if (found) {
        g_last_su_gwt_hwnd = found;
        g_last_su_gwt_mono = nowMono();
    }
    return found;
#else
    (void)prev_hwnd;
    (void)korean_substr;
    return 0;
#endif
}

std::optional<std::pair<int, int>> matchCenterToScreen(std::intptr_t hwnd,
                                                       const double region[4],
                                                       bool has_region,
                                                       int match_center_x,
                                                       int match_center_y) {
#ifdef _WIN32
    if (!isWindow(hwnd)) {
        return std::nullopt;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    RECT cr{};
    if (!GetClientRect(who, &cr)) {
        return std::nullopt;
    }
    const int cw = cr.right - cr.left;
    const int ch = cr.bottom - cr.top;
    int client_x = match_center_x;
    int client_y = match_center_y;
    if (has_region && region) {
        if (auto px = vision::regionPixels(cw, ch, region)) {
            client_x = (*px)[0] + match_center_x;
            client_y = (*px)[1] + match_center_y;
        }
    }
    POINT pt{client_x, client_y};
    if (!ClientToScreen(who, &pt)) {
        return std::nullopt;
    }
    return std::pair<int, int>{pt.x, pt.y};
#else
    (void)hwnd;
    (void)region;
    (void)has_region;
    (void)match_center_x;
    (void)match_center_y;
    return std::nullopt;
#endif
}

}  // namespace pipela::core::win32
