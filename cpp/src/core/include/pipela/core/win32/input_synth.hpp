#pragma once

namespace pipela::core::win32 {

// AGENT: True while synthetic input is in flight — low-level hooks must ignore matching events.
bool synthIgnoreLeft();
bool synthIgnoreRight();

void mouseLeftClick();
void mouseRightDown();
void mouseRightUp();
void sendVirtualKey(unsigned short vk, bool key_up = false);
void setCapsLock(bool on);
void mouseMove(int x, int y);
void mouseLeftDoubleClick();

}  // namespace pipela::core::win32
