#pragma once

#include <string>

namespace pipela::core {

std::string resolveRepoRoot();
std::string assetsDir();
std::string splashImagePath();
std::string registrySchemaPath();
std::string templateCaptureUserStorageDir();
std::string killCounterStatsFilePath();
std::string localPipelaDataDir();

}  // namespace pipela::core
