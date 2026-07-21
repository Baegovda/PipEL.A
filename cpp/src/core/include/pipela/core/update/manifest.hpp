#pragma once

#include <optional>
#include <string>
#include <tuple>
#include <vector>

#include <nlohmann/json.hpp>

namespace pipela::core::update {

// AGENT: Mirrors main.py _pipela_version_tuple — compare first three numeric segments.
std::tuple<int, int, int> versionTuple(const std::string& ver_str);

int compareVersions(const std::string& a, const std::string& b);

std::string defaultManifestUrl();

std::string manifestUrlFromEnv();

std::string reinstallDownloadUrlFromEnv();

std::optional<std::string> manifestDownloadUrl(const nlohmann::json& obj);

std::optional<std::string> manifestBrowserUrl(const nlohmann::json& obj);

// HTTP(S) GET JSON manifest. Returns (json, error). error codes match Python where noted.
std::pair<nlohmann::json, std::string> fetchUpdateManifest();

std::pair<std::string, std::string> resolveReinstallDownloadUrl();

}  // namespace pipela::core::update
