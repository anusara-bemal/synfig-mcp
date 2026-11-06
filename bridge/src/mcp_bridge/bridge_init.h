#ifndef MCP_BRIDGE_INIT_H
#define MCP_BRIDGE_INIT_H

namespace mcp_bridge {

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
