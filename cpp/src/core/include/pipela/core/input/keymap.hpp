#pragma once

#include <optional>
#include <string>

namespace pipela::core::input {

// AGENT: Windows VK for single ASCII letter/digit; mirrors pipela_core/input_keymap.py subset.
std::optional<unsigned int> asciiCharToVk(char ch);

bool isNamedFunctionKeyVk(unsigned int vk);

// AGENT: Mirrors pipela_core/win32_input_constants.vk_to_display_name.
std::string vkToDisplayName(unsigned int vk);

}  // namespace pipela::core::input
