include(FetchContent)

find_package(Qt6 REQUIRED COMPONENTS Gui)

if(NOT TARGET Catch2::Catch2WithMain)
    FetchContent_Declare(
        Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG v3.5.4
    )
    FetchContent_MakeAvailable(Catch2)
endif()

add_executable(pipela_golden_tests
    golden/registry_parse_test.cpp
    golden/dock_layout_test.cpp
    golden/tier_schema_test.cpp
    golden/snapshot_vision_test.cpp
    golden/worker_state_test.cpp
    golden/registry_roundtrip_test.cpp
    golden/update_manifest_test.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/app/dock/side_dock_layout.cpp
)

target_include_directories(pipela_golden_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/app
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/app/dock
)

target_link_libraries(pipela_golden_tests PRIVATE pipela_core Catch2::Catch2WithMain Qt6::Gui)
if(MSVC)
    target_compile_options(pipela_golden_tests PRIVATE /EHsc)
endif()

add_test(NAME pipela_golden COMMAND pipela_golden_tests)
