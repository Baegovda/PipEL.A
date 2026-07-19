#include "pipela/core/registry/store.hpp"

#include <fstream>
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

namespace {

std::string readFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("cannot open schema: " + path);
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

std::optional<std::string> extractJsonString(const std::string& blob, const std::string& key) {
    const std::string needle = "\"" + key + "\"";
    const auto pos = blob.find(needle);
    if (pos == std::string::npos) {
        return std::nullopt;
    }
    const auto colon = blob.find(':', pos + needle.size());
    if (colon == std::string::npos) {
        return std::nullopt;
    }
    const auto q1 = blob.find('"', colon + 1);
    if (q1 == std::string::npos) {
        return std::nullopt;
    }
    const auto q2 = blob.find('"', q1 + 1);
    if (q2 == std::string::npos) {
        return std::nullopt;
    }
    return blob.substr(q1 + 1, q2 - q1 - 1);
}

}  // namespace

SchemaDocument loadSchemaFromRepo(const std::string& repo_root) {
    const std::string path = repo_root + "/registry/schema.json";
    const std::string blob = readFile(path);
    SchemaDocument doc;
    if (auto rp = extractJsonString(blob, "registry_path")) {
        doc.registry_path = *rp;
    }
    const auto ver_pos = blob.find("\"schema_version\"");
    if (ver_pos != std::string::npos) {
        const auto colon = blob.find(':', ver_pos);
        if (colon != std::string::npos) {
            doc.schema_version = std::stoi(blob.substr(colon + 1));
        }
    }
    // Minimal parser: count "registry_key" occurrences for parity harness.
    for (size_t i = 0; (i = blob.find("\"registry_key\"", i)) != std::string::npos; ++i) {
        SchemaEntry e;
        const auto colon = blob.find(':', i);
        const auto q1 = blob.find('"', colon + 1);
        const auto q2 = blob.find('"', q1 + 1);
        if (q1 != std::string::npos && q2 != std::string::npos) {
            e.registry_key = blob.substr(q1 + 1, q2 - q1 - 1);
            e.value_type = "unknown";
            doc.entries.push_back(std::move(e));
        }
    }
    return doc;
}

}  // namespace pipela::core::registry
