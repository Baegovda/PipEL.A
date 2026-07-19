add_library(pipela_core STATIC
    version.cpp
    paths.cpp
    registry/parse.cpp
    registry/store.cpp
    state/app_state.cpp
    vision/template_match.cpp
    kill_counter/tier_data.cpp
    win32/dock_layout.cpp
    workers/worker_runtime.cpp
)

target_include_directories(pipela_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_definitions(pipela_core
    PUBLIC
        PIPELA_REPO_ROOT="${PIPELA_REPO_ROOT}"
)

if(PIPELA_ENABLE_OPENCV)
    find_package(OpenCV REQUIRED COMPONENTS core imgproc)
    target_link_libraries(pipela_core PUBLIC ${OpenCV_LIBS})
    target_compile_definitions(pipela_core PUBLIC PIPELA_HAS_OPENCV=1)
endif()

if(WIN32)
    target_link_libraries(pipela_core PUBLIC user32)
endif()
