#include "pipela/core/input/keymap.hpp"

#include <cctype>
#include <cstdio>

namespace pipela::core::input {

std::optional<unsigned int> asciiCharToVk(char ch) {
    const unsigned char u = static_cast<unsigned char>(ch);
    if (std::isalpha(u)) {
        return static_cast<unsigned int>(std::toupper(u));
    }
    if (std::isdigit(u)) {
        return static_cast<unsigned int>(u);
    }
    return std::nullopt;
}

bool isNamedFunctionKeyVk(unsigned int vk) {
    return vk >= 0x70 && vk <= 0x7B;
}

std::string vkToDisplayName(unsigned int vk) {
    vk &= 0xFF;
    if (vk >= 0x30 && vk <= 0x39) {
        return std::string(1, static_cast<char>(vk));
    }
    if (vk >= 0x41 && vk <= 0x5A) {
        return std::string(1, static_cast<char>(vk));
    }
    if (vk >= 0x70 && vk <= 0x7B) {
        return "F" + std::to_string(vk - 0x70 + 1);
    }
    switch (vk) {
        case 0x20:
            return "Space";
        case 0x0D:
            return "Enter";
        case 0x09:
            return "Tab";
        case 0x1B:
            return "Esc";
        case 0x08:
            return "Backspace";
        case 0x2D:
            return "Insert";
        case 0x2E:
            return "Delete";
        case 0x21:
            return "PgUp";
        case 0x22:
            return "PgDn";
        case 0x23:
            return "End";
        case 0x24:
            return "Home";
        case 0x25:
            return "Left";
        case 0x26:
            return "Up";
        case 0x27:
            return "Right";
        case 0x28:
            return "Down";
        default:
            break;
    }
    char buf[8];
    std::snprintf(buf, sizeof(buf), "0x%02X", vk);
    return buf;
}

}  // namespace pipela::core::input
