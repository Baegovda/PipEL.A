#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

extern "C" __declspec(dllexport) int pipela_input_hooks_init() { return 1; }

extern "C" __declspec(dllexport) void pipela_input_hooks_shutdown() {}

BOOL APIENTRY DllMain(HMODULE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_DETACH) {
        pipela_input_hooks_shutdown();
    }
    return TRUE;
}
