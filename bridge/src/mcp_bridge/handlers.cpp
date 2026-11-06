#include "handlers.h"
#include "auth.h"
#include "dispatcher.h"
#include "types_serializer.h"

#include <iostream>
#include <vector>

#ifndef MCP_BRIDGE_STANDALONE
#include <gui/app.h>
#include <gui/instance.h>
#include <gui/canvasview.h>
#include <synfigapp/canvasinterface.h>
#include <synfigapp/selectionmanager.h>
#include <synfig/canvas.h>
#include <synfig/layer.h>
#include <synfig/layers/layer_pastecanvas.h>
#include <synfig/renddesc.h>
#endif

namespace mcp_bridge {

const char* PROTOCOL_VERSION = "1.0";
const char* STUDIO_VERSION = "1.5.5";

static std::string s_session_token;

void set_session_token(const std::string& token) {
    s_session_token = token;
}

std::string get_session_token() {
    return s_session_token;
}

#ifndef MCP_BRIDGE_STANDALONE
static etl::handle<studio::Instance> resolve_instance(const std::string& doc_id) {
    if (studio::App::instance_list.empty()) {
        return nullptr;
    }

    if (doc_id.empty() || doc_id == "active" || doc_id == "doc_0") {
        etl::handle<studio::Instance> sel = studio::App::get_selected_instance();
        if (sel) return sel;
        return studio::App::instance_list.front();
    }

    int idx = 0;
    for (auto it = studio::App::instance_list.begin(); it != studio::App::instance_list.end(); ++it, ++idx) {
        std::string current_id = "doc_" + std::to_string(idx);
        if (doc_id == current_id || (*it)->get_file_name() == doc_id) {
            return *it;
        }
        if ((*it)->get_canvas() && (*it)->get_canvas()->get_name() == doc_id) {
            return *it;
        }
    }

    return nullptr;
}

static synfig::Layer::Handle find_layer_in_canvas(synfig::Canvas::Handle canvas, const std::string& layer_id) {
    if (!canvas) return nullptr;

    for (auto it = canvas->begin(); it != canvas->end(); ++it) {
        synfig::Layer::Handle layer = *it;
        if (!layer) continue;

        if (layer->get_description() == layer_id ||
            layer->get_guid().get_string() == layer_id ||
            layer->get_name() == layer_id) {
            return layer;
        }

        etl::handle<synfig::Layer_PasteCanvas> paste =
            etl::handle<synfig::Layer_PasteCanvas>::cast_dynamic(layer);
        if (paste && paste->get_sub_canvas()) {
            synfig::Layer::Handle sub = find_layer_in_canvas(paste->get_sub_canvas(), layer_id);
            if (sub) return sub;
        }
    }
    return nullptr;
}

static nlohmann::json build_layer_tree(synfig::Canvas::Handle canvas) {
    nlohmann::json layers = nlohmann::json::array();
    if (!canvas) return layers;

    for (auto it = canvas->rbegin(); it != canvas->rend(); ++it) {
        synfig::Layer::Handle layer = *it;
        if (!layer) continue;

        nlohmann::json l;
        l["id"] = layer->get_guid().get_string();
        l["desc"] = layer->get_description();
        l["type"] = layer->get_name();
        l["active"] = layer->active();
        l["depth"] = layer->get_depth();

        etl::handle<synfig::Layer_PasteCanvas> paste =
            etl::handle<synfig::Layer_PasteCanvas>::cast_dynamic(layer);
        if (paste && paste->get_sub_canvas()) {
            l["children"] = build_layer_tree(paste->get_sub_canvas());
        } else {
            l["children"] = nlohmann::json::array();
        }

        layers.push_back(l);
    }
    return layers;
}
#endif

nlohmann::json dispatch_request(const nlohmann::json& req, bool& inout_authenticated) {
    nlohmann::json res;
    res["jsonrpc"] = "2.0";

    if (!req.contains("id")) {
        res["id"] = nullptr;
    } else {
        res["id"] = req["id"];
    }

    if (!req.contains("method") || !req["method"].is_string()) {
        res["error"] = {
            {"code", -32600},
            {"message", "Invalid Request: missing or invalid 'method' field"}
        };
        return res;
    }

    std::string method = req["method"].get<std::string>();
    nlohmann::json params = req.value("params", nlohmann::json::object());

    // 1. Handshake
    if (method == "hello") {
        std::string client_token = params.value("token", "");
        std::string client_version = params.value("protocol_version", "");

        if (!validate_token(client_token, s_session_token)) {
            res["error"] = {
                {"code", 1002},
                {"message", "Authentication failed: invalid token"}
            };
            return res;
        }

        std::string client_major = client_version.substr(0, client_version.find('.'));
        std::string server_major = std::string(PROTOCOL_VERSION).substr(0, std::string(PROTOCOL_VERSION).find('.'));
        if (client_major != server_major) {
            res["error"] = {
                {"code", 1003},
                {"message", "Incompatible protocol version"}
            };
            return res;
        }

        inout_authenticated = true;
        res["result"] = {
            {"protocol_version", PROTOCOL_VERSION},
            {"studio_version", STUDIO_VERSION},
            {"capabilities", {
                "doc.read",
                "scene.read",
                "param.read",
                "selection.read",
                "anim.read",
                "events"
            }},
            {"session_id", "synfig_mcp_session"}
        };
        return res;
    }

    // Require authentication for all subsequent methods
    if (!inout_authenticated) {
        res["error"] = {
            {"code", 1002},
            {"message", "Client not authenticated. Send 'hello' handshake first."}
        };
        return res;
    }

#ifndef MCP_BRIDGE_STANDALONE
    // 2. doc.list
    if (method == "doc.list") {
        return run_on_main_thread([&]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            nlohmann::json doc_list = nlohmann::json::array();
            int idx = 0;
            for (auto it = studio::App::instance_list.begin(); it != studio::App::instance_list.end(); ++it, ++idx) {
                etl::handle<studio::Instance> inst = *it;
                if (!inst || !inst->get_canvas()) continue;

                nlohmann::json doc_item;
                doc_item["doc_id"] = "doc_" + std::to_string(idx);
                doc_item["name"] = inst->get_canvas()->get_name();
                doc_item["file_path"] = inst->get_file_name().empty() ? nullptr : nlohmann::json(inst->get_file_name());
                doc_list.push_back(doc_item);
            }

            r["result"] = doc_list;
            return r;
        });
    }

    // 3. doc.info
    if (method == "doc.info") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {
                    {"code", 2001},
                    {"message", "Document not found: " + doc_id}
                };
                return r;
            }

            synfig::Canvas::Handle canvas = inst->get_canvas();
            const synfig::RendDesc& desc = canvas->rend_desc();
            double fps = static_cast<double>(desc.get_frame_rate());
            double start_t = static_cast<double>(desc.get_time_start());
            double end_t = static_cast<double>(desc.get_time_end());
            int duration_frames = static_cast<int>((end_t - start_t) * fps);

            r["result"] = {
                {"doc_id", doc_id},
                {"name", canvas->get_name()},
                {"file_path", inst->get_file_name().empty() ? nullptr : nlohmann::json(inst->get_file_name())},
                {"width", desc.get_w()},
                {"height", desc.get_h()},
                {"fps", fps},
                {"start_time", start_t},
                {"end_time", end_t},
                {"duration_frames", duration_frames}
            };
            return r;
        });
    }

    // 4. scene.tree
    if (method == "scene.tree") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {
                    {"code", 2001},
                    {"message", "Document not found: " + doc_id}
                };
                return r;
            }

            nlohmann::json tree = build_layer_tree(inst->get_canvas());
            r["result"] = {
                {"doc_id", doc_id},
                {"layers", tree}
            };
            return r;
        });
    }

    // 5. param.get
    if (method == "param.get") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");

        return run_on_main_thread([&, doc_id, layer_id, param_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {
                    {"code", 2001},
                    {"message", "Document not found: " + doc_id}
                };
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {
                    {"code", 2002},
                    {"message", "Layer not found: " + layer_id}
                };
                return r;
            }

            synfig::ValueBase val = layer->get_param(param_name);
            if (!val.is_valid()) {
                r["error"] = {
                    {"code", 2003},
                    {"message", "Parameter not found: " + param_name}
                };
                return r;
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"value", valuebase_to_json(val)}
            };
            return r;
        });
    }

    // 6. selection.get
    if (method == "selection.get") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {
                    {"code", 2001},
                    {"message", "Document not found: " + doc_id}
                };
                return r;
            }

            etl::handle<studio::CanvasView> cv = inst->find_canvas_view(inst->get_canvas());
            if (!cv) {
                cv = studio::App::get_selected_canvas_view();
            }

            nlohmann::json selected_layers = nlohmann::json::array();
            if (cv && cv->get_selection_manager()) {
                auto selected = cv->get_selection_manager()->get_selected_layers();
                for (auto it = selected.begin(); it != selected.end(); ++it) {
                    if (*it) {
                        std::string name = (*it)->get_description().empty() ? (*it)->get_name() : (*it)->get_description();
                        selected_layers.push_back(name);
                    }
                }
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"selected_layers", selected_layers}
            };
            return r;
        });
    }

    // 7. anim.time_get
    if (method == "anim.time_get") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {
                    {"code", 2001},
                    {"message", "Document not found: " + doc_id}
                };
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfig::Time t(0);
            if (ci) {
                t = ci->get_time();
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"time", {
                    {"seconds", static_cast<double>(t)},
                    {"string", t.get_string()}
                }}
            };
            return r;
        });
    }
#else
    // Standalone fallback for testing without Synfig Studio
    if (method == "doc.info") {
        res["result"] = {
            {"doc_id", params.value("doc_id", "doc_0")},
            {"name", "Standalone Test Canvas"},
            {"file_path", nullptr},
            {"width", 1920},
            {"height", 1080},
            {"fps", 24.0},
            {"start_time", 0.0},
            {"end_time", 5.0},
            {"duration_frames", 120}
        };
        return res;
    }
#endif

    // Unhandled method
    res["error"] = {
        {"code", -32601},
        {"message", "Method not found: " + method}
    };
    return res;
}

} // namespace mcp_bridge
