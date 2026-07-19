#pragma once

namespace pipela::core::win32 {

void mouseLeftClick();
void mouseRightDown();
void mouseRightUp();
void sendVirtualKey(unsigned short vk, bool key_up = false);
void setCapsLock(bool on);
void mouseMove(int x, int y);
void mouseLeftDoubleClick();

}  // namespace pipela::core::win32
