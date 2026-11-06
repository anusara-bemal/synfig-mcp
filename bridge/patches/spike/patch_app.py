with open('D:/Projects/Github/synfig mcp/build_synfig/synfig_src/synfig-studio/src/gui/app.cpp', 'r', newline='') as f:
    content = f.read()

# Add include
include_target = '#include <gui/localization.h>'
include_repl = '#include <gui/localization.h>\r\n#include "mcp_bridge/g0_test_hook.h"'
if include_repl not in content:
    assert include_target in content, 'include_target not found'
    content = content.replace(include_target, include_repl, 1)

# In App::init at end:
init_target = 'App::dock_info_ = dock_info;\r\n}'
init_repl = 'App::dock_info_ = dock_info;\r\n\tmcp_bridge::start_g0_test_hook();\r\n}'
if init_repl not in content:
    assert init_target in content, 'init_target not found'
    content = content.replace(init_target, init_repl, 1)

# In App::on_shutdown:
shutdown_target = 'App::on_shutdown()\r\n{\r\n\tshutdown_in_progress=true;'
shutdown_repl = 'App::on_shutdown()\r\n{\r\n\tmcp_bridge::stop_g0_test_hook();\r\n\tshutdown_in_progress=true;'
if shutdown_repl not in content:
    assert shutdown_target in content, 'shutdown_target not found'
    content = content.replace(shutdown_target, shutdown_repl, 1)

with open('D:/Projects/Github/synfig mcp/build_synfig/synfig_src/synfig-studio/src/gui/app.cpp', 'w', newline='') as f:
    f.write(content)

print('Successfully patched app.cpp')
