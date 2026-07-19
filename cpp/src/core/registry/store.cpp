#include "pipela/core/registry/store.hpp"

#include <fstream>
#include <nlohmann/json.hpp>
#include <sstream>
#include <stdexcept>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::registry {

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
        const int name_chars =
            WideCharToMultiByte(CP_UTF8, 0, name_w.c_str(), static_cast<int>(name_len), nullptr,
                                0, nullptr, nullptr);
        std::string name_utf8(static_cast<size_t>(name_chars), '\0');
        WideCharToMultiByte(CP_UTF8, 0, name_w.c_str(), static_cast<int>(name_len), name_utf8.data(),
                            name_chars, nullptr, nullptr);
        std::string value(reinterpret_cast<char*>(data.data()));
        out.emplace(std::move(name_utf8), std::move(value));
    }
    RegCloseKey(key);
#endif
    return out;
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
