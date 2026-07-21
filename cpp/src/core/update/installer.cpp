#include "pipela/core/update/installer.hpp"

#include "pipela/core/paths.hpp"
#include "pipela/core/version.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <shellapi.h>
#include <winhttp.h>
#endif

namespace pipela::core::update {

namespace {

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

int runHiddenCommand(const std::wstring& command_line) {
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi{};
    std::wstring cmd = command_line;
    if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr,
                        nullptr, &si, &pi)) {
        return -1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return static_cast<int>(code);
}
#endif

}  // namespace

std::string downloadUrlToFile(const std::string& url, const std::string& dest_path) {
#if !defined(_WIN32)
    (void)url;
    (void)dest_path;
    return "download unsupported";
#else
    std::wstring host;
    std::wstring path;
    if (!parseUrl(url, host, path)) {
        return "invalid download URL";
    }
    std::filesystem::path dest(dest_path);
    std::error_code ec;
    std::filesystem::create_directories(dest.parent_path(), ec);

    HINTERNET session = WinHttpOpen(
        toWide(std::string(kAppDisplayName) + "/" + appVersion() + " (update-download)").c_str(),
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) {
        return "WinHttpOpen failed";
    }
    WinHttpSetTimeouts(session, 30000, 30000, 120000, 120000);
    HINTERNET connect = WinHttpConnect(session, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!connect) {
        WinHttpCloseHandle(session);
        return "WinHttpConnect failed";
    }
    HINTERNET request = WinHttpOpenRequest(connect, L"GET", path.c_str(), nullptr,
                                           WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                           WINHTTP_FLAG_SECURE);
    if (!request) {
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return "WinHttpOpenRequest failed";
    }
    if (!WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0,
                            0, 0) ||
        !WinHttpReceiveResponse(request, nullptr)) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return "HTTP request failed";
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
        return "HTTP " + std::to_string(status);
    }

    std::ofstream out(dest_path, std::ios::binary | std::ios::trunc);
    if (!out) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return "cannot open dest file";
    }
    DWORD avail = 0;
    while (WinHttpQueryDataAvailable(request, &avail) && avail > 0) {
        std::vector<char> chunk(avail);
        DWORD read = 0;
        if (!WinHttpReadData(request, chunk.data(), avail, &read)) {
            break;
        }
        out.write(chunk.data(), static_cast<std::streamsize>(read));
    }
    out.close();
    WinHttpCloseHandle(request);
    WinHttpCloseHandle(connect);
    WinHttpCloseHandle(session);
    if (!out.good()) {
        return "download write failed";
    }
    return {};
#endif
}

std::string currentExecutablePath() {
#if defined(_WIN32)
    wchar_t buf[MAX_PATH]{};
    const DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) {
        return {};
    }
    return wideToUtf8(buf);
#else
    return {};
#endif
}

std::string installDirectoryFromExePath(const std::string& exe_path) {
    if (exe_path.empty()) {
        return {};
    }
    std::filesystem::path p(exe_path);
    return p.parent_path().string();
}

std::string updatesCacheDir() {
    const std::filesystem::path base(localPipelaDataDir());
    const std::filesystem::path dir = base / "updates";
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    return dir.string();
}

std::string extractZipArchive(const std::string& zip_path, const std::string& dest_dir) {
#if !defined(_WIN32)
    (void)zip_path;
    (void)dest_dir;
    return "extract unsupported";
#else
    std::error_code ec;
    std::filesystem::create_directories(dest_dir, ec);
    std::filesystem::remove_all(dest_dir, ec);
    std::filesystem::create_directories(dest_dir, ec);

    std::wstring cmd = L"powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"Expand-Archive -LiteralPath '";
    cmd += toWide(zip_path);
    cmd += L"' -DestinationPath '";
    cmd += toWide(dest_dir);
    cmd += L"' -Force\"";
    const int code = runHiddenCommand(cmd);
    if (code != 0) {
        return "Expand-Archive failed (code " + std::to_string(code) + ")";
    }
    if (!std::filesystem::exists(std::filesystem::path(dest_dir) / "Pipela.exe")) {
        return "extracted bundle missing Pipela.exe";
    }
    return {};
#endif
}

std::string scheduleInPlaceUpdateAndRelaunch(const std::string& staged_dir,
                                             const std::string& target_dir,
                                             unsigned long parent_pid) {
#if !defined(_WIN32)
    (void)staged_dir;
    (void)target_dir;
    (void)parent_pid;
    return "update unsupported";
#else
    const std::filesystem::path bat_path =
        std::filesystem::path(updatesCacheDir()) /
        ("pipela_apply_" + std::to_string(parent_pid) + ".bat");
    std::ofstream bat(bat_path.string(), std::ios::trunc);
    if (!bat) {
        return "cannot write updater script";
    }
    bat << "@echo off\r\n";
    bat << "setlocal\r\n";
    bat << ":waitloop\r\n";
    bat << "tasklist /FI \"PID eq " << parent_pid << "\" 2>nul | find \"" << parent_pid
        << "\" >nul\r\n";
    bat << "if %errorlevel%==0 (\r\n";
    bat << "  timeout /t 1 /nobreak >nul\r\n";
    bat << "  goto waitloop\r\n";
    bat << ")\r\n";
    bat << "xcopy /E /Y /I \"" << staged_dir << "\\*\" \"" << target_dir << "\\\" >nul\r\n";
    bat << "start \"\" \"" << target_dir << "\\Pipela.exe\"\r\n";
    bat << "del \"%~f0\"\r\n";
    bat.close();

    const std::wstring wbat = toWide(bat_path.string());
    HINSTANCE r = ShellExecuteW(nullptr, L"open", wbat.c_str(), nullptr, nullptr, SW_HIDE);
    if (reinterpret_cast<intptr_t>(r) <= 32) {
        return "ShellExecute updater failed";
    }
    return {};
#endif
}

std::string applyReleaseFromUrl(const std::string& download_url, const std::string& version,
                                unsigned long parent_pid) {
    if (download_url.empty()) {
        return "empty download_url";
    }
    const std::string zip_path =
        (std::filesystem::path(updatesCacheDir()) / ("Pipela-cpp-" + version + "-win64.zip"))
            .string();
    if (const std::string dl_err = downloadUrlToFile(download_url, zip_path); !dl_err.empty()) {
        return "download: " + dl_err;
    }
    const std::string stage_dir =
        (std::filesystem::path(updatesCacheDir()) / "stage" / version).string();
    if (const std::string ex_err = extractZipArchive(zip_path, stage_dir); !ex_err.empty()) {
        return ex_err;
    }
    const std::string exe = currentExecutablePath();
    const std::string target = installDirectoryFromExePath(exe);
    if (target.empty()) {
        return "cannot resolve install directory";
    }
    return scheduleInPlaceUpdateAndRelaunch(stage_dir, target, parent_pid);
}

}  // namespace pipela::core::update
