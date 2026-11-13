#ifndef MCP_BRIDGE_HANDLERS_H
#define MCP_BRIDGE_HANDLERS_H

#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace mcp_bridge {

/**
 * Expected protocol version and capabilities.
 */
extern const char* PROTOCOL_VERSION;
extern const char* STUDIO_VERSION;

/**
 * Configure session credentials.
 */
void set_session_token(const std::string& token);
std::string get_session_token();

/**
 * Dispatch an incoming JSON-RPC 2.0 request.
 * Marshals document operations through dispatcher to GTK main thread.
 * Returns the complete JSON-RPC response object.
 */
nlohmann::json dispatch_request(const nlohmann::json& req, bool& inout_authenticated);

} // namespace mcp_bridge

#endif // MCP_BRIDGE_HANDLERS_H
