set(PYBIND11_FINDPYTHON ON)
find_package(Python 3.10 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Gui)

pybind11_add_module(pipela_native module.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../../src/app/dock/side_dock_layout.cpp
)

target_include_directories(pipela_native PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../src/app
    ${CMAKE_CURRENT_SOURCE_DIR}/../../src/app/dock
)

target_link_libraries(pipela_native PRIVATE pipela_core Qt6::Gui)

target_compile_definitions(pipela_native PRIVATE VERSION_INFO="${PROJECT_VERSION}")
