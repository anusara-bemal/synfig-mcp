#include "handlers.h"
#include "auth.h"
#include "dispatcher.h"
#include "types_serializer.h"

#include <iostream>
#include <vector>
#include <string>

#ifndef MCP_BRIDGE_STANDALONE
#include <gui/app.h>
#include <gui/instance.h>
#include <gui/canvasview.h>
#include <synfigapp/action.h>
#include <synfigapp/action_system.h>
#include <synfigapp/canvasinterface.h>
#include <synfigapp/selectionmanager.h>
#include <synfigapp/value_desc.h>
#include <synfig/canvas.h>
#include <synfig/layer.h>
#include <synfig/layers/layer_pastecanvas.h>
#include <synfig/renddesc.h>
#include <synfig/keyframe.h>
#include <synfig/time.h>
#include <synfig/target.h>
#include <synfig/targetparam.h>
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

static nlohmann::json make_diff(const std::string& action,
                                const std::vector<std::string>& created = {},
                                const std::vector<std::string>& modified = {},
                                const std::vector<std::string>& deleted = {}) {
    nlohmann::json d;
    d["action"] = action;
    d["created"] = created;
    d["modified"] = modified;
    d["deleted"] = deleted;
    return d;
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
                "doc.write",
                "scene.read",
                "layer.write",
                "param.read",
                "param.write",
                "selection.read",
                "selection.write",
                "anim.read",
                "anim.write",
                "history",
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
    // --- 2. DOCUMENT METHODS ---
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

    if (method == "doc.new") {
        return run_on_main_thread([&]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            studio::App::new_instance();
            if (studio::App::instance_list.empty()) {
                r["error"] = {{"code", -32000}, {"message", "Failed to create new document"}};
                return r;
            }

            etl::handle<studio::Instance> inst = studio::App::instance_list.back();
            synfig::Canvas::Handle canvas = inst->get_canvas();
            synfig::RendDesc desc = canvas->rend_desc();

            if (params.contains("width")) desc.set_w(params["width"].get<int>());
            if (params.contains("height")) desc.set_h(params["height"].get<int>());
            if (params.contains("fps")) desc.set_frame_rate(params["fps"].get<float>());
            if (params.contains("duration")) desc.set_time_end(synfig::Time(params["duration"].get<double>()));
            canvas->rend_desc() = desc;

            std::string new_doc_id = "doc_" + std::to_string(studio::App::instance_list.size() - 1);
            r["result"] = {
                {"doc_id", new_doc_id},
                {"name", canvas->get_name()},
                {"width", desc.get_w()},
                {"height", desc.get_h()},
                {"fps", static_cast<double>(desc.get_frame_rate())},
                {"diff", make_diff("doc.new", {new_doc_id}, {}, {})}
            };
            return r;
        });
    }

    if (method == "doc.open") {
        std::string file_path = params.value("file_path", "");
        return run_on_main_thread([&, file_path]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            if (file_path.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing 'file_path' parameter"}};
                return r;
            }

            bool ok = studio::App::open(synfig::filesystem::Path(file_path));
            if (!ok || studio::App::instance_list.empty()) {
                r["error"] = {{"code", 2001}, {"message", "Failed to open document: " + file_path}};
                return r;
            }

            etl::handle<studio::Instance> inst = studio::App::instance_list.back();
            std::string doc_id = "doc_" + std::to_string(studio::App::instance_list.size() - 1);
            r["result"] = {
                {"doc_id", doc_id},
                {"name", inst->get_canvas()->get_name()},
                {"file_path", inst->get_file_name()},
                {"diff", make_diff("doc.open", {doc_id}, {}, {})}
            };
            return r;
        });
    }

    if (method == "doc.save") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string file_path = params.value("file_path", "");
        return run_on_main_thread([&, doc_id, file_path]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            bool ok = false;
            if (!file_path.empty()) {
                ok = inst->save_as(file_path);
            } else {
                ok = inst->save();
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"file_path", inst->get_file_name()},
                {"success", ok},
                {"diff", make_diff("doc.save", {}, {doc_id}, {})}
            };
            return r;
        });
    }

    if (method == "doc.close") {
        std::string doc_id = params.value("doc_id", "doc_0");
        bool force = params.value("force", false);
        return run_on_main_thread([&, doc_id, force]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            // Safe closing without blocking on GTK modal dialogs:
            // If dirty and !force, return an explicit error instead of popping a modal dialog.
            if (!force && inst->get_action_count() > 0) {
                r["error"] = {{"code", 2004}, {"message", "Document has unsaved changes. Set force=true or save first."}};
                return r;
            }

            // Direct close() bypasses safe_close() yes_no_cancel dialog completely.
            inst->close();

            r["result"] = {
                {"doc_id", doc_id},
                {"closed", true},
                {"diff", make_diff("doc.close", {}, {}, {doc_id})}
            };
            return r;
        });
    }

    if (method == "doc.set_properties") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: doc.set_properties");

            synfig::RendDesc desc = inst->get_canvas()->rend_desc();
            if (params.contains("width")) desc.set_w(params["width"].get<int>());
            if (params.contains("height")) desc.set_h(params["height"].get<int>());
            if (params.contains("fps")) desc.set_frame_rate(params["fps"].get<float>());
            if (params.contains("start_time")) desc.set_time_start(synfig::Time(params["start_time"].get<double>()));
            if (params.contains("end_time")) desc.set_time_end(synfig::Time(params["end_time"].get<double>()));

            synfigapp::Action::Handle action = synfigapp::Action::create("CanvasRendDescSet");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("rend_desc", desc);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"width", desc.get_w()},
                {"height", desc.get_h()},
                {"fps", static_cast<double>(desc.get_frame_rate())},
                {"start_time", static_cast<double>(desc.get_time_start())},
                {"end_time", static_cast<double>(desc.get_time_end())},
                {"diff", make_diff("doc.set_properties", {}, {doc_id}, {})}
            };
            return r;
        });
    }

    // --- 3. CANVAS METHODS ---
    if (method == "canvas.list") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            nlohmann::json canvases = nlohmann::json::array();
            canvases.push_back({
                {"canvas_id", inst->get_canvas()->get_id()},
                {"name", inst->get_canvas()->get_name()}
            });

            for (auto it = inst->get_canvas()->children().begin(); it != inst->get_canvas()->children().end(); ++it) {
                if (*it) {
                    canvases.push_back({
                        {"canvas_id", (*it)->get_id()},
                        {"name", (*it)->get_name()}
                    });
                }
            }

            r["result"] = {{"doc_id", doc_id}, {"canvases", canvases}};
            return r;
        });
    }

    if (method == "canvas.create") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string canvas_id = params.value("id", "child_canvas");
        return run_on_main_thread([&, doc_id, canvas_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: canvas.create");

            synfigapp::Action::Handle action = synfigapp::Action::create("CanvasAdd");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("src", synfig::Canvas::create());
                action->set_param("id", canvas_id);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"diff", make_diff("canvas.create", {canvas_id}, {}, {})}
            };
            return r;
        });
    }

    // --- 4. SCENE & LAYER METHODS ---
    if (method == "scene.tree") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            nlohmann::json tree = build_layer_tree(inst->get_canvas());
            r["result"] = {{"doc_id", doc_id}, {"layers", tree}};
            return r;
        });
    }

    if (method == "layer.add") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_type = params.value("layer_type", "circle");
        int depth = params.value("depth", 0);
        std::string desc = params.value("description", "");

        return run_on_main_thread([&, doc_id, layer_type, depth, desc]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            if (!ci) {
                r["error"] = {{"code", -32000}, {"message", "Canvas interface not found"}};
                return r;
            }

            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.add");

            synfig::Layer::Handle layer = ci->add_layer_to(layer_type, inst->get_canvas(), depth);
            if (!layer) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create layer of type: " + layer_type}};
                return r;
            }

            if (!desc.empty()) {
                layer->set_description(desc);
            }

            // Apply optional initial parameters
            if (params.contains("params") && params["params"].is_object()) {
                for (auto& item : params["params"].items()) {
                    synfig::ValueBase val = json_to_valuebase(item.value());
                    if (val.is_valid()) {
                        ci->change_value(synfigapp::ValueDesc(layer, item.key()), val);
                    }
                }
            }

            grouper.finish();

            std::string final_id = layer->get_description().empty() ? layer->get_guid().get_string() : layer->get_description();
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", final_id},
                {"layer_type", layer->get_name()},
                {"description", layer->get_description()},
                {"depth", layer->get_depth()},
                {"diff", make_diff("layer.add", {final_id}, {}, {})}
            };
            return r;
        });
    }

    if (method == "layer.remove" || method == "layer.delete") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        return run_on_main_thread([&, doc_id, layer_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.remove");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerRemove");
            if (action) {
                action->set_param("canvas", layer->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("layer", layer);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"diff", make_diff("layer.remove", {}, {}, {layer_id})}
            };
            return r;
        });
    }

    if (method == "layer.duplicate") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        return run_on_main_thread([&, doc_id, layer_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.duplicate");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerDuplicate");
            if (action) {
                action->set_param("canvas", layer->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("layer", layer);
                inst->perform_action(action);
            }

            grouper.finish();

            std::string dup_id = layer_id + "_copy";
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", dup_id},
                {"diff", make_diff("layer.duplicate", {dup_id}, {}, {})}
            };
            return r;
        });
    }

    if (method == "layer.reorder" || method == "layer.move") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        int new_depth = params.value("new_depth", 0);
        return run_on_main_thread([&, doc_id, layer_id, new_depth]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.reorder");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerMove");
            if (action) {
                action->set_param("canvas", layer->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("layer", layer);
                action->set_param("new_index", new_depth);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"depth", new_depth},
                {"diff", make_diff("layer.reorder", {}, {layer_id}, {})}
            };
            return r;
        });
    }

    if (method == "layer.raise" || method == "layer.lower") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        bool is_raise = (method == "layer.raise");
        return run_on_main_thread([&, doc_id, layer_id, is_raise]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), is_raise ? "mcp: layer.raise" : "mcp: layer.lower");

            synfigapp::Action::Handle action = synfigapp::Action::create(is_raise ? "LayerRaise" : "LayerLower");
            if (action) {
                action->set_param("canvas", layer->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("layer", layer);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"depth", layer->get_depth()},
                {"diff", make_diff(is_raise ? "layer.raise" : "layer.lower", {}, {layer_id}, {})}
            };
            return r;
        });
    }

    if (method == "layer.group") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::vector<std::string> layer_ids = params.value("layer_ids", std::vector<std::string>());
        std::string group_name = params.value("group_name", "Group");

        return run_on_main_thread([&, doc_id, layer_ids, group_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.group");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerEncapsulate");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("description", synfig::String(group_name));

                for (const auto& lid : layer_ids) {
                    synfig::Layer::Handle l = find_layer_in_canvas(inst->get_canvas(), lid);
                    if (l) {
                        action->set_param("layer", l);
                    }
                }
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"group_id", group_name},
                {"grouped_layers", layer_ids},
                {"diff", make_diff("layer.group", {group_name}, {}, {})}
            };
            return r;
        });
    }

    if (method == "layer.ungroup") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string group_id = params.value("group_layer_id", "");
        return run_on_main_thread([&, doc_id, group_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), group_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + group_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: layer.ungroup");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerExtract");
            if (action) {
                action->set_param("canvas", layer->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("layer", layer);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"group_id", group_id},
                {"diff", make_diff("layer.ungroup", {}, {}, {group_id})}
            };
            return r;
        });
    }

    // --- 5. PARAMETER METHODS ---
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
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            synfig::ValueBase val = layer->get_param(param_name);
            if (!val.is_valid()) {
                r["error"] = {{"code", 2003}, {"message", "Parameter not found: " + param_name}};
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

    if (method == "param.set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        nlohmann::json val_json = params.value("value", nlohmann::json::object());

        return run_on_main_thread([&, doc_id, layer_id, param_name, val_json]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            synfig::ValueBase old_val = layer->get_param(param_name);
            synfig::ValueBase new_val = json_to_valuebase(val_json);
            if (!new_val.is_valid()) {
                r["error"] = {{"code", -32602}, {"message", "Invalid value for parameter: " + param_name}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: param.set");

            bool ok = ci->change_value(synfigapp::ValueDesc(layer, param_name), new_val);
            if (!ok) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to set parameter: " + param_name}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"before", valuebase_to_json(old_val)},
                {"after", val_json},
                {"diff", make_diff("param.set", {}, {layer_id}, {})}
            };
            return r;
        });
    }

    // --- 6. ANIMATION METHODS ---
    if (method == "anim.time_get" || method == "anim.time.get") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
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

    if (method == "anim.time_set" || method == "anim.time.set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        double t_sec = 0.0;
        if (params.contains("time")) {
            if (params["time"].is_number()) {
                t_sec = params["time"].get<double>();
            } else if (params["time"].is_object() && params["time"].contains("seconds")) {
                t_sec = params["time"]["seconds"].get<double>();
            }
        }

        return run_on_main_thread([&, doc_id, t_sec]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfig::Time t(t_sec);
            if (ci) {
                ci->seek_time(t);
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

    if (method == "anim.keyframe_add" || method == "keyframe.add") {
        std::string doc_id = params.value("doc_id", "doc_0");
        double t_sec = params.value("time", 0.0);
        std::string desc = params.value("description", "");

        return run_on_main_thread([&, doc_id, t_sec, desc]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.keyframe_add");

            synfig::Time t_kf(t_sec);
            synfig::Keyframe kf(t_kf);
            if (!desc.empty()) {
                kf.set_description(desc);
            }

            synfigapp::Action::Handle action = synfigapp::Action::create("KeyframeAdd");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("keyframe", kf);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"time", t_sec},
                {"description", desc},
                {"diff", make_diff("anim.keyframe_add", {std::to_string(t_sec)}, {}, {})}
            };
            return r;
        });
    }

    if (method == "anim.keyframe_remove" || method == "keyframe.delete" || method == "keyframe.remove") {
        std::string doc_id = params.value("doc_id", "doc_0");
        double t_sec = params.value("time", 0.0);

        return run_on_main_thread([&, doc_id, t_sec]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.keyframe_remove");

            synfig::KeyframeList::iterator iter;
            if (!inst->get_canvas()->keyframe_list().find(synfig::Time(t_sec), iter)) {
                grouper.cancel();
                r["error"] = {{"code", 2002}, {"message", "Keyframe not found at time: " + std::to_string(t_sec)}};
                return r;
            }

            synfig::Keyframe kf = *iter;
            synfigapp::Action::Handle action = synfigapp::Action::create("KeyframeRemove");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("keyframe", kf);
                inst->perform_action(action);
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"time", t_sec},
                {"diff", make_diff("anim.keyframe_remove", {}, {}, {std::to_string(t_sec)})}
            };
            return r;
        });
    }

    if (method == "anim.keyframe_list" || method == "keyframe.list") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            nlohmann::json kfs = nlohmann::json::array();
            for (const auto& kf : inst->get_canvas()->keyframe_list()) {
                nlohmann::json kf_obj;
                kf_obj["time"] = static_cast<double>(kf.get_time());
                kf_obj["description"] = kf.get_description();
                kf_obj["active"] = kf.active();
                kfs.push_back(kf_obj);
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"keyframes", kfs}
            };
            return r;
        });
    }

    if (method == "anim.waypoint_set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        double t_sec = params.value("time", 0.0);
        nlohmann::json val_json = params.value("value", nlohmann::json::object());

        return run_on_main_thread([&, doc_id, layer_id, param_name, t_sec, val_json]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            synfig::ValueBase val = json_to_valuebase(val_json);
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.waypoint_set");

            ci->change_value_at_time(synfigapp::ValueDesc(layer, param_name), val, synfig::Time(t_sec));
            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"time", t_sec},
                {"value", val_json},
                {"diff", make_diff("anim.waypoint_set", {}, {layer_id}, {})}
            };
            return r;
        });
    }

    // --- 7. SELECTION METHODS ---
    if (method == "selection.get") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
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

    if (method == "selection.set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::vector<std::string> layer_ids = params.value("layer_ids", std::vector<std::string>());

        return run_on_main_thread([&, doc_id, layer_ids]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<studio::CanvasView> cv = inst->find_canvas_view(inst->get_canvas());
            if (!cv) {
                cv = studio::App::get_selected_canvas_view();
            }

            if (!cv || !cv->get_selection_manager()) {
                r["error"] = {{"code", -32000}, {"message", "Selection manager not available"}};
                return r;
            }

            synfigapp::SelectionManager::LayerList layer_list;
            for (const auto& lid : layer_ids) {
                synfig::Layer::Handle l = find_layer_in_canvas(inst->get_canvas(), lid);
                if (l) {
                    layer_list.push_back(l);
                }
            }

            cv->get_selection_manager()->set_selected_layers(layer_list);

            r["result"] = {
                {"doc_id", doc_id},
                {"selected_layers", layer_ids}
            };
            return r;
        });
    }

    // --- 8. HISTORY METHODS ---
    if (method == "history.undo" || method == "history.redo") {
        std::string doc_id = params.value("doc_id", "doc_0");
        bool is_undo = (method == "history.undo");

        return run_on_main_thread([&, doc_id, is_undo]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            bool ok = is_undo ? inst->undo() : inst->redo();
            r["result"] = {
                {"doc_id", doc_id},
                {"success", ok},
                {"diff", make_diff(is_undo ? "history.undo" : "history.redo", {}, {doc_id}, {})}
            };
            return r;
        });
    }

    if (method == "history.list") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            nlohmann::json undo_stack = nlohmann::json::array();
            for (const auto& a : inst->undo_action_stack()) {
                if (a) undo_stack.push_back(a->get_name());
            }

            nlohmann::json redo_stack = nlohmann::json::array();
            for (const auto& a : inst->redo_action_stack()) {
                if (a) redo_stack.push_back(a->get_name());
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"undo_stack", undo_stack},
                {"redo_stack", redo_stack}
            };
            return r;
        });
    }

    if (method == "render.frame" || method == "canvas.render_frame") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string output_path = params.value("output_path", "");
        double render_time = params.value("time", 0.0);
        std::string target_name = params.value("target", "png");

        return run_on_main_thread([&, doc_id, output_path, render_time, target_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            if (output_path.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing 'output_path' parameter"}};
                return r;
            }

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Canvas::Handle canvas = inst->get_canvas();
            synfig::RendDesc desc = canvas->rend_desc();
            if (params.contains("width")) desc.set_w(params["width"].get<int>());
            if (params.contains("height")) desc.set_h(params["height"].get<int>());
            desc.set_time(synfig::Time(render_time));

            synfig::Target::Handle target = synfig::Target::create(
                target_name,
                synfig::filesystem::Path(output_path),
                synfig::TargetParam()
            );

            if (!target) {
                std::string ext = synfig::filesystem::Path::filename_extension(output_path);
                if (!ext.empty() && ext[0] == '.') ext.erase(0, 1);
                if (!ext.empty() && synfig::Target::ext_book().count(ext)) {
                    target = synfig::Target::create(
                        synfig::Target::ext_book()[ext],
                        synfig::filesystem::Path(output_path),
                        synfig::TargetParam()
                    );
                }
            }

            if (!target) {
                r["error"] = {{"code", 2005}, {"message", "Unable to create render target for: " + output_path}};
                return r;
            }

            target->set_canvas(canvas);
            target->set_rend_desc(&desc);
            target->set_quality(4);

            bool ok = target->init();
            if (ok) {
                ok = target->render();
            }

            if (!ok) {
                r["error"] = {{"code", 2006}, {"message", "Frame render failed for: " + output_path}};
                return r;
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"output_path", output_path},
                {"time", render_time},
                {"success", true}
            };
            return r;
        });
    }

    if (method == "test.manual_action") {
        std::string doc_id = params.value("doc_id", "doc_0");
        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Canvas::Handle canvas = inst->get_canvas();
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(canvas);

            synfig::Layer::Handle layer = synfig::Layer::create("circle");
            layer->set_description("ManualUserCircle");
            layer->set_canvas(canvas);

            bool ok = ci ? ci->layer_add_action(layer) : false;

            r["result"] = {
                {"doc_id", doc_id},
                {"success", ok},
                {"manual", true}
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
    if (method == "layer.add" || method == "param.set" || method == "history.undo" || method == "history.redo" || method == "doc.close" || method == "render.frame" || method == "canvas.render_frame" || method == "test.manual_action" || method == "anim.keyframe_list" || method == "keyframe.list") {
        res["result"] = {
            {"doc_id", params.value("doc_id", "doc_0")},
            {"success", true},
            {"closed", true},
            {"diff", make_diff(method, {"mock_id"}, {}, {})}
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
