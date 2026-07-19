add_library(pipela_core STATIC
    version.cpp
    paths.cpp
    registry/parse.cpp
    registry/store.cpp
    state/app_state.cpp
    vision/template_match.cpp
    kill_counter/tier_data.cpp
    kill_counter/tier_data.generated.cpp
    win32/dock_layout.cpp
    win32/game_windows.cpp
    workers/worker_runtime.cpp
)

target_include_directories(pipela_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/kill_counter
)

target_compile_definitions(pipela_core
    PUBLIC
        PIPELA_REPO_ROOT="${PIPELA_REPO_ROOT}"
)

include(FetchContent)
FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(nlohmann_json)
target_link_libraries(pipela_core PUBLIC nlohmann_json::nlohmann_json)

if(PIPELA_ENABLE_OPENCV)
    find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs)
    target_link_libraries(pipela_core PUBLIC ${OpenCV_LIBS})
    target_include_directories(pipela_core PUBLIC ${OpenCV_INCLUDE_DIRS})
    target_compile_definitions(pipela_core PUBLIC PIPELA_HAS_OPENCV=1)
endif()

if(WIN32)
    target_link_libraries(pipela_core PUBLIC user32 gdi32)
endif()
