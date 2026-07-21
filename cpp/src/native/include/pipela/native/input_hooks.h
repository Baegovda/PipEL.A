#pragma once

#include <stdint.h>

#ifdef _WIN32
#ifdef PIPELA_INPUT_HOOKS_EXPORTS
#define PIPELA_INPUT_HOOKS_API __declspec(dllexport)
#else
#define PIPELA_INPUT_HOOKS_API __declspec(dllimport)
#endif
#else
#define PIPELA_INPUT_HOOKS_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*PipelaMouseHookCallback)(int x_phys, int y_phys, int button, int pressed,
                                        unsigned int hook_flags, void* user_data);
typedef void (*PipelaKeyboardHookCallback)(unsigned int vk, int is_down, void* user_data);

PIPELA_INPUT_HOOKS_API int pipela_input_hooks_init(void);
PIPELA_INPUT_HOOKS_API void pipela_input_hooks_shutdown(void);

PIPELA_INPUT_HOOKS_API int pipela_input_hooks_start(void);
PIPELA_INPUT_HOOKS_API void pipela_input_hooks_stop(void);

PIPELA_INPUT_HOOKS_API void pipela_input_hooks_set_mouse_callback(PipelaMouseHookCallback cb,
                                                                  void* user_data);
PIPELA_INPUT_HOOKS_API void pipela_input_hooks_set_keyboard_callback(
    PipelaKeyboardHookCallback cb, void* user_data);

PIPELA_INPUT_HOOKS_API int pipela_input_hooks_is_running(void);

#ifdef __cplusplus
}
#endif
