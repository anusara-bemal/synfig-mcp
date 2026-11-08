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
 * Retrieve path to MCP configuration toggle file:
 * - Windows: %USERPROFILE%\.synfig\mcp_enabled
 * - POSIX:   $HOME/.synfig/mcp_enabled
 */
std::string get_config_file_path();

/**
 * Remove stale token files from previous crashed instances.
 * Checks whether the process ID in mcp_token_<pid> is still active.
 */
void clean_stale_tokens();

/**
 * Remove session token files (both per-PID and default mcp_token if matching) on shutdown.
 */
void remove_session_token_files();

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
