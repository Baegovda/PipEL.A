cmake_minimum_required(VERSION 3.20)
project(Pipela VERSION 0.10.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

include(PipelaOptions)
include(CPackConfig.cmake OPTIONAL)

option(PIPELA_BUILD_TESTS "Build C++ unit tests" ON)
option(PIPELA_BUILD_PYBIND "Build pipela_native pybind11 module" ON)
option(PIPELA_BUILD_QT_APP "Build Qt6 Pipela executable" ON)
option(PIPELA_BUILD_NATIVE_HUD "Build cursor_hud_dcomp DLL" ON)
option(PIPELA_ENABLE_OPENCV "Enable OpenCV template matching in core" OFF)

set(PIPELA_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")

add_subdirectory(src/core)

if(PIPELA_BUILD_NATIVE_HUD OR PIPELA_BUILD_QT_APP)
    add_subdirectory(src/native)
endif()

if(PIPELA_BUILD_PYBIND)
    add_subdirectory(bindings/pybind)
endif()

if(PIPELA_BUILD_QT_APP)
    add_subdirectory(src/app)
endif()

if(PIPELA_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

include(CPack)
