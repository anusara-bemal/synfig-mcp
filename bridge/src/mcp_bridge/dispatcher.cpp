#include "dispatcher.h"

#include <iostream>
#include <mutex>
#include <queue>
#include <future>
#include <thread>
#include <chrono>

#ifndef MCP_BRIDGE_STANDALONE
#include <glibmm/dispatcher.h>
#endif

namespace mcp_bridge {

struct TaskItem {
    std::function<nlohmann::json()> func;
    std::shared_ptr<std::promise<nlohmann::json>> promise;
};

static std::mutex s_queue_mutex;
static std::queue<TaskItem> s_task_queue;
static std::thread::id s_main_thread_id;
static bool s_initialized = false;

#ifndef MCP_BRIDGE_STANDALONE
static std::unique_ptr<Glib::Dispatcher> s_dispatcher;

static void on_dispatch_triggered() {
    while (true) {
        TaskItem item;
        {
            std::lock_guard<std::mutex> lock(s_queue_mutex);
            if (s_task_queue.empty()) {
                break;
            }
            item = std::move(s_task_queue.front());
            s_task_queue.pop();
        }

        if (item.func && item.promise) {
            try {
                nlohmann::json res = item.func();
                item.promise->set_value(res);
            } catch (const std::exception& e) {
                try {
                    item.promise->set_exception(std::current_exception());
                } catch (...) {}
            } catch (...) {
                try {
                    item.promise->set_exception(std::make_exception_ptr(std::runtime_error("Unknown exception on main thread")));
                } catch (...) {}
            }
        }
    }
}
#endif

void init_dispatcher() {
    s_main_thread_id = std::this_thread::get_id();
#ifndef MCP_BRIDGE_STANDALONE
    s_dispatcher.reset(new Glib::Dispatcher());
    s_dispatcher->connect(sigc::ptr_fun(&on_dispatch_triggered));
#endif
    s_initialized = true;
}

void cleanup_dispatcher() {
#ifndef MCP_BRIDGE_STANDALONE
    s_dispatcher.reset();
#endif
    s_initialized = false;
}

bool is_main_thread() {
    return s_initialized && (std::this_thread::get_id() == s_main_thread_id);
}

nlohmann::json run_on_main_thread(std::function<nlohmann::json()> task, int timeout_seconds) {
    if (!s_initialized || is_main_thread()) {
        return task();
    }

#ifndef MCP_BRIDGE_STANDALONE
    auto promise = std::make_shared<std::promise<nlohmann::json>>();
    auto future = promise->get_future();

    {
        std::lock_guard<std::mutex> lock(s_queue_mutex);
        s_task_queue.push(TaskItem{std::move(task), promise});
    }

    if (s_dispatcher) {
        s_dispatcher->emit();
    } else {
        throw std::runtime_error("Dispatcher not available");
    }

    if (future.wait_for(std::chrono::seconds(timeout_seconds)) == std::future_status::timeout) {
        throw std::runtime_error("Request timed out waiting for GTK main thread");
    }

    return future.get();
#else
    return task();
#endif
}

} // namespace mcp_bridge
