#include "g0_test_hook.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#endif

#include <glibmm/dispatcher.h>
#include <thread>
#include <atomic>
#include <iostream>
#include <string>

#include <gui/app.h>
#include <gui/canvasview.h>
#include <synfigapp/canvasinterface.h>
#include <synfigapp/action_system.h>

namespace mcp_bridge {

namespace {

std::thread s_socket_thread;
std::atomic<bool> s_running{false};
Glib::Dispatcher* s_dispatcher = nullptr;

#ifdef _WIN32
SOCKET s_server_socket = INVALID_SOCKET;
#else
int s_server_socket = -1;
#endif

void on_gtk_dispatch_trigger()
{
    std::cout << "\n======================================================\n";
    std::cout << "[MCP Bridge G0 Hook] Trigger received on GTK main thread!" << std::endl;

    etl::loose_handle<studio::CanvasView> canvas_view = studio::App::get_selected_canvas_view();
    if (!canvas_view) {
        std::cerr << "[MCP Bridge G0 Hook] ERROR: No active canvas view selected." << std::endl;
        std::cerr << "                      Please open or create a canvas in Synfig Studio first." << std::endl;
        std::cout << "======================================================\n" << std::endl;
        return;
    }

    etl::handle<synfigapp::CanvasInterface> canvas_interface = canvas_view->canvas_interface();
    if (!canvas_interface) {
        std::cerr << "[MCP Bridge G0 Hook] ERROR: Canvas interface is null." << std::endl;
        std::cout << "======================================================\n" << std::endl;
        return;
    }

    synfig::Canvas::Handle canvas = canvas_interface->get_canvas();
    if (!canvas) {
        std::cerr << "[MCP Bridge G0 Hook] ERROR: Canvas handle is null." << std::endl;
        std::cout << "======================================================\n" << std::endl;
        return;
    }

    std::cout << "[MCP Bridge G0 Hook] Current canvas name: " << canvas->get_name() << std::endl;
    std::cout << "[MCP Bridge G0 Hook] Adding 'circle' layer via CanvasInterface::add_layer_to()..." << std::endl;

    // CanvasInterface::add_layer_to creates the layer, sets defaults,
    // applies the Action::LayerAdd under a PassiveGrouper, and notifies the UI.
    synfig::Layer::Handle layer = canvas_interface->add_layer_to("circle", canvas, 0);

    if (layer) {
        std::cout << "[MCP Bridge G0 Hook] SUCCESS: Circle layer added! Description: '"
                  << layer->get_description() << "'" << std::endl;
        std::cout << "[MCP Bridge G0 Hook] The layer is now live on the canvas." << std::endl;
        std::cout << "[MCP Bridge G0 Hook] Press Ctrl+Z in Synfig Studio to test undoability." << std::endl;
    } else {
        std::cerr << "[MCP Bridge G0 Hook] ERROR: Failed to add circle layer." << std::endl;
    }
    std::cout << "======================================================\n" << std::endl;
}

void socket_worker_thread()
{
#ifdef _WIN32
    WSADATA wsa_data;
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        std::cerr << "[MCP Bridge G0 Hook] Failed to initialize Winsock." << std::endl;
        return;
    }
#endif

    s_server_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
#ifdef _WIN32
    if (s_server_socket == INVALID_SOCKET) {
        std::cerr << "[MCP Bridge G0 Hook] Failed to create socket: " << WSAGetLastError() << std::endl;
        WSACleanup();
        return;
    }
#else
    if (s_server_socket < 0) {
        std::cerr << "[MCP Bridge G0 Hook] Failed to create socket." << std::endl;
        return;
    }
#endif

    int opt = 1;
#ifdef _WIN32
    setsockopt(s_server_socket, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
#else
    setsockopt(s_server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    server_addr.sin_port = htons(19998);

    if (bind(s_server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) != 0) {
        std::cerr << "[MCP Bridge G0 Hook] Failed to bind to 127.0.0.1:19998" << std::endl;
#ifdef _WIN32
        closesocket(s_server_socket);
        WSACleanup();
#else
        close(s_server_socket);
#endif
        return;
    }

    if (listen(s_server_socket, 5) != 0) {
        std::cerr << "[MCP Bridge G0 Hook] Failed to listen on socket" << std::endl;
#ifdef _WIN32
        closesocket(s_server_socket);
        WSACleanup();
#else
        close(s_server_socket);
#endif
        return;
    }

    std::cout << "\n[MCP Bridge G0 Hook] Listening on 127.0.0.1:19998 for G0 test triggers...\n" << std::endl;

    while (s_running.load()) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(s_server_socket, &read_fds);

        timeval tv{1, 0}; // 1 second timeout
        int ret = select((int)s_server_socket + 1, &read_fds, nullptr, nullptr, &tv);

        if (ret > 0 && FD_ISSET(s_server_socket, &read_fds)) {
            sockaddr_in client_addr{};
#ifdef _WIN32
            int client_len = sizeof(client_addr);
            SOCKET client_socket = accept(s_server_socket, (struct sockaddr*)&client_addr, &client_len);
            if (client_socket != INVALID_SOCKET) {
                char buf[256];
                int bytes_read = recv(client_socket, buf, sizeof(buf) - 1, 0);
                if (bytes_read > 0) {
                    buf[bytes_read] = '\0';
                    std::cout << "[MCP Bridge G0 Hook] Received command over socket: " << buf << std::endl;
                    if (s_dispatcher) {
                        s_dispatcher->emit();
                    }
                    const char* resp = "OK: Dispatched create_circle to GTK main loop\n";
                    send(client_socket, resp, (int)strlen(resp), 0);
                }
                closesocket(client_socket);
            }
#else
            socklen_t client_len = sizeof(client_addr);
            int client_socket = accept(s_server_socket, (struct sockaddr*)&client_addr, &client_len);
            if (client_socket >= 0) {
                char buf[256];
                int bytes_read = recv(client_socket, buf, sizeof(buf) - 1, 0);
                if (bytes_read > 0) {
                    buf[bytes_read] = '\0';
                    std::cout << "[MCP Bridge G0 Hook] Received command over socket: " << buf << std::endl;
                    if (s_dispatcher) {
                        s_dispatcher->emit();
                    }
                    const char* resp = "OK: Dispatched create_circle to GTK main loop\n";
                    send(client_socket, resp, strlen(resp), 0);
                }
                close(client_socket);
            }
#endif
        }
    }

#ifdef _WIN32
    if (s_server_socket != INVALID_SOCKET) {
        closesocket(s_server_socket);
        s_server_socket = INVALID_SOCKET;
    }
    WSACleanup();
#else
    if (s_server_socket >= 0) {
        close(s_server_socket);
        s_server_socket = -1;
    }
#endif
    std::cout << "[MCP Bridge G0 Hook] Socket worker thread stopped." << std::endl;
}

} // anonymous namespace

void start_g0_test_hook()
{
    if (s_running.load()) return;

    // Create Glib::Dispatcher on GTK main thread
    if (!s_dispatcher) {
        s_dispatcher = new Glib::Dispatcher();
        s_dispatcher->connect(sigc::ptr_fun(&on_gtk_dispatch_trigger));
    }

    s_running.store(true);
    s_socket_thread = std::thread(socket_worker_thread);
    std::cout << "[MCP Bridge G0 Hook] Hook started." << std::endl;
}

void stop_g0_test_hook()
{
    if (!s_running.load()) return;

    s_running.store(false);
    if (s_socket_thread.joinable()) {
        s_socket_thread.join();
    }

    delete s_dispatcher;
    s_dispatcher = nullptr;
    std::cout << "[MCP Bridge G0 Hook] Hook stopped." << std::endl;
}

} // namespace mcp_bridge
