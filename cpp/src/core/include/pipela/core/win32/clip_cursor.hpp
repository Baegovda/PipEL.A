#pragma once

namespace pipela::core::win32 {

bool clipCursorToScreenRect(int left, int top, int right, int bottom);
void clipCursorRelease();

}  // namespace pipela::core::win32
