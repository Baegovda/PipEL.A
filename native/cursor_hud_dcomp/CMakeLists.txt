cmake_minimum_required(VERSION 3.20)
project(cursor_hud_dcomp LANGUAGES CXX)

get_filename_component(PIPELA_ASSET_ARROW_PNG
    "${CMAKE_CURRENT_LIST_DIR}/../../assets/arrow.png"
    REALPATH
)
get_filename_component(PIPELA_ASSET_GUNFIRE_PNG
    "${CMAKE_CURRENT_LIST_DIR}/../../assets/gunfire.png"
    REALPATH
)
get_filename_component(PIPELA_ASSET_CHOPPER_PNG
    "${CMAKE_CURRENT_LIST_DIR}/../../assets/chopper.png"
    REALPATH
)

# Generate a stable .rc that uses absolute PNG paths.
set(GENERATED_RC "${CMAKE_CURRENT_BINARY_DIR}/cursor_hud_dcomp.rc")
configure_file(
    "${CMAKE_CURRENT_LIST_DIR}/cursor_hud_dcomp.rc.in"
    "${GENERATED_RC}"
    @ONLY
)

add_library(cursor_hud_dcomp SHARED
    cursor_hud_dcomp.cpp
    "${GENERATED_RC}"
)

target_compile_features(cursor_hud_dcomp PRIVATE cxx_std_17)
target_compile_definitions(cursor_hud_dcomp PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(cursor_hud_dcomp PRIVATE /W4)

target_link_libraries(cursor_hud_dcomp
    PRIVATE
        user32
        gdi32
        ole32
        windowscodecs
        dcomp
        dxgi
        d2d1
        d3d11
)

set_target_properties(cursor_hud_dcomp PROPERTIES
    OUTPUT_NAME "cursor_hud_dcomp"
)

