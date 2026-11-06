#ifndef MCP_BRIDGE_DISPATCHER_H
#define MCP_BRIDGE_DISPATCHER_H

#include <functional>
#include <memory>
#include <nlohmann/json.hpp>

namespace mcp_bridge {

/**
 * Initialize the cross-thread dispatcher on the GTK main thread.
 * Must be called from studio::App::init or the main GTK thread.
 */
void init_dispatcher();

/**
 * Cleanup dispatcher resources on shutdown.
 */
void cleanup_dispatcher();

/**
 * Check if the current calling thread is the main GUI thread.
 */
bool is_main_thread();

/**
 * Execute a callable on the GTK main thread and block until it completes or times out.
 * Returns the nlohmann::json result.
 */
nlohmann::json run_on_main_thread(std::function<nlohmann::json()> task, int timeout_seconds = 10);

} // namespace mcp_bridge

#endif // MCP_BRIDGE_DISPATCHER_H
