// AGENT: WH_MOUSE_LL + WH_KEYBOARD_LL — dedicated hook thread (no Qt from callbacks).
#ifndef NOMINMAX
#define NOMINMAX
#endif
#define PIPELA_INPUT_HOOKS_EXPORTS
#include "pipela/native/input_hooks.h"

#include <atomic>
#include <mutex>
#include <thread>

#include <windows.h>

namespace {

constexpr int kWhMouseLl = 14;
constexpr int kWhKeyboardLl = 13;
constexpr UINT kWmMouseMove = 0x0200;
constexpr UINT kWmLButtonDown = 0x0201;
constexpr UINT kWmLButtonUp = 0x0202;
constexpr UINT kWmRButtonDown = 0x0204;
constexpr UINT kWmRButtonUp = 0x0205;
constexpr UINT kWmMButtonDown = 0x0207;
constexpr UINT kWmMButtonUp = 0x0208;
constexpr UINT kWmKeyDown = 0x0100;
constexpr UINT kWmKeyUp = 0x0101;
constexpr UINT kWmSysKeyDown = 0x0104;
constexpr UINT kWmSysKeyUp = 0x0105;
constexpr UINT kWmQuit = 0x0012;

struct HookState {
    std::mutex mu;
    std::thread thread;
    DWORD thread_id{0};
    HHOOK mouse_hook{nullptr};
    HHOOK keyboard_hook{nullptr};
    std::atomic<bool> running{false};
    PipelaMouseHookCallback mouse_cb{nullptr};
    void* mouse_user{nullptr};
    PipelaKeyboardHookCallback keyboard_cb{nullptr};
    void* keyboard_user{nullptr};
};

HookState g_state;

LRESULT CALLBACK mouse_proc(int n_code, WPARAM w_param, LPARAM l_param) {
    if (n_code >= 0) {
        const auto* ms = reinterpret_cast<const MSLLHOOKSTRUCT*>(l_param);
        PipelaMouseHookCallback cb = nullptr;
        void* user = nullptr;
        {
            std::lock_guard<std::mutex> lock(g_state.mu);
            cb = g_state.mouse_cb;
            user = g_state.mouse_user;
        }
        if (cb != nullptr && ms != nullptr) {
            const UINT wp = static_cast<UINT>(w_param);
            int button = 0;
            int pressed = -1;
            if (wp == kWmMouseMove) {
                button = 0;
                pressed = 0;
            } else if (wp == kWmLButtonDown) {
                button = 1;
                pressed = 1;
            } else if (wp == kWmLButtonUp) {
                button = 1;
                pressed = 0;
            } else if (wp == kWmRButtonDown) {
                button = 2;
                pressed = 1;
            } else if (wp == kWmRButtonUp) {
                button = 2;
                pressed = 0;
            } else if (wp == kWmMButtonDown) {
                button = 3;
                pressed = 1;
            } else if (wp == kWmMButtonUp) {
                button = 3;
                pressed = 0;
            }
            if (pressed >= 0) {
                const unsigned int hook_flags = ms != nullptr ? static_cast<unsigned int>(ms->flags) : 0u;
                cb(static_cast<int>(ms->pt.x), static_cast<int>(ms->pt.y), button, pressed,
                   hook_flags, user);
            }
        }
    }
    return CallNextHookEx(nullptr, n_code, w_param, l_param);
}

LRESULT CALLBACK keyboard_proc(int n_code, WPARAM w_param, LPARAM l_param) {
    if (n_code >= 0) {
        const auto* kb = reinterpret_cast<const KBDLLHOOKSTRUCT*>(l_param);
        PipelaKeyboardHookCallback cb = nullptr;
        void* user = nullptr;
        {
            std::lock_guard<std::mutex> lock(g_state.mu);
            cb = g_state.keyboard_cb;
            user = g_state.keyboard_user;
        }
        if (cb != nullptr && kb != nullptr) {
            const UINT wp = static_cast<UINT>(w_param);
            int is_down = -1;
            if (wp == kWmKeyDown || wp == kWmSysKeyDown) {
                is_down = 1;
            } else if (wp == kWmKeyUp || wp == kWmSysKeyUp) {
                is_down = 0;
            }
            if (is_down >= 0) {
                cb(kb->vkCode, is_down, user);
            }
        }
    }
    return CallNextHookEx(nullptr, n_code, w_param, l_param);
}

void hook_thread_main() {
    g_state.thread_id = GetCurrentThreadId();
    HHOOK mh = SetWindowsHookExW(kWhMouseLl, mouse_proc, GetModuleHandleW(nullptr), 0);
    HHOOK kh = SetWindowsHookExW(kWhKeyboardLl, keyboard_proc, GetModuleHandleW(nullptr), 0);
    {
        std::lock_guard<std::mutex> lock(g_state.mu);
        g_state.mouse_hook = mh;
        g_state.keyboard_hook = kh;
    }

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    HHOOK mh2 = nullptr;
    HHOOK kh2 = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_state.mu);
        mh2 = g_state.mouse_hook;
        kh2 = g_state.keyboard_hook;
        g_state.mouse_hook = nullptr;
        g_state.keyboard_hook = nullptr;
    }
    if (mh2 != nullptr) {
        UnhookWindowsHookEx(mh2);
    }
    if (kh2 != nullptr) {
        UnhookWindowsHookEx(kh2);
    }
}

}  // namespace

extern "C" {

int pipela_input_hooks_init(void) { return 1; }

void pipela_input_hooks_shutdown(void) { pipela_input_hooks_stop(); }

int pipela_input_hooks_start(void) {
    if (g_state.running.load()) {
        return 1;
    }
    g_state.running.store(true);
    g_state.thread = std::thread(hook_thread_main);
    return 1;
}

void pipela_input_hooks_stop(void) {
    if (!g_state.running.exchange(false)) {
        return;
    }
    const DWORD tid = g_state.thread_id;
    if (tid != 0) {
        PostThreadMessageW(tid, kWmQuit, 0, 0);
    }
    if (g_state.thread.joinable()) {
        g_state.thread.join();
    }
    g_state.thread_id = 0;
}

void pipela_input_hooks_set_mouse_callback(PipelaMouseHookCallback cb, void* user_data) {
    std::lock_guard<std::mutex> lock(g_state.mu);
    g_state.mouse_cb = cb;
    g_state.mouse_user = user_data;
}

void pipela_input_hooks_set_keyboard_callback(PipelaKeyboardHookCallback cb, void* user_data) {
    std::lock_guard<std::mutex> lock(g_state.mu);
    g_state.keyboard_cb = cb;
    g_state.keyboard_user = user_data;
}

int pipela_input_hooks_is_running(void) { return g_state.running.load() ? 1 : 0; }

}  // extern "C"

BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_DETACH) {
        pipela_input_hooks_shutdown();
    }
    return TRUE;
}
