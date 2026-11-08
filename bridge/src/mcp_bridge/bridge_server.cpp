#include "bridge_server.h"
#include "handlers.h"
#include "events.h"

#include <iostream>
#include <algorithm>
#include <cstring>

namespace mcp_bridge {

BridgeServer::BridgeServer(int port, const std::string& host)
    : m_port(port)
    , m_host(host)
    , m_running(false)
    , m_listen_sock(INVALID_SOCKET_VALUE) {
}

BridgeServer::~BridgeServer() {
    stop();
}

void BridgeServer::close_socket(socket_t sock) {
    if (sock != INVALID_SOCKET_VALUE) {
#ifdef _WIN32
        closesocket(sock);
#else
        close(sock);
#endif
    }
}

bool BridgeServer::start() {
    if (m_running) {
        return true;
    }

#ifdef _WIN32
    WSADATA wsa_data;
    int wsa_err = WSAStartup(MAKEWORD(2, 2), &wsa_data);
    if (wsa_err != 0) {
        std::cerr << "[mcp_bridge] WSAStartup failed: " << wsa_err << std::endl;
        return false;
    }
#endif

    m_listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (m_listen_sock == INVALID_SOCKET_VALUE) {
        std::cerr << "[mcp_bridge] Failed to create socket" << std::endl;
        return false;
    }

    int opt = 1;
#ifdef _WIN32
    setsockopt(m_listen_sock, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, (const char*)&opt, sizeof(opt));
#else
    setsockopt(m_listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif

    sockaddr_in server_addr;
    std::memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(m_port);
    server_addr.sin_addr.s_addr = inet_addr(m_host.c_str());

    if (bind(m_listen_sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR_VALUE) {
        std::cerr << "[mcp_bridge] Bind failed on " << m_host << ":" << m_port << std::endl;
        close_socket(m_listen_sock);
        m_listen_sock = INVALID_SOCKET_VALUE;
        return false;
    }

    if (listen(m_listen_sock, 5) == SOCKET_ERROR_VALUE) {
        std::cerr << "[mcp_bridge] Listen failed on port " << m_port << std::endl;
        close_socket(m_listen_sock);
        m_listen_sock = INVALID_SOCKET_VALUE;
        return false;
    }

    m_running = true;
    std::cout << "[mcp_bridge] TCP server listening on " << m_host << ":" << m_port << std::endl;

    m_accept_thread = std::thread(&BridgeServer::accept_loop, this);
    return true;
}

void BridgeServer::stop() {
    if (!m_running) {
        return;
    }
    m_running = false;

    if (m_listen_sock != INVALID_SOCKET_VALUE) {
        close_socket(m_listen_sock);
        m_listen_sock = INVALID_SOCKET_VALUE;
    }

    {
        std::lock_guard<std::mutex> lock(m_clients_mutex);
        for (socket_t sock : m_client_sockets) {
            close_socket(sock);
        }
        m_client_sockets.clear();
    }

    if (m_accept_thread.joinable()) {
        m_accept_thread.join();
    }

#ifdef _WIN32
    WSACleanup();
#endif
    std::cout << "[mcp_bridge] TCP server stopped" << std::endl;
}

void BridgeServer::broadcast(const std::string& message) {
    std::lock_guard<std::mutex> lock(m_clients_mutex);
    for (socket_t sock : m_client_sockets) {
        send(sock, message.c_str(), static_cast<int>(message.length()), 0);
    }
}

void BridgeServer::accept_loop() {
    while (m_running) {
        sockaddr_in client_addr;
#ifdef _WIN32
        int addr_len = sizeof(client_addr);
#else
        socklen_t addr_len = sizeof(client_addr);
#endif
        socket_t client_sock = accept(m_listen_sock, (struct sockaddr*)&client_addr, &addr_len);
        if (client_sock == INVALID_SOCKET_VALUE) {
            if (!m_running) break;
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(m_clients_mutex);
            m_client_sockets.push_back(client_sock);
        }

        std::thread([this, client_sock]() {
            this->client_loop(client_sock);
        }).detach();
    }
}

void BridgeServer::client_loop(socket_t client_sock) {
    bool authenticated = false;
    std::string buffer;
    char chunk[4096];

    while (m_running) {
        int bytes_read = recv(client_sock, chunk, sizeof(chunk), 0);
        if (bytes_read <= 0) {
            break;
        }

        buffer.append(chunk, bytes_read);

        if (buffer.length() > MAX_MESSAGE_SIZE) {
            nlohmann::json err = {
                {"jsonrpc", "2.0"},
                {"id", nullptr},
                {"error", {
                    {"code", -32600},
                    {"message", "Message payload exceeds 10MB limit"}
                }}
            };
            std::string err_str = err.dump() + "\n";
            send(client_sock, err_str.c_str(), static_cast<int>(err_str.length()), 0);
            break;
        }

        size_t newline_pos = std::string::npos;
        while ((newline_pos = buffer.find('\n')) != std::string::npos) {
            std::string line = buffer.substr(0, newline_pos);
            buffer.erase(0, newline_pos + 1);

            // Trim trailing \r if present
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            if (line.empty()) {
                continue;
            }

            nlohmann::json req;
            nlohmann::json res;
            try {
                req = nlohmann::json::parse(line);
                res = dispatch_request(req, authenticated);
            } catch (const std::exception& e) {
                res["jsonrpc"] = "2.0";
                res["id"] = nullptr;
                res["error"] = {
                    {"code", -32700},
                    {"message", std::string("Parse error: ") + e.what()}
                };
            }

            std::string res_str = res.dump() + "\n";
            send(client_sock, res_str.c_str(), static_cast<int>(res_str.length()), 0);
        }
    }

    {
        std::lock_guard<std::mutex> lock(m_clients_mutex);
        m_client_sockets.erase(
            std::remove(m_client_sockets.begin(), m_client_sockets.end(), client_sock),
            m_client_sockets.end()
        );
    }
    close_socket(client_sock);
}

} // namespace mcp_bridge
