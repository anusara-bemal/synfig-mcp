with open('D:/Projects/Github/synfig mcp/build_synfig/synfig_src/synfig-studio/src/gui/CMakeLists.txt', 'r', newline='') as f:
    content = f.read()

target1 = '\t\t"${CMAKE_CURRENT_LIST_DIR}/helpers.cpp"\r\n)'
repl1 = '\t\t"${CMAKE_CURRENT_LIST_DIR}/helpers.cpp"\r\n\t\t"${CMAKE_CURRENT_LIST_DIR}/mcp_bridge/g0_test_hook.cpp"\r\n)'
assert target1 in content, f'target1 not found'
content = content.replace(target1, repl1, 1)

target2 = 'if(TCMALLOC_LIBRARY)\r\n\ttarget_link_libraries(synfigstudio PRIVATE ${TCMALLOC_LIBRARY})\r\nendif()'
repl2 = target2 + '\r\n\r\nif (WIN32)\r\n\ttarget_link_libraries(synfigstudio PRIVATE ws2_32)\r\nendif()'
assert target2 in content, f'target2 not found'
content = content.replace(target2, repl2, 1)

with open('D:/Projects/Github/synfig mcp/build_synfig/synfig_src/synfig-studio/src/gui/CMakeLists.txt', 'w', newline='') as f:
    f.write(content)
print('Successfully patched CMakeLists.txt')
