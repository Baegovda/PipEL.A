find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(pipela_native module.cpp)

target_link_libraries(pipela_native PRIVATE pipela_core)

target_compile_definitions(pipela_native PRIVATE VERSION_INFO="${PROJECT_VERSION}")
