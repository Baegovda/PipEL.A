find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)

qt_add_resources(PIPELA_APP_RESOURCES resources/theme.qrc resources/icons.qrc)

# AGENT: GLOB — new .cpp under app/ subdirs auto-pickup; no manual CMakeLists line per file.
file(GLOB_RECURSE PIPELA_APP_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/*/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/*/*/*.cpp"
)
list(FILTER PIPELA_APP_SOURCES EXCLUDE REGEX "/CMakeFiles/")

add_executable(Pipela
    ${PIPELA_APP_SOURCES}
    ${PIPELA_APP_RESOURCES}
)

target_include_directories(Pipela PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/shell
    ${CMAKE_CURRENT_SOURCE_DIR}/control
    ${CMAKE_CURRENT_SOURCE_DIR}/overlays
    ${CMAKE_CURRENT_SOURCE_DIR}/theme
    ${CMAKE_CURRENT_SOURCE_DIR}/widgets
    ${CMAKE_CURRENT_SOURCE_DIR}/dock
    ${CMAKE_CURRENT_SOURCE_DIR}/panels
    ${CMAKE_CURRENT_SOURCE_DIR}/panels/settings
    ${CMAKE_CURRENT_SOURCE_DIR}/input
    ${CMAKE_CURRENT_SOURCE_DIR}/../native/include
)

target_link_libraries(Pipela PRIVATE Qt6::Widgets pipela_core pipela_platform)

if(WIN32 AND TARGET pipela_input_hooks)
    target_link_libraries(Pipela PRIVATE pipela_input_hooks)
    add_dependencies(Pipela pipela_input_hooks)
    add_custom_command(TARGET Pipela POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:pipela_input_hooks>
            $<TARGET_FILE_DIR:Pipela>
        COMMENT "Copy pipela_input_hooks.dll next to Pipela.exe")
endif()

set_target_properties(Pipela PROPERTIES
    WIN32_EXECUTABLE ON
    OUTPUT_NAME "Pipela"
)

if(WIN32 AND TARGET cursor_hud_dcomp)
    target_link_libraries(Pipela PRIVATE cursor_hud_dcomp)
    add_dependencies(Pipela cursor_hud_dcomp)
    add_custom_command(TARGET Pipela POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:cursor_hud_dcomp>
            $<TARGET_FILE_DIR:Pipela>
        COMMENT "Copy cursor_hud_dcomp.dll next to Pipela.exe")
endif()

set(_pipela_assets_src "${CMAKE_CURRENT_SOURCE_DIR}/../../../assets")
if(EXISTS "${_pipela_assets_src}/splash.png")
    add_custom_command(TARGET Pipela POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:Pipela>/assets
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_pipela_assets_src}/splash.png"
            $<TARGET_FILE_DIR:Pipela>/assets/splash.png
        COMMENT "Copy assets/splash.png next to Pipela.exe")
endif()
if(EXISTS "${_pipela_assets_src}/vaultboy.png")
    add_custom_command(TARGET Pipela POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:Pipela>/assets
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_pipela_assets_src}/vaultboy.png"
            $<TARGET_FILE_DIR:Pipela>/assets/vaultboy.png
        COMMENT "Copy assets/vaultboy.png next to Pipela.exe")
endif()
set(_pipela_ico_src "${CMAKE_CURRENT_SOURCE_DIR}/../../../Pipela.ico")
if(EXISTS "${_pipela_ico_src}")
    add_custom_command(TARGET Pipela POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_pipela_ico_src}"
            $<TARGET_FILE_DIR:Pipela>/Pipela.ico
        COMMENT "Copy Pipela.ico next to Pipela.exe")
endif()

if(WIN32)
    target_link_libraries(Pipela PRIVATE shell32)
endif()

if(MSVC)
    target_compile_options(Pipela PRIVATE /utf-8)
endif()

include(${CMAKE_CURRENT_SOURCE_DIR}/../../cmake/PipelaQtDeploy.cmake)
pipela_deploy_qt_runtime(Pipela)

include(GNUInstallDirs)
install(TARGETS Pipela RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
