#include "pipela/core/registry/store.hpp"

#include <fstream>
#include <nlohmann/json.hpp>
#include <sstream>
#include <stdexcept>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::registry {

namespace {

std::wstring utf8ToWide(const std::string& utf8) {
    if (utf8.empty()) {
        return {};
    }
    const int chars = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), static_cast<int>(utf8.size()),
                                          nullptr, 0);
    std::wstring wide(static_cast<size_t>(chars), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), static_cast<int>(utf8.size()), wide.data(), chars);
    return wide;
}

std::string wideToUtf8(const wchar_t* wide, int char_count) {
    if (wide == nullptr || char_count <= 0) {
        return {};
    }
    const int bytes =
        WideCharToMultiByte(CP_UTF8, 0, wide, char_count, nullptr, 0, nullptr, nullptr);
    if (bytes <= 0) {
        return {};
    }
    std::string out(static_cast<size_t>(bytes), '\0');
    WideCharToMultiByte(CP_UTF8, 0, wide, char_count, out.data(), bytes, nullptr, nullptr);
    return out;
}

HKEY openOrCreatePipelaKey(REGSAM access) {
    HKEY key = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\Pipela", 0, nullptr, 0, access, nullptr, &key,
                        nullptr) != ERROR_SUCCESS) {
        return nullptr;
    }
    return key;
}

}  // namespace

std::map<std::string, std::string> loadAllStringValues() {
    std::map<std::string, std::string> out;
#ifdef _WIN32
    HKEY key = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Pipela", 0, KEY_READ, &key) != ERROR_SUCCESS) {
        return out;
    }
    DWORD count = 0;
    DWORD max_name = 0;
    DWORD max_data = 0;
    if (RegQueryInfoKeyW(key, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, &count,
                         &max_name, &max_data, nullptr, nullptr) != ERROR_SUCCESS) {
        RegCloseKey(key);
        return out;
    }
    std::wstring name_w(max_name + 1, L'\0');
    std::vector<BYTE> data(max_data + 2, 0);
    for (DWORD i = 0; i < count; ++i) {
        DWORD name_len = max_name + 1;
        DWORD data_len = max_data + 2;
        DWORD type = 0;
        if (RegEnumValueW(key, i, name_w.data(), &name_len, nullptr, &type, data.data(),
                          &data_len) != ERROR_SUCCESS) {
            continue;
        }
        if (type != REG_SZ) {
            continue;
        }
        const std::string name_utf8 = wideToUtf8(name_w.c_str(), static_cast<int>(name_len));
        const wchar_t* value_w = reinterpret_cast<const wchar_t*>(data.data());
        const int value_chars = static_cast<int>(data_len / sizeof(wchar_t));
        int value_len = value_chars;
        if (value_len > 0 && value_w[value_len - 1] == L'\0') {
            --value_len;
        }
        const std::string value = wideToUtf8(value_w, value_len);
        out.emplace(name_utf8, value);
    }
    RegCloseKey(key);
#endif
    return out;
}

bool saveStringValue(const std::string& name, const std::string& value) {
#ifdef _WIN32
    HKEY key = openOrCreatePipelaKey(KEY_SET_VALUE);
    if (!key) {
        return false;
    }
    const std::wstring name_w = utf8ToWide(name);
    const std::wstring value_w = utf8ToWide(value);
    const LSTATUS st = RegSetValueExW(key, name_w.c_str(), 0, REG_SZ,
                                        reinterpret_cast<const BYTE*>(value_w.c_str()),
                                        static_cast<DWORD>((value_w.size() + 1) * sizeof(wchar_t)));
    RegCloseKey(key);
    return st == ERROR_SUCCESS;
#else
    (void)name;
    (void)value;
    return false;
#endif
}

bool saveBoolValue(const std::string& name, bool value) {
    return saveStringValue(name, value ? "true" : "false");
}

SchemaDocument loadSchemaFromFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("cannot open schema: " + path);
    }
    nlohmann::json j;
    in >> j;
    SchemaDocument doc;
    doc.registry_path = j.value("registry_path", "Software\\Pipela");
    doc.schema_version = j.value("schema_version", 0);
    doc.entry_count = j.value("entry_count", 0);
    if (j.contains("entries") && j["entries"].is_array()) {
        for (const auto& e : j["entries"]) {
            SchemaEntry row;
            row.registry_key = e.value("registry_key", "");
            row.value_type = e.value("value_type", "unknown");
            if (e.contains("global_name") && e["global_name"].is_string()) {
                row.global_name = e["global_name"].get<std::string>();
            }
            if (e.contains("default")) {
                if (e["default"].is_string()) {
                    row.default_value = e["default"].get<std::string>();
                } else {
                    row.default_value = e["default"].dump();
                }
            }
            if (!row.registry_key.empty()) {
                doc.entries.push_back(std::move(row));
            }
        }
    }
    if (doc.entry_count == 0) {
        doc.entry_count = static_cast<int>(doc.entries.size());
    }
    return doc;
}

}  // namespace pipela::core::registry
