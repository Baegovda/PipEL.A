#pragma once

#include <string>

namespace pipela::core::update {

// AGENT: Stream HTTPS GET to a local file (WinHTTP). Returns empty error on success.
std::string downloadUrlToFile(const std::string& url, const std::string& dest_path);

std::string currentExecutablePath();

std::string installDirectoryFromExePath(const std::string& exe_path);

std::string updatesCacheDir();

// AGENT: Extract zip via PowerShell Expand-Archive into dest_dir (created if needed).
std::string extractZipArchive(const std::string& zip_path, const std::string& dest_dir);

// AGENT: Write updater batch, launch it, return empty on success (caller should quit app).
std::string scheduleInPlaceUpdateAndRelaunch(const std::string& staged_dir,
                                             const std::string& target_dir,
                                             unsigned long parent_pid);

// AGENT: Download manifest zip, extract, schedule replace — end-to-end apply.
std::string applyReleaseFromUrl(const std::string& download_url, const std::string& version,
                                unsigned long parent_pid);

}  // namespace pipela::core::update
