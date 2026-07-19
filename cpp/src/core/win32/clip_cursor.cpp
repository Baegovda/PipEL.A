#include "pipela/core/win32/clip_cursor.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::win32 {

bool clipCursorToScreenRect(int left, int top, int right, int bottom) {
#ifdef _WIN32
    if (right <= left || bottom <= top) {
        return false;
    }
    RECT r{left, top, right, bottom};
    return ClipCursor(&r) != FALSE;
#else
    (void)left;
    (void)top;
    (void)right;
    (void)bottom;
    return false;
#endif
}

void clipCursorRelease() {
#ifdef _WIN32
    ClipCursor(nullptr);
#endif
}

}  // namespace pipela::core::win32
