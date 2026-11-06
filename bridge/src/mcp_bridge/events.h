#ifndef MCP_BRIDGE_EVENTS_H
#define MCP_BRIDGE_EVENTS_H

#include <string>
#include <vector>
#include <functional>
#include <nlohmann/json.hpp>

namespace mcp_bridge {

/**
 * Callback function to broadcast JSON-RPC notification string to all connected clients.
 */
typedef std::function<void(const std::string&)> EventBroadcastFunc;

/**
 * Register broadcast callback used by event listeners.
 */
void set_event_broadcaster(EventBroadcastFunc func);

/**
 * Emit a JSON-RPC notification.
 */
void broadcast_notification(const std::string& method, const nlohmann::json& params);

/**
 * Attach event listeners to Studio App and open instances.
 * Must be called on GTK main thread.
 */
void setup_event_listeners();

/**
 * Disconnect all event listeners.
 */
void teardown_event_listeners();

} // namespace mcp_bridge

#endif // MCP_BRIDGE_EVENTS_H
