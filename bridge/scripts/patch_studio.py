import os

# 1. Patch app.cpp
app_path = 'build_synfig/synfig_src/synfig-studio/src/gui/app.cpp'
with open(app_path, 'r', encoding='utf-8', newline='') as f:
    app_content = f.read()

target_inc = '#include <gui/localization.h>'
repl_inc = '#include <gui/localization.h>\r\n#include "mcp_bridge/bridge_init.h"'
assert target_inc in app_content, 'target_inc not found'
app_content = app_content.replace(target_inc, repl_inc, 1)

target_init = 'App::dock_info_ = dock_info;\r\n}'
repl_init = 'App::dock_info_ = dock_info;\r\n\tmcp_bridge::start();\r\n}'
assert target_init in app_content, 'target_init not found'
app_content = app_content.replace(target_init, repl_init, 1)

target_shut = 'App::on_shutdown()\r\n{\r\n\tshutdown_in_progress=true;'
repl_shut = 'App::on_shutdown()\r\n{\r\n\tmcp_bridge::stop();\r\n\tshutdown_in_progress=true;'
assert target_shut in app_content, 'target_shut not found'
app_content = app_content.replace(target_shut, repl_shut, 1)

with open(app_path, 'w', encoding='utf-8', newline='') as f:
    f.write(app_content)
print('Patched app.cpp successfully')

# 2. Patch CMakeLists.txt
cmake_path = 'build_synfig/synfig_src/synfig-studio/src/gui/CMakeLists.txt'
with open(cmake_path, 'r', encoding='utf-8', newline='') as f:
    cmake_content = f.read()

target_cmake1 = '\t\t"${CMAKE_CURRENT_LIST_DIR}/helpers.cpp"\r\n)'
repl_cmake1 = '\t\t"${CMAKE_CURRENT_LIST_DIR}/helpers.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/auth.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/types_serializer.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/dispatcher.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/events.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/handlers.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/bridge_server.cpp"\r\n' \
    '\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/bridge_init.cpp"\r\n)'
assert target_cmake1 in cmake_content, 'target_cmake1 not found'
cmake_content = cmake_content.replace(target_cmake1, repl_cmake1, 1)

target_cmake2 = 'if(TCMALLOC_LIBRARY)\r\n\ttarget_link_libraries(synfigstudio PRIVATE ${TCMALLOC_LIBRARY})\r\nendif()'
repl_cmake2 = target_cmake2 + '\r\n\r\nif (WIN32)\r\n\ttarget_link_libraries(synfigstudio PRIVATE ws2_32 advapi32)\r\nendif()'
assert target_cmake2 in cmake_content, 'target_cmake2 not found'
cmake_content = cmake_content.replace(target_cmake2, repl_cmake2, 1)

with open(cmake_path, 'w', encoding='utf-8', newline='') as f:
    f.write(cmake_content)
print('Patched CMakeLists.txt successfully')
