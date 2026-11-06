#ifndef MCP_BRIDGE_AUTH_H
#define MCP_BRIDGE_AUTH_H

#include <string>

namespace mcp_bridge {

/**
 * Generate a cryptographically random 32-character hex token.
 */
std::string generate_session_token();

/**
 * Retrieve the path to the user-only token file:
 * - Windows: %USERPROFILE%\.synfig\mcp_token
 * - POSIX:   $HOME/.synfig/mcp_token
 */
std::string get_token_file_path();

/**
 * Write token to the token file with restricted permissions (0600 on POSIX).
 * Ensures the parent directory exists.
 */
bool write_token_file(const std::string& token);

/**
 * Read token from the token file.
 */
std::string read_token_file();

/**
 * Validate received client token against expected session token.
 */
bool validate_token(const std::string& received_token, const std::string& expected_token);

} // namespace mcp_bridge

#endif // MCP_BRIDGE_AUTH_H
