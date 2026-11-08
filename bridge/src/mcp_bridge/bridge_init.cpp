#include "bridge_init.h"
#include "auth.h"
#include "dispatcher.h"
#include "handlers.h"
#include "events.h"
#include "bridge_server.h"

#include <iostream>
#include <memory>
#include <cstdlib>

namespace mcp_bridge {

static std::unique_ptr<BridgeServer> s_server;

bool start(int port) {
    const char* env_disable = std::getenv("SYNFIG_MCP_DISABLE");
    if (env_disable && (*env_disable == '1' || *env_disable == 't' || *env_disable == 'T')) {
        std::cout << "[mcp_bridge] Synfig MCP Bridge disabled via SYNFIG_MCP_DISABLE" << std::endl;
        return false;
    }

    // Check if port overridden by environment variable
    bool explicit_port = false;
    const char* env_port = std::getenv("SYNFIG_MCP_PORT");
    if (env_port && *env_port) {
        try {
            port = std::stoi(env_port);
            explicit_port = true;
        } catch (...) {}
    }

    std::cout << "[mcp_bridge] Initializing Synfig MCP Bridge on port " << port << "..." << std::endl;

    // 1. Generate and save per-session token
    std::string token = generate_session_token();
    set_session_token(token);
    if (!write_token_file(token)) {
        std::cerr << "[mcp_bridge] Warning: Could not write token to token file" << std::endl;
    } else {
        std::cout << "[mcp_bridge] Session token saved to " << get_token_file_path() << std::endl;
    }

    // 2. Initialize GTK main thread dispatcher
    init_dispatcher();

    // 3. Create and start TCP server (with multi-instance auto-port probing)
    int max_attempts = explicit_port ? 1 : 10;
    int bound_port = -1;
    for (int i = 0; i < max_attempts; ++i) {
        int try_port = port + i;
        s_server.reset(new BridgeServer(try_port));
        if (s_server->start()) {
            bound_port = try_port;
            break;
        }
        s_server.reset();
    }

    if (bound_port < 0) {
        std::cerr << "[mcp_bridge] Error: Failed to start TCP server on port " << port << std::endl;
        return false;
    }

    // 4. Hook up event broadcasting
    set_event_broadcaster([](const std::string& notif_json) {
        if (s_server) {
            s_server->broadcast(notif_json);
        }
    });

    // 5. Connect Studio GTK signals
    setup_event_listeners();

    std::cout << "[mcp_bridge] Synfig MCP Bridge successfully started and ready for AI connections." << std::endl;
    return true;
}

void stop() {
    std::cout << "[mcp_bridge] Shutting down Synfig MCP Bridge..." << std::endl;

    teardown_event_listeners();

    if (s_server) {
        s_server->stop();
        s_server.reset();
    }

    cleanup_dispatcher();

    std::cout << "[mcp_bridge] Synfig MCP Bridge shutdown complete." << std::endl;
}

} // namespace mcp_bridge
