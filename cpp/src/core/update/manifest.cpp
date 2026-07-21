#include "pipela/core/update/manifest.hpp"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <sstream>

#include "pipela/core/version.hpp"

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <winhttp.h>
#endif

namespace pipela::core::update {

namespace {

std::string trim(const std::string& s) {
    const auto start = s.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) {
        return {};
    }
    const auto end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

std::string envVar(const char* name) {
#if defined(_WIN32)
    char* buf = nullptr;
    size_t len = 0;
    if (_dupenv_s(&buf, &len, name) != 0 || buf == nullptr) {
        free(buf);
        return {};
    }
    const std::string out(buf);
    free(buf);
    return trim(out);
#else
    const char* v = std::getenv(name);
    return v ? trim(v) : std::string{};
#endif
}

int parseVersionPart(const std::string& part) {
    int n = 0;
    bool any = false;
    for (char ch : part) {
        if (std::isdigit(static_cast<unsigned char>(ch))) {
            any = true;
            n = n * 10 + (ch - '0');
        } else {
            break;
        }
    }
    return any ? n : 0;
}

#if defined(_WIN32)
std::wstring toWide(const std::string& utf8) {
    if (utf8.empty()) {
        return {};
    }
    const int need = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    if (need <= 0) {
        return {};
    }
    std::wstring out(static_cast<size_t>(need), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, out.data(), need);
    if (!out.empty() && out.back() == L'\0') {
        out.pop_back();
    }
    return out;
}

std::string wideToUtf8(const std::wstring& w) {
    if (w.empty()) {
        return {};
    }
    const int need = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (need <= 0) {
        return {};
    }
    std::string out(static_cast<size_t>(need), '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, out.data(), need, nullptr, nullptr);
    if (!out.empty() && out.back() == '\0') {
        out.pop_back();
    }
    return out;
}

std::pair<std::string, std::string> httpGetUtf8(const std::wstring& host, const std::wstring& path,
                                                const std::wstring& user_agent) {
    HINTERNET session =
        WinHttpOpen(user_agent.c_str(), WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                    WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) {
        return {"", "WinHttpOpen failed"};
    }
    WinHttpSetTimeouts(session, 15000, 15000, 15000, 15000);
    HINTERNET connect = WinHttpConnect(session, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!connect) {
        WinHttpCloseHandle(session);
        return {"", "WinHttpConnect failed"};
    }
    HINTERNET request = WinHttpOpenRequest(connect, L"GET", path.c_str(), nullptr,
                                           WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                           WINHTTP_FLAG_SECURE);
    if (!request) {
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return {"", "WinHttpOpenRequest failed"};
    }
    const BOOL sent = WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                         WINHTTP_NO_REQUEST_DATA, 0, 0, 0);
    if (!sent || !WinHttpReceiveResponse(request, nullptr)) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return {"", "HTTP request failed"};
    }
    DWORD status = 0;
    DWORD status_size = sizeof(status);
    WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                        WINHTTP_HEADER_NAME_BY_INDEX, &status, &status_size,
                        WINHTTP_NO_HEADER_INDEX);
    if (status < 200 || status >= 300) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return {"", "HTTP " + std::to_string(status)};
    }
    std::string body;
    DWORD avail = 0;
    while (WinHttpQueryDataAvailable(request, &avail) && avail > 0) {
        std::vector<char> chunk(avail);
        DWORD read = 0;
        if (!WinHttpReadData(request, chunk.data(), avail, &read)) {
            break;
        }
        body.append(chunk.data(), read);
    }
    WinHttpCloseHandle(request);
    WinHttpCloseHandle(connect);
    WinHttpCloseHandle(session);
    return {body, ""};
}

bool parseUrl(const std::string& url, std::wstring& host, std::wstring& path) {
    const std::wstring wurl = toWide(url);
    URL_COMPONENTS parts{};
    parts.dwStructSize = sizeof(parts);
    wchar_t host_buf[256]{};
    wchar_t path_buf[2048]{};
    parts.lpszHostName = host_buf;
    parts.dwHostNameLength = static_cast<DWORD>(std::size(host_buf));
    parts.lpszUrlPath = path_buf;
    parts.dwUrlPathLength = static_cast<DWORD>(std::size(path_buf));
    if (!WinHttpCrackUrl(wurl.c_str(), 0, 0, &parts)) {
        return false;
    }
    host = host_buf;
    path = path_buf[0] ? path_buf : L"/";
    return true;
}
#endif

}  // namespace

std::tuple<int, int, int> versionTuple(const std::string& ver_str) {
    std::vector<int> parts;
    std::istringstream stream(ver_str);
    std::string token;
    while (std::getline(stream, token, '.')) {
        parts.push_back(parseVersionPart(trim(token)));
    }
    while (parts.size() < 3) {
        parts.push_back(0);
    }
    return {parts[0], parts[1], parts[2]};
}

int compareVersions(const std::string& a, const std::string& b) {
    const auto ta = versionTuple(a);
    const auto tb = versionTuple(b);
    if (ta < tb) {
        return -1;
    }
    if (ta > tb) {
        return 1;
    }
    return 0;
}

std::string defaultManifestUrl() {
    return "https://raw.githubusercontent.com/Baegovda/PipEL.A/refs/heads/main/version.json";
}

std::string manifestUrlFromEnv() {
    const std::string env = envVar("PIPELA_UPDATE_MANIFEST_URL");
    if (!env.empty()) {
        return env;
    }
    return defaultManifestUrl();
}

std::string reinstallDownloadUrlFromEnv() {
    std::string u = envVar("PIPELA_REINSTALL_DOWNLOAD_URL");
    if (u.empty()) {
        u = envVar("PIPELA_REINSTALL_EXE_URL");
    }
    return u;
}

std::optional<std::string> manifestDownloadUrl(const nlohmann::json& obj) {
    if (!obj.is_object()) {
        return std::nullopt;
    }
    for (const char* key : {"download_url", "url"}) {
        if (obj.contains(key) && obj[key].is_string()) {
            const std::string s = trim(obj[key].get<std::string>());
            if (!s.empty()) {
                return s;
            }
        }
    }
    return std::nullopt;
}

std::optional<std::string> manifestBrowserUrl(const nlohmann::json& obj) {
    if (!obj.is_object()) {
        return std::nullopt;
    }
    for (const char* key : {"release_url", "release_page_url"}) {
        if (obj.contains(key) && obj[key].is_string()) {
            const std::string s = trim(obj[key].get<std::string>());
            if (!s.empty()) {
                return s;
            }
        }
    }
    return manifestDownloadUrl(obj);
}

std::pair<nlohmann::json, std::string> fetchUpdateManifest() {
    const std::string url = manifestUrlFromEnv();
    if (url.empty()) {
        return {nlohmann::json{}, "no_manifest_url"};
    }
#if !defined(_WIN32)
    return {nlohmann::json{}, "WinHTTP unavailable"};
#else
    std::wstring host;
    std::wstring path;
    if (!parseUrl(url, host, path)) {
        return {nlohmann::json{}, "invalid manifest URL"};
    }
    const std::wstring ua =
        toWide(std::string(kAppDisplayName) + "/" + appVersion() + " (update-check)");
    auto [body, err] = httpGetUtf8(host, path, ua);
    if (!err.empty()) {
        return {nlohmann::json{}, err};
    }
    try {
        nlohmann::json data = nlohmann::json::parse(body);
        if (!data.is_object()) {
            return {nlohmann::json{}, "invalid_json_object"};
        }
        return {data, ""};
    } catch (const std::exception& ex) {
        return {nlohmann::json{}, std::string("JSON error: ") + ex.what()};
    }
#endif
}

std::pair<std::string, std::string> resolveReinstallDownloadUrl() {
    const std::string forced = reinstallDownloadUrlFromEnv();
    if (!forced.empty()) {
        return {forced, ""};
    }
    auto [data, err] = fetchUpdateManifest();
    if (!err.empty()) {
        return {"", "manifest: " + err};
    }
    const auto dl = manifestDownloadUrl(data);
    if (!dl) {
        return {"", "download_url missing — set PIPELA_REINSTALL_DOWNLOAD_URL or fill manifest JSON"};
    }
    return {*dl, ""};
}

}  // namespace pipela::core::update
