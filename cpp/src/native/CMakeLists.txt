# AGENT: native layer — DComp HUD wrapper + input hooks.
add_library(pipela_native_layer STATIC
    dcomp_hud_wrapper.cpp
)

target_include_directories(pipela_native_layer
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(WIN32)
    target_link_libraries(pipela_native_layer PUBLIC user32)
endif()

set(_HUD_SRC "${CMAKE_CURRENT_SOURCE_DIR}/../../../native/cursor_hud_dcomp")
if(EXISTS "${_HUD_SRC}/cursor_hud_dcomp.cpp")
    add_subdirectory("${_HUD_SRC}" "${CMAKE_CURRENT_BINARY_DIR}/cursor_hud_dcomp")
endif()

add_subdirectory(input_hooks)
