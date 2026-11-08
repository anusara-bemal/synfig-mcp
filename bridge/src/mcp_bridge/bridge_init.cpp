#include "bridge_init.h"
#include "auth.h"
#include "dispatcher.h"
#include "handlers.h"
#include "events.h"
#include "bridge_server.h"

#include <iostream>
#include <fstream>
#include <memory>
#include <cstdlib>
#include <cstring>

#ifndef BUILD_COMMIT_SHA
#define BUILD_COMMIT_SHA "dev"
#endif

#ifndef BUILD_VERSION
#define BUILD_VERSION "0.8.0-rc1"
#endif

namespace mcp_bridge {

static std::unique_ptr<BridgeServer> s_server;
static bool s_running = false;
static int s_bound_port = -1;

const char* get_build_commit_sha() {
    return BUILD_COMMIT_SHA;
}

const char* get_build_version() {
    return BUILD_VERSION;
}

bool is_bridge_enabled() {
    // 1. Explicit environment variable check (CI / automated runs)
    const char* env_enable = std::getenv("SYNFIG_MCP_ENABLE");
    if (env_enable && (*env_enable == '1' || *env_enable == 't' || *env_enable == 'T')) {
        return true;
    }
    const char* env_disable = std::getenv("SYNFIG_MCP_DISABLE");
    if (env_disable && (*env_disable == '1' || *env_disable == 't' || *env_disable == 'T')) {
        return false;
    }

    // 2. Persisted file ~/.synfig/mcp_enabled
    std::string cfg_path = get_config_file_path();
    std::ifstream ifs(cfg_path.c_str());
    if (ifs.is_open()) {
        std::string val;
        ifs >> val;
        ifs.close();
        if (val == "1" || val == "true" || val == "on" || val == "ON") {
            return true;
        }
    }

    // Default: OFF (opt-in)
    return false;
}

bool is_bridge_running() {
    return s_running;
}

int get_bound_port() {
    return s_bound_port;
}

bool toggle_bridge() {
    std::string cfg_path = get_config_file_path();
    if (s_running) {
        stop();
        std::ofstream ofs(cfg_path.c_str(), std::ios::out | std::ios::trunc);
        if (ofs.is_open()) {
            ofs << "0" << std::endl;
        }
        return false;
    } else {
        std::ofstream ofs(cfg_path.c_str(), std::ios::out | std::ios::trunc);
        if (ofs.is_open()) {
            ofs << "1" << std::endl;
        }
        return start();
    }
}

bool start(int port) {
    if (s_running) {
        return true;
    }

    if (!is_bridge_enabled()) {
        std::cout << "[mcp_bridge] Synfig MCP Bridge is OFF by default (opt-in). Set SYNFIG_MCP_ENABLE=1 or toggle in Studio settings." << std::endl;
        return false;
    }

    // Clean stale token files left by previous crashed instances
    clean_stale_tokens();

    // Check if port overridden by environment variable
    bool explicit_port = false;
    const char* env_port = std::getenv("SYNFIG_MCP_PORT");
    if (env_port && *env_port) {
        try {
            port = std::stoi(env_port);
            explicit_port = true;
        } catch (...) {}
    }

    std::cout << "[mcp_bridge] Initializing Synfig MCP Bridge on port " << port << " (commit: " << BUILD_COMMIT_SHA << ")..." << std::endl;

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
        remove_session_token_files();
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

    s_running = true;
    s_bound_port = bound_port;

    std::cout << "\n======================================================\n";
    std::cout << " [mcp_bridge] STATUS: ACTIVE & LISTENING on 127.0.0.1:" << bound_port << "\n";
    std::cout << " [mcp_bridge] Synfig MCP Bridge ready for AI connections.\n";
    std::cout << " [mcp_bridge] Version: " << BUILD_VERSION << " | Commit: " << BUILD_COMMIT_SHA << "\n";
    std::cout << "======================================================\n" << std::endl;

    return true;
}

void stop() {
    if (!s_running && !s_server) {
        return;
    }
    std::cout << "[mcp_bridge] Shutting down Synfig MCP Bridge..." << std::endl;

    teardown_event_listeners();

    if (s_server) {
        s_server->stop();
        s_server.reset();
    }

    cleanup_dispatcher();

    // Clean up session token files on shutdown
    remove_session_token_files();

    s_running = false;
    s_bound_port = -1;

    std::cout << "[mcp_bridge] Synfig MCP Bridge shutdown complete." << std::endl;
}

} // namespace mcp_bridge
