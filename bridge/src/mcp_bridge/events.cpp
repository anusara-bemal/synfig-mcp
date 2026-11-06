#include "events.h"
#include <iostream>
#include <mutex>

#ifndef MCP_BRIDGE_STANDALONE
#include <gui/app.h>
#include <gui/instance.h>
#include <gui/canvasview.h>
#include <synfigapp/canvasinterface.h>
#include <synfigapp/selectionmanager.h>
#endif

namespace mcp_bridge {

static std::mutex s_broadcast_mutex;
static EventBroadcastFunc s_broadcaster;

void set_event_broadcaster(EventBroadcastFunc func) {
    std::lock_guard<std::mutex> lock(s_broadcast_mutex);
    s_broadcaster = func;
}

void broadcast_notification(const std::string& method, const nlohmann::json& params) {
    nlohmann::json notif;
    notif["jsonrpc"] = "2.0";
    notif["method"] = method;
    notif["params"] = params;

    std::string line = notif.dump() + "\n";
    std::lock_guard<std::mutex> lock(s_broadcast_mutex);
    if (s_broadcaster) {
        s_broadcaster(line);
    }
}

#ifndef MCP_BRIDGE_STANDALONE
static std::vector<sigc::connection> s_connections;

static void on_time_changed(etl::handle<studio::Instance> instance) {
    if (!instance) return;
    etl::handle<synfigapp::CanvasInterface> ci = instance->find_canvas_interface(instance->get_canvas());
    if (!ci) return;

    synfig::Time t = ci->get_time();
    std::string doc_id = instance->get_file_name().empty() ? "doc_0" : instance->get_file_name();

    nlohmann::json params;
    params["doc_id"] = doc_id;
    params["time"] = {
        {"seconds", static_cast<double>(t)},
        {"string", t.get_string()}
    };

    broadcast_notification("event.time_changed", params);
}

static void on_instance_created(etl::handle<studio::Instance> instance) {
    if (!instance) return;
    etl::handle<synfigapp::CanvasInterface> ci = instance->find_canvas_interface(instance->get_canvas());
    if (ci) {
        sigc::connection c = ci->signal_time_changed().connect(
            sigc::bind(sigc::ptr_fun(&on_time_changed), instance)
        );
        s_connections.push_back(c);
    }
}

void setup_event_listeners() {
    // Listen for new instances opened/created
    s_connections.push_back(
        studio::App::signal_instance_created().connect(sigc::ptr_fun(&on_instance_created))
    );

    // Attach to existing open instances
    for (auto it = studio::App::instance_list.begin(); it != studio::App::instance_list.end(); ++it) {
        on_instance_created(*it);
    }
}

void teardown_event_listeners() {
    for (auto& c : s_connections) {
        c.disconnect();
    }
    s_connections.clear();
}
#else
void setup_event_listeners() {}
void teardown_event_listeners() {}
#endif

} // namespace mcp_bridge
