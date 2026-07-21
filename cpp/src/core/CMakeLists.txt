add_library(pipela_core STATIC
    version.cpp
    update/manifest.cpp
    update/installer.cpp
    feature_trace_log.cpp
    workers/worker_loop_trace.cpp
    input/left_click_controller.cpp
    paths.cpp
    input/keymap.cpp
    registry/parse.cpp
    registry/store.cpp
    registry/snapshot.cpp
    registry/json_region.cpp
    reload/sequence.cpp
    reload/idle_secondary.cpp
    state/app_state.cpp
    vision/template_match.cpp
    vision/roi.cpp
    vision/capture.cpp
    vision/registry_image_loader.cpp
    template/region_dispatch.cpp
    template/capture_catalog.cpp
    template/path_resolve.cpp
    template/apply.cpp
    template/last_match_cache.cpp
    settings_sequence_scroll.cpp
    vision/ocr_tesseract.cpp
    kill_counter/tier_data.cpp
    kill_counter/tier_data.generated.cpp
    kill_counter/tier_colors.cpp
    kill_counter/screen_probe.cpp
    kill_counter/stats_store.cpp
    kill_counter/goal_display.cpp
    kill_counter/session.cpp
    win32/game_windows.cpp
    win32/window_ops.cpp
    win32/foreground_monitor.cpp
    win32/clip_cursor.cpp
    win32/input_synth.cpp
    workers/worker_context.cpp
    workers/worker_loops.cpp
    workers/worker_runtime.cpp
    workers/ride_worker.cpp
    workers/hp_refill_worker.cpp
    workers/reload_worker.cpp
    workers/ammo_restock_worker.cpp
    workers/call_merc_worker.cpp
    workers/flame_trigger_worker.cpp
    workers/start_game_launcher_worker.cpp
    workers/kill_counter_worker.cpp
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

find_package(Tesseract QUIET)
if(Tesseract_FOUND)
    target_link_libraries(pipela_core PUBLIC Tesseract::libtesseract)
    target_compile_definitions(pipela_core PUBLIC PIPELA_HAS_TESSERACT=1)
endif()

if(WIN32)
    target_link_libraries(pipela_core PUBLIC user32 gdi32 crypt32 shell32 winhttp)
endif()

if(MSVC)
    target_compile_options(pipela_core PRIVATE /utf-8)
endif()
