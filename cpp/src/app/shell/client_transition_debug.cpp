#include "shell/client_transition_debug.hpp"

#include <cstdlib>
#include <iostream>

namespace pipela::app::shell {

namespace {

bool truthy(const char* raw) {
    if (raw == nullptr || *raw == '\0') {
        return false;
    }
    const std::string s(raw);
    return s == "1" || s == "true" || s == "yes" || s == "on" || s == "y";
}

bool falsyExplicit(const char* raw) {
    if (raw == nullptr || *raw == '\0') {
        return false;
    }
    const std::string s(raw);
    return s == "0" || s == "false" || s == "no" || s == "off" || s == "n";
}

bool parseEnabled() {
    const char* k1 = std::getenv("PIPELA_DEBUG_CLIENT_TRANSITION");
    const char* k2 = std::getenv("PIPELA_DEBUG_CLIENT_DOCK");
    if (falsyExplicit(k1) || falsyExplicit(k2)) {
        return false;
    }
    return truthy(k1) || truthy(k2);
}

}  // namespace

bool clientTransitionDebugEnabled() {
    static const bool enabled = parseEnabled();
    return enabled;
}

void clientTransitionLog(const std::string& msg) {
    if (!clientTransitionDebugEnabled()) {
        return;
    }
    static bool banner = false;
    if (!banner) {
        banner = true;
        std::cerr << "[Pipela:CLIENT_TRANSITION] stderr debug ON "
                     "(PIPELA_DEBUG_CLIENT_TRANSITION=0 to disable)\n";
    }
    std::cerr << "[Pipela:CLIENT_TRANSITION] " << msg << '\n';
}

}  // namespace pipela::app::shell
