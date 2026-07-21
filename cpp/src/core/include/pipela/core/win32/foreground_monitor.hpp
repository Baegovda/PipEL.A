#pragma once

#include <cstdint>
#include <functional>

namespace pipela::core::win32 {

// AGENT: EVENT_SYSTEM_FOREGROUND — re-stack title strip when game/Pipela focus changes.
class ForegroundWinEventMonitor {
public:
    using Callback = std::function<void(std::intptr_t fg_hwnd)>;

    ForegroundWinEventMonitor() = default;
    ~ForegroundWinEventMonitor();

    ForegroundWinEventMonitor(const ForegroundWinEventMonitor&) = delete;
    ForegroundWinEventMonitor& operator=(const ForegroundWinEventMonitor&) = delete;

    bool start(Callback cb);
    void stop();

private:
    Callback cb_;
    void* hook_{nullptr};
};

}  // namespace pipela::core::win32
