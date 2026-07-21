# AGENT: native layer — platform wrappers + input hooks + HUD DLL.
add_library(pipela_platform STATIC
    platform/dcomp_wrapper.cpp
)

target_include_directories(pipela_platform
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(WIN32)
    target_link_libraries(pipela_platform PUBLIC user32)
endif()

if(PIPELA_BUILD_NATIVE_HUD AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/hud_dcomp/cursor_hud_dcomp.cpp")
    add_subdirectory(hud_dcomp)
endif()

add_subdirectory(input_hooks)
