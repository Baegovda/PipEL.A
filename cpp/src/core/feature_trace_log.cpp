#include "pipela/core/feature_trace_log.hpp"

#include "pipela/core/paths.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/version.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <thread>
#include <unordered_map>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <process.h>
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace pipela::core {

namespace {

std::mutex g_mu;
bool g_session_ready{false};
std::chrono::steady_clock::time_point g_session_start{std::chrono::steady_clock::now()};

bool envDisabled(const char* key) {
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
    return v == "0" || v == "false" || v == "no" || v == "off";
}

std::string envString(const char* key) {
    const char* raw = std::getenv(key);
    return raw != nullptr ? std::string(raw) : std::string();
}

std::string lowerAscii(std::string v) {
    for (char& c : v) {
        if (c >= 'A' && c <= 'Z') {
            c = static_cast<char>(c - 'A' + 'a');
        }
    }
    return v;
}

FeatureTraceDepth parseDepthEnv() {
    const std::string raw = lowerAscii(envString("PIPELA_FEATURE_TRACE_DEPTH"));
    if (raw.empty() || raw == "deep" || raw == "max" || raw == "full") {
        return FeatureTraceDepth::Deep;
    }
    if (raw == "verbose" || raw == "detail") {
        return FeatureTraceDepth::Verbose;
    }
    if (raw == "normal" || raw == "basic" || raw == "lite") {
        return FeatureTraceDepth::Normal;
    }
    if (raw == "0" || raw == "off" || raw == "false" || raw == "no") {
        return FeatureTraceDepth::Off;
    }
    return FeatureTraceDepth::Deep;
}

std::string nowIsoLocal() {
    using clock = std::chrono::system_clock;
    const auto now = clock::now();
    const std::time_t t = clock::to_time_t(now);
    const auto ms =
        std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count() % 1000;
    std::tm tm_buf{};
#ifdef _WIN32
    localtime_s(&tm_buf, &t);
#else
    localtime_r(&t, &tm_buf);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm_buf, "%Y-%m-%dT%H:%M:%S") << '.' << std::setw(3) << std::setfill('0')
        << ms;
    return oss.str();
}

std::string depthLabel(FeatureTraceDepth d) {
    switch (d) {
        case FeatureTraceDepth::Normal:
            return "normal";
        case FeatureTraceDepth::Verbose:
            return "verbose";
        case FeatureTraceDepth::Deep:
            return "deep";
        default:
            return "off";
    }
}

std::string stateValueToString(const state::StateValue& v) {
    if (std::holds_alternative<std::monostate>(v)) {
        return "null";
    }
    if (const auto* b = std::get_if<bool>(&v)) {
        return *b ? "true" : "false";
    }
    if (const auto* i = std::get_if<int>(&v)) {
        return std::to_string(*i);
    }
    if (const auto* l = std::get_if<std::int64_t>(&v)) {
        return std::to_string(*l);
    }
    if (const auto* d = std::get_if<double>(&v)) {
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(4) << *d;
        return oss.str();
    }
    if (const auto* s = std::get_if<std::string>(&v)) {
        if (s->size() > 120) {
            return s->substr(0, 117) + "...";
        }
        return *s;
    }
    return "?";
}

bool stateValuesEqual(const state::StateValue& a, const state::StateValue& b) {
    if (a.index() != b.index()) {
        return false;
    }
    if (std::holds_alternative<std::monostate>(a)) {
        return true;
    }
    if (const auto* ba = std::get_if<bool>(&a)) {
        return *ba == *std::get_if<bool>(&b);
    }
    if (const auto* ia = std::get_if<int>(&a)) {
        return *ia == *std::get_if<int>(&b);
    }
    if (const auto* la = std::get_if<std::int64_t>(&a)) {
        return *la == *std::get_if<std::int64_t>(&b);
    }
    if (const auto* da = std::get_if<double>(&a)) {
        const auto* db = std::get_if<double>(&b);
        return db != nullptr && std::abs(*da - *db) < 1e-9;
    }
    if (const auto* sa = std::get_if<std::string>(&a)) {
        const auto* sb = std::get_if<std::string>(&b);
        return sb != nullptr && *sa == *sb;
    }
    return false;
}

bool isScoreKey(const std::string& key) {
    return key.size() >= 6 && key.compare(key.size() - 6, 6, "_score") == 0;
}

bool isTimestampKey(const std::string& key) {
    return key.find("_time") != std::string::npos || key.find("_ts") != std::string::npos ||
           key.find("_mono") != std::string::npos || key.find("_until") != std::string::npos;
}

FeatureTraceDepth minDepthForStateKey(const std::string& key) {
    if (key == "target_hwnd" || key == "running" || key == "select_mode" ||
        key == "left_click_active" || key == "right_hold_active" ||
        key == "flame_trigger_active" || key == "left_click_feature_enabled" ||
        key == "right_hold_feature_enabled" || key == "flame_trigger_feature_enabled" ||
        key == "reload_active" || key == "ammo_restock_active" || key == "call_merc_active" ||
        key == "kill_counter_enabled" || key == "nobullet_detected" ||
        key == "ammo_restock_sequence_busy" || key == "call_merc_sequence_busy" ||
        key == "left_pressed") {
        return FeatureTraceDepth::Normal;
    }
    if (isScoreKey(key) || key.find("_count") != std::string::npos ||
        key.find("_phase") != std::string::npos || key.find("_detail") != std::string::npos ||
        key.find("_progress") != std::string::npos) {
        return FeatureTraceDepth::Verbose;
    }
    if (isTimestampKey(key)) {
        return FeatureTraceDepth::Deep;
    }
    return FeatureTraceDepth::Verbose;
}

void appendLineUnlocked(const std::string& line) {
    std::ofstream out(featureTraceLogPath(), std::ios::app | std::ios::binary);
    if (!out.is_open()) {
        return;
    }
    out << line << '\n';
    out.flush();
}

void writeSessionHeaderUnlocked() {
    g_session_start = std::chrono::steady_clock::now();
    appendLineUnlocked("=== Pipela feature_trace session " + nowIsoLocal() + " ===");
    appendLineUnlocked("path=" + featureTraceLogPath());
    appendLineUnlocked("version=" + appVersion());
#ifdef _WIN32
    appendLineUnlocked("pid=" + std::to_string(static_cast<unsigned long>(GetCurrentProcessId())));
#else
    appendLineUnlocked("pid=" + std::to_string(static_cast<int>(getpid())));
#endif
    appendLineUnlocked("depth=" + depthLabel(featureTraceDepth()) +
                       " (PIPELA_FEATURE_TRACE_DEPTH=normal|verbose|deep; default deep)");
    appendLineUnlocked(
        "format=+mono_ms thread | category | message  (state/* = AppState writes)");
}

void appendFormattedLine(const char* category, const std::string& message) {
    if (!featureTraceEnabled() || category == nullptr || message.empty()) {
        return;
    }
    std::ostringstream line;
    line << "+" << featureTraceMonoMs() << "ms " << featureTraceThreadTag() << " | " << category
         << " | " << message;
    appendLineUnlocked(line.str());
}

}  // namespace

bool featureTraceEnabled() {
    if (envDisabled("PIPELA_FEATURE_TRACE")) {
        return false;
    }
    return featureTraceDepth() != FeatureTraceDepth::Off;
}

FeatureTraceDepth featureTraceDepth() {
    if (envDisabled("PIPELA_FEATURE_TRACE")) {
        return FeatureTraceDepth::Off;
    }
    return parseDepthEnv();
}

bool featureTraceAtLeast(FeatureTraceDepth min_depth) {
    return static_cast<int>(featureTraceDepth()) >= static_cast<int>(min_depth);
}

std::string featureTraceLogPath() { return localPipelaDataDir() + "/feature_trace.log"; }

uint64_t featureTraceMonoMs() {
    const auto elapsed =
        std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() -
                                                              g_session_start);
    return static_cast<uint64_t>(std::max<int64_t>(0, elapsed.count()));
}

std::string featureTraceThreadTag() {
    const auto tid_hash =
        static_cast<unsigned>(std::hash<std::thread::id>{}(std::this_thread::get_id()) & 0xFFFFu);
    std::ostringstream oss;
    oss << "T" << std::hex << std::setw(4) << std::setfill('0') << tid_hash;
    return oss.str();
}

void featureTraceEnsureSession() {
    if (!featureTraceEnabled()) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_mu);
    if (g_session_ready) {
        return;
    }
    g_session_ready = true;
    writeSessionHeaderUnlocked();
}

void featureTraceLog(const char* category, const std::string& message) {
    featureTraceLogAt(FeatureTraceDepth::Normal, category, message);
}

void featureTraceLogAt(FeatureTraceDepth min_depth, const char* category, const std::string& message) {
    if (!featureTraceAtLeast(min_depth) || category == nullptr || message.empty()) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_mu);
    if (!g_session_ready) {
        g_session_ready = true;
        writeSessionHeaderUnlocked();
    }
    appendFormattedLine(category, message);
}

void featureTraceLogStateChange(const std::string& key,
                                const std::optional<state::StateValue>& old_value,
                                const state::StateValue& new_value) {
    if (!featureTraceEnabled()) {
        return;
    }
    if (old_value && stateValuesEqual(*old_value, new_value)) {
        return;
    }
    const FeatureTraceDepth min_depth = minDepthForStateKey(key);
    if (!featureTraceAtLeast(min_depth)) {
        return;
    }
    if (isScoreKey(key) && min_depth == FeatureTraceDepth::Verbose &&
        featureTraceDepth() != FeatureTraceDepth::Deep) {
        featureTraceThrottle("state/" + key, 2000, FeatureTraceDepth::Verbose, "state",
                             key + "=" + stateValueToString(new_value));
        return;
    }
    std::ostringstream msg;
    msg << "set " << key;
    if (old_value) {
        msg << " " << stateValueToString(*old_value) << "->" << stateValueToString(new_value);
    } else {
        msg << " ->" << stateValueToString(new_value);
    }
    featureTraceLogAt(min_depth, "state", msg.str());
}

void featureTraceRuntimeSnapshot(const state::AppState& state, const char* reason) {
    if (!featureTraceAtLeast(FeatureTraceDepth::Verbose)) {
        return;
    }
    static const char* kKeys[] = {
        "running",           "select_mode",           "target_hwnd",
        "left_click_active", "right_hold_active",     "flame_trigger_active",
        "reload_active",     "ammo_restock_active",   "nobullet_detected",
        "ammo_restock_sequence_busy", "call_merc_sequence_busy",
        "kill_counter_enabled",
    };
    std::ostringstream oss;
    oss << "snapshot reason=" << (reason ? reason : "?");
    for (const char* key : kKeys) {
        if (auto v = state.get(key)) {
            oss << " " << key << "=" << stateValueToString(*v);
        }
    }
    featureTraceLogAt(FeatureTraceDepth::Verbose, "runtime", oss.str());
}

void featureTraceThrottle(const std::string& throttle_key,
                          int interval_ms,
                          FeatureTraceDepth min_depth,
                          const char* category,
                          const std::string& message) {
    if (!featureTraceAtLeast(min_depth) || category == nullptr || message.empty()) {
        return;
    }
    static std::mutex throttle_mu;
    static std::unordered_map<std::string, uint64_t> last_ms;
    const uint64_t now = featureTraceMonoMs();
    {
        std::lock_guard<std::mutex> tlock(throttle_mu);
        if (interval_ms > 0) {
            const auto it = last_ms.find(throttle_key);
            if (it != last_ms.end() && now - it->second < static_cast<uint64_t>(interval_ms)) {
                return;
            }
            last_ms[throttle_key] = now;
        }
    }
    featureTraceLogAt(min_depth, category, message);
}

}  // namespace pipela::core
