#include "pipela/core/win32/game_windows.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::win32 {

bool isWindow(std::intptr_t hwnd) {
#ifdef _WIN32
    return hwnd != 0 && IsWindow(reinterpret_cast<HWND>(hwnd)) != FALSE;
#else
    (void)hwnd;
    return false;
#endif
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
    ClientToScreen(reinterpret_cast<HWND>(hwnd), &tl);
    const int w = cr.right - cr.left;
    const int h = cr.bottom - cr.top;
    return {tl.x, tl.y, tl.x + w, tl.y + h};
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

}  // namespace pipela::core::win32
