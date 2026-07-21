# AGENT: Copy vcpkg Qt6 plugins next to Pipela.exe (platforms/qwindows.dll required at runtime).
function(pipela_deploy_qt_runtime target)
    if(NOT WIN32 OR NOT TARGET ${target})
        return()
    endif()

    if(DEFINED VCPKG_INSTALLED_DIR AND DEFINED VCPKG_TARGET_TRIPLET)
        set(_qt_plugins "${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}/Qt6/plugins")
    else()
        set(_qt_plugins "${CMAKE_BINARY_DIR}/vcpkg_installed/x64-windows/Qt6/plugins")
    endif()

    if(NOT EXISTS "${_qt_plugins}/platforms/qwindows.dll")
        message(WARNING "pipela_deploy_qt_runtime: qwindows.dll not found at ${_qt_plugins}")
        return()
    endif()

    set(_app_dir "$<TARGET_FILE_DIR:${target}>")
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "${_app_dir}/platforms"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${_app_dir}/styles"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${_app_dir}/imageformats"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_qt_plugins}/platforms/qwindows.dll"
            "${_app_dir}/platforms/"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_qt_plugins}/styles/qmodernwindowsstyle.dll"
            "${_app_dir}/styles/"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_qt_plugins}/imageformats/qgif.dll"
            "${_app_dir}/imageformats/"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_qt_plugins}/imageformats/qico.dll"
            "${_app_dir}/imageformats/"
        COMMENT "Deploy Qt plugins next to ${target}")

    if(EXISTS "${_qt_plugins}/imageformats/qpng.dll")
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${_qt_plugins}/imageformats/qpng.dll"
                "${_app_dir}/imageformats/"
            COMMENT "Deploy qpng.dll next to ${target}")
    endif()
endfunction()
