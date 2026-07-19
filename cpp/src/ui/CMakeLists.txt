find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)

qt_add_resources(PIPELA_UI_RESOURCES resources/theme.qrc)

add_executable(Pipela
    app/main.cpp
    shell/application.cpp
    control/control_main_window.cpp
    theme/theme_tokens.cpp
    ${PIPELA_UI_RESOURCES}
)

target_include_directories(Pipela PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/shell
    ${CMAKE_CURRENT_SOURCE_DIR}/control
    ${CMAKE_CURRENT_SOURCE_DIR}/theme
    ${CMAKE_CURRENT_SOURCE_DIR}/../native/include
)

target_link_libraries(Pipela PRIVATE Qt6::Widgets pipela_core pipela_native_layer)

set_target_properties(Pipela PROPERTIES
    WIN32_EXECUTABLE ON
    OUTPUT_NAME "Pipela"
)

if(WIN32 AND TARGET cursor_hud_dcomp)
    target_link_libraries(Pipela PRIVATE cursor_hud_dcomp)
endif()

include(GNUInstallDirs)
install(TARGETS Pipela RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
