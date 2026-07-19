#include "pipela/core/paths.hpp"

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

std::string registrySchemaPath() { return resolveRepoRoot() + "/registry/schema.json"; }

}  // namespace pipela::core
