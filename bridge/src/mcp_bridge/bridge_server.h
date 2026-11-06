#ifndef MCP_BRIDGE_SERVER_H
#define MCP_BRIDGE_SERVER_H

#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <mutex>
#include <atomic>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET socket_t;
#define INVALID_SOCKET_VALUE INVALID_SOCKET
#define SOCKET_ERROR_VALUE SOCKET_ERROR
#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
typedef int socket_t;
#define INVALID_SOCKET_VALUE (-1)
#define SOCKET_ERROR_VALUE (-1)
#endif

namespace mcp_bridge {

const size_t MAX_MESSAGE_SIZE = 10 * 1024 * 1024; // 10 MB guard

class BridgeServer {
public:
    explicit BridgeServer(int port = 19998, const std::string& host = "127.0.0.1");
    ~BridgeServer();

    bool start();
    void stop();
    bool is_running() const { return m_running; }
    int get_port() const { return m_port; }

    /**
     * Broadcast a newline-delimited notification string to all connected clients.
     */
    void broadcast(const std::string& message);

private:
    void accept_loop();
    void client_loop(socket_t client_sock);
    void close_socket(socket_t sock);

    int m_port;
    std::string m_host;
    std::atomic<bool> m_running;
    socket_t m_listen_sock;
    std::thread m_accept_thread;

    std::mutex m_clients_mutex;
    std::vector<socket_t> m_client_sockets;
};

} // namespace mcp_bridge

#endif // MCP_BRIDGE_SERVER_H
