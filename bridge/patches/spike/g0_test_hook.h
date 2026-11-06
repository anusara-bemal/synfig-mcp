#ifndef __MCP_BRIDGE_G0_TEST_HOOK_H
#define __MCP_BRIDGE_G0_TEST_HOOK_H

namespace mcp_bridge {

/**
 * Initialize and start the Phase G0 feasibility test hook.
 * Starts a background socket listener on 127.0.0.1:19998.
 * When any command is received, dispatches to the GTK main loop
 * via Glib::Dispatcher to inject a circle layer into the active canvas.
 */
void start_g0_test_hook();

/**
 * Stop the test hook and shut down background socket thread.
 */
void stop_g0_test_hook();

} // namespace mcp_bridge

#endif // __MCP_BRIDGE_G0_TEST_HOOK_H
