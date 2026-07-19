find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)

add_executable(Pipela
    app/main.cpp
    shell/application.cpp
    theme/theme_tokens.cpp
)

target_include_directories(Pipela PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/shell
    ${CMAKE_CURRENT_SOURCE_DIR}/theme
)

target_link_libraries(Pipela PRIVATE Qt6::Widgets pipela_core)

set_target_properties(Pipela PROPERTIES
    WIN32_EXECUTABLE ON
    OUTPUT_NAME "Pipela"
)

if(WIN32)
    if(TARGET cursor_hud_dcomp)
        target_link_libraries(Pipela PRIVATE cursor_hud_dcomp)
    endif()
endif()
