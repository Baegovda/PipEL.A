# AGENT: wraps existing native/cursor_hud_dcomp as Pipela CMake subproject.
cmake_minimum_required(VERSION 3.20)

set(_HUD_SRC "${CMAKE_CURRENT_SOURCE_DIR}/../../../native/cursor_hud_dcomp")
if(NOT EXISTS "${_HUD_SRC}/cursor_hud_dcomp.cpp")
    message(FATAL_ERROR "cursor_hud_dcomp sources not found at ${_HUD_SRC}")
endif()

add_subdirectory("${_HUD_SRC}" "${CMAKE_CURRENT_BINARY_DIR}/cursor_hud_dcomp")
add_subdirectory(input_hooks)
