#include "shell/dev_ui_mode.hpp"

#include <QCoreApplication>

#include <cstdlib>
#include <string>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"

namespace pipela::ui::shell {

namespace {

bool envMatches(const char* key, const char* const* values, std::size_t count) {
    const char* raw = std::getenv(key);
    if (raw == nullptr || raw[0] == '\0') {
        return false;
    }
    std::string v(raw);
    for (char& c : v) {
        if (c >= 'A' && c <= 'Z') {
            c = static_cast<char>(c - 'A' + 'a');
        }
    }
    for (std::size_t i = 0; i < count; ++i) {
        if (v == values[i]) {
            return true;
        }
    }
    return false;
}

bool envTruthy(const char* key) {
    static const char* kTruthy[] = {"1", "true", "yes", "on", "y"};
    return envMatches(key, kTruthy, sizeof(kTruthy) / sizeof(kTruthy[0]));
}

bool envFalsy(const char* key) {
    static const char* kFalsy[] = {"0", "false", "no", "off", "n"};
    return envMatches(key, kFalsy, sizeof(kFalsy) / sizeof(kFalsy[0]));
}

}  // namespace

bool pipelaDevUiEnabled() {
    const QStringList args = QCoreApplication::arguments();
    if (args.contains(QString::fromUtf8("--dev-ui"))) {
        return true;
    }
    if (args.contains(QString::fromUtf8("--no-dev-ui"))) {
        return false;
    }
    for (const char* key : {"PIPELA_DEV_UI", "PIPELA_DEBUG_UI"}) {
        if (envTruthy(key)) {
            return true;
        }
        if (envFalsy(key)) {
            return false;
        }
    }
    // C++ Pipela.exe is always a shipped binary — default off unless env/argv forces on.
    return false;
}

bool pipelaDevUiNoAnchor(pipela::ui::dock::UiDockPhase phase) {
    return phase == pipela::ui::dock::UiDockPhase::Standby;
}

bool pipelaDevUiStandbyChrome(pipela::ui::dock::UiDockPhase phase) {
    return pipelaDevUiEnabled() && pipelaDevUiNoAnchor(phase);
}

namespace {

constexpr const char* kLauncherDebugChromeKey = "pipela_launcher_debug_chrome";

}  // namespace

bool pipelaLauncherDebugChromeEnabled() {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(kLauncherDebugChromeKey);
    if (it == all.end()) {
        return false;
    }
    return pipela::core::registry::parseBool(it->second);
}

void setPipelaLauncherDebugChromeEnabled(bool enabled) {
    pipela::core::registry::saveBoolValue(kLauncherDebugChromeKey, enabled);
}

}  // namespace pipela::ui::shell
