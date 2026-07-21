#include "pipela/core/paths.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <shlobj.h>
#include <windows.h>
#endif

#include <filesystem>

namespace pipela::core {

std::string resolveRepoRoot() {
    // AGENT: dev default — CMake defines PIPELA_REPO_ROOT for packaged builds.
#ifdef PIPELA_REPO_ROOT
    return PIPELA_REPO_ROOT;
#else
    return "..";
#endif
}

std::string assetsDir() { return resolveRepoRoot() + "/assets"; }

std::string splashImagePath() { return assetsDir() + "/splash.png"; }

std::string registrySchemaPath() { return resolveRepoRoot() + "/registry/schema.json"; }

std::string templateCaptureUserStorageDir() {
#ifdef _WIN32
    wchar_t local_app[MAX_PATH]{};
    if (SHGetFolderPathW(nullptr, CSIDL_LOCAL_APPDATA, nullptr, SHGFP_TYPE_CURRENT,
                         local_app) != S_OK) {
        return resolveRepoRoot() + "/templates";
    }
    const int chars = WideCharToMultiByte(CP_UTF8, 0, local_app, -1, nullptr, 0, nullptr, nullptr);
    std::string base(static_cast<size_t>(chars > 0 ? chars - 1 : 0), '\0');
    if (chars > 0) {
        WideCharToMultiByte(CP_UTF8, 0, local_app, -1, base.data(), chars, nullptr, nullptr);
    }
    const std::filesystem::path dir = std::filesystem::path(base) / "Pipela" / "templates";
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    return dir.string();
#else
    return resolveRepoRoot() + "/templates";
#endif
}

std::string localPipelaDataDir() {
#ifdef _WIN32
    wchar_t local_app[MAX_PATH]{};
    if (SHGetFolderPathW(nullptr, CSIDL_LOCAL_APPDATA, nullptr, SHGFP_TYPE_CURRENT,
                         local_app) != S_OK) {
        return resolveRepoRoot();
    }
    const int chars = WideCharToMultiByte(CP_UTF8, 0, local_app, -1, nullptr, 0, nullptr, nullptr);
    std::string base(static_cast<size_t>(chars > 0 ? chars - 1 : 0), '\0');
    if (chars > 0) {
        WideCharToMultiByte(CP_UTF8, 0, local_app, -1, base.data(), chars, nullptr, nullptr);
    }
    const std::filesystem::path dir = std::filesystem::path(base) / "Pipela";
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    return dir.string();
#else
    return resolveRepoRoot();
#endif
}

std::string killCounterStatsFilePath() {
#ifdef _WIN32
    const std::filesystem::path dir = std::filesystem::path(localPipelaDataDir());
    return (dir / "kill_counter_stats.json").string();
#else
    return resolveRepoRoot() + "/kill_counter_stats.json";
#endif
}

}  // namespace pipela::core
