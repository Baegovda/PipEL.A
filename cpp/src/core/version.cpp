#include "pipela/core/version.hpp"

namespace pipela::core {

std::string appVersion() { return "0.10.18"; }

std::string stripDisplayVersion() { return appVersion(); }

}  // namespace pipela::core
