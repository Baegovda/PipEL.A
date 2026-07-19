#pragma once

namespace pipela::core::win32 {

void mouseLeftClick();
void mouseRightDown();
void mouseRightUp();
void sendVirtualKey(unsigned short vk, bool key_up = false);

}  // namespace pipela::core::win32
