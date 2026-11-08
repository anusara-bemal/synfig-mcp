#ifndef MCP_BRIDGE_INIT_H
#define MCP_BRIDGE_INIT_H

namespace mcp_bridge {

/**
 * Check whether the MCP bridge is enabled (opt-in).
 * Enabled if SYNFIG_MCP_ENABLE=1 is set or if ~/.synfig/mcp_enabled is '1'.
 */
bool is_bridge_enabled();

/**
 * Check whether the MCP bridge is currently running.
 */
bool is_bridge_running();

/**
 * Toggle the MCP bridge on/off, updating ~/.synfig/mcp_enabled.
 */
bool toggle_bridge();

/**
 * Get the currently bound port, or -1 if stopped.
 */
int get_bound_port();

/**
 * Get the build commit SHA and version strings.
 */
const char* get_build_commit_sha();
const char* get_build_version();

/**
 * Start the MCP bridge server and event listeners.
 * Must be called from the GTK main thread during Studio initialization (e.g. App::init).
 */
bool start(int port = 19998);

/**
 * Stop the MCP bridge server and event listeners.
 * Must be called during Studio shutdown (e.g. App::on_shutdown).
 */
void stop();

} // namespace mcp_bridge

#endif // MCP_BRIDGE_INIT_H
