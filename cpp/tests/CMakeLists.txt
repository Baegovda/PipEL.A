include(FetchContent)

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
)

target_link_libraries(pipela_golden_tests PRIVATE pipela_core Catch2::Catch2WithMain)

add_test(NAME pipela_golden COMMAND pipela_golden_tests)
