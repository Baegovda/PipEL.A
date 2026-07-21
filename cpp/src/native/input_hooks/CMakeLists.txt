# AGENT: low-level input hook DLL placeholder (Phase 3 — LL mouse/keyboard).
cmake_minimum_required(VERSION 3.20)

add_library(pipela_input_hooks SHARED input_hooks.cpp)

target_compile_features(pipela_input_hooks PRIVATE cxx_std_17)
target_include_directories(pipela_input_hooks
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

target_compile_definitions(pipela_input_hooks PRIVATE
    PIPELA_INPUT_HOOKS_EXPORTS
    UNICODE
    _UNICODE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
)
target_link_libraries(pipela_input_hooks PRIVATE user32)

set_target_properties(pipela_input_hooks PROPERTIES OUTPUT_NAME "pipela_input_hooks")
