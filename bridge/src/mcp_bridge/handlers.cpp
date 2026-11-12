#include "handlers.h"
#include "auth.h"
#include "bridge_init.h"
#include "dispatcher.h"
#include "types_serializer.h"

#include <iostream>
#include <vector>
#include <list>
#include <string>
#include <sstream>
#include <algorithm>
#include <filesystem>
#include <cctype>

#ifdef _WIN32
#include <windows.h>
#else
#include <limits.h>
#include <stdlib.h>
#include <unistd.h>
#endif

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
#include <synfig/paramdesc.h>
#include <synfig/layers/layer_pastecanvas.h>
#include <synfig/renddesc.h>
#include <synfig/keyframe.h>
#include <synfig/time.h>
#include <synfig/target.h>
#include <synfig/targetparam.h>
#include <synfig/valuenodes/valuenode_animated.h>
#include <synfig/valuenodes/valuenode_bone.h>
#include <synfig/valuenodes/valuenode_staticlist.h>
#include <synfig/bone.h>
#include <synfig/valuenode_registry.h>
#include <synfig/waypoint.h>
#include <synfigapp/main.h>
#endif

namespace mcp_bridge {

#ifndef MCP_BRIDGE_STANDALONE
static synfig::Interpolation parse_interpolation(const std::string& str, synfig::Interpolation default_val = synfig::INTERPOLATION_TCB) {
    if (str == "linear") return synfig::INTERPOLATION_LINEAR;
    if (str == "constant") return synfig::INTERPOLATION_CONSTANT;
    if (str == "halt") return synfig::INTERPOLATION_HALT;
    if (str == "clamped") return synfig::INTERPOLATION_CLAMPED;
    if (str == "manual") return synfig::INTERPOLATION_MANUAL;
    // "auto" is the name Synfig shows in the UI for the TCB spline mode.
    if (str == "auto" || str == "tcb") return synfig::INTERPOLATION_TCB;
    return default_val;
}
#endif

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

//! Build an error response immediately, without dispatching to the GUI thread.
/*!
 * Every handler that needs a layer, a parameter or a value node must reject
 * empty identifiers *before* it queues work on the main thread.  Dispatching
 * a request with an empty identifier used to enqueue a task that could never
 * resolve, so the caller waited for its transport timeout instead of getting a
 * deterministic 2002 error.  This helper produces the JSON-RPC error payload
 * directly on the socket thread.
 *
 * The payload carries both the JSON-RPC ``error`` object (for protocol
 * clients) and the flat ``status``/``code``/``message`` members (for tooling
 * that reads the response body without unwrapping ``error``).
 */
static std::string safe_extract_string(const nlohmann::json& obj, const std::string& key, const std::string& fallback = "") {
    if (!obj.is_object() || !obj.contains(key) || obj[key].is_null()) {
        return fallback;
    }
    if (obj[key].is_string()) {
        return obj[key].get<std::string>();
    }
    return fallback;
}

static nlohmann::json make_input_error(const nlohmann::json& req,
                                       int code,
                                       const std::string& message) {
    nlohmann::json r;
    r["jsonrpc"] = "2.0";
    if (req.contains("id")) {
        r["id"] = req["id"];
    }
    r["status"] = "error";
    r["code"] = code;
    r["message"] = message;
    r["error"] = {{"code", code}, {"message", message}};
    return r;
}

//! Validate the identifiers every layer-scoped request depends on.
/*!
 * Returns an empty JSON object when the request may proceed, or a fully
 * formed error response when it must be rejected.  Callers use the
 * ``is_null()`` check so a legitimate empty result is never confused with an
 * error.
 */
static bool reject_empty_identifiers(const nlohmann::json& req,
                                     const std::string& layer_id,
                                     const std::string& param_name,
                                     nlohmann::json& out) {
    if (layer_id.empty()) {
        out = make_input_error(req, 2002, "Layer ID cannot be empty or null.");
        return true;
    }
    if (param_name.empty()) {
        out = make_input_error(req, 2003, "Parameter name cannot be empty or null.");
        return true;
    }
    return false;
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

static std::string interpolation_to_string(synfig::Interpolation interpolation) {
    switch (interpolation) {
    case synfig::INTERPOLATION_LINEAR: return "linear";
    case synfig::INTERPOLATION_CONSTANT: return "constant";
    case synfig::INTERPOLATION_HALT: return "halt";
    case synfig::INTERPOLATION_CLAMPED: return "clamped";
    case synfig::INTERPOLATION_MANUAL: return "manual";
    case synfig::INTERPOLATION_TCB: return "auto";
    default: return "linear";
    }
}

static synfig::Canvas::Handle find_canvas_by_id(synfig::Canvas::Handle canvas, const std::string& canvas_id) {
    if (!canvas) return nullptr;
    if (canvas_id.empty() || canvas_id == ":" || canvas_id == "root") return canvas;
    if (canvas->get_id() == canvas_id || canvas->get_name() == canvas_id) return canvas;
    for (auto& child : canvas->children()) {
        synfig::Canvas::Handle found = find_canvas_by_id(child, canvas_id);
        if (found) return found;
    }
    return nullptr;
}

static nlohmann::json build_layer_params(synfig::Layer::Handle layer) {
    nlohmann::json params = nlohmann::json::object();
    if (!layer) return params;
    for (const auto& item : layer->get_param_list()) {
        if (!item.second.is_valid()) continue;
        params[item.first] = valuebase_to_json(item.second);
    }
    return params;
}

static nlohmann::json build_layer_tree(synfig::Canvas::Handle canvas) {
    nlohmann::json layers = nlohmann::json::array();
    if (!canvas) return layers;

    for (auto it = canvas->rbegin(); it != canvas->rend(); ++it) {
        synfig::Layer::Handle layer = *it;
        if (!layer) continue;

        nlohmann::json l;
        const synfig::String description = layer->get_description();
        // The id is the description when the layer has one, so the same value
        // can be used to address the layer in every backend.
        l["id"] = description.empty() ? layer->get_guid().get_string() : description;
        l["desc"] = description;
        l["description"] = description;
        l["type"] = layer->get_name();
        l["active"] = layer->active();
        l["depth"] = layer->get_depth();
        l["params"] = build_layer_params(layer);

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

#ifdef MCP_BRIDGE_STANDALONE
const char* get_build_version() {
    return "0.8.0";
}
const char* get_build_commit_sha() {
    return "dev";
}
#endif

static std::vector<std::string> s_workspace_roots;

static std::string normalize_path_str(const std::string& p) {
    if (p.empty()) return "";
#ifdef _WIN32
    char full[MAX_PATH];
    if (GetFullPathNameA(p.c_str(), MAX_PATH, full, NULL) == 0) {
        return p;
    }
    std::string cur_full = full;
    std::string rel_suffix = "";

    HANDLE h = CreateFileA(cur_full.c_str(), 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    while (h == INVALID_HANDLE_VALUE && !cur_full.empty()) {
        size_t last_slash = cur_full.find_last_of("\\/");
        if (last_slash == std::string::npos) break;
        std::string component = cur_full.substr(last_slash + 1);
        rel_suffix = rel_suffix.empty() ? component : (component + "\\" + rel_suffix);
        cur_full = cur_full.substr(0, last_slash);
        h = CreateFileA(cur_full.c_str(), 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    }

    std::string res;
    if (h != INVALID_HANDLE_VALUE) {
        char final_p[MAX_PATH];
        DWORD ret = GetFinalPathNameByHandleA(h, final_p, MAX_PATH, FILE_NAME_NORMALIZED);
        CloseHandle(h);
        if (ret > 0 && ret < MAX_PATH) {
            std::string resolved = final_p;
            if (resolved.rfind("\\\\?\\", 0) == 0) resolved = resolved.substr(4);
            res = rel_suffix.empty() ? resolved : (resolved + "\\" + rel_suffix);
        } else {
            res = full;
        }
    } else {
        res = full;
    }
    std::transform(res.begin(), res.end(), res.begin(), ::tolower);
    std::replace(res.begin(), res.end(), '/', '\\');
    while (!res.empty() && (res.back() == '\\' || res.back() == '/')) res.pop_back();
    return res;
#else
    char resolved[PATH_MAX];
    if (realpath(p.c_str(), resolved)) {
        return std::string(resolved);
    }
    std::string cur = p;
    std::string rel;
    while (!cur.empty()) {
        if (realpath(cur.c_str(), resolved)) {
            std::string canon_base(resolved);
            return rel.empty() ? canon_base : (canon_base + "/" + rel);
        }
        size_t slash = cur.find_last_of('/');
        if (slash == std::string::npos) break;
        std::string comp = cur.substr(slash + 1);
        rel = rel.empty() ? comp : (comp + "/" + rel);
        cur = cur.substr(0, slash);
    }
    return p;
#endif
}

static bool is_within_root(const std::string& target_canon, const std::string& root_canon) {
    std::string s_target = normalize_path_str(target_canon);
    std::string s_root = normalize_path_str(root_canon);
    if (s_target == s_root) return true;
#ifdef _WIN32
    if (s_target.rfind(s_root + "\\", 0) == 0) return true;
#else
    if (s_target.rfind(s_root + "/", 0) == 0) return true;
#endif
    return false;
}

static bool is_overly_broad_root(const std::string& path_str, std::string& reason) {
    std::string normalized = path_str;
    std::replace(normalized.begin(), normalized.end(), '\\', '/');
    while (normalized.size() > 1 && normalized.back() == '/') normalized.pop_back();

#ifdef _WIN32
    std::string lower = normalized;
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    const char* home = std::getenv("USERPROFILE");
    const char* system_root = std::getenv("SYSTEMROOT");
    const char* program_files = std::getenv("ProgramFiles");
    const char* program_files_x86 = std::getenv("ProgramFiles(x86)");
    auto same_path = [&lower](const char* value) {
        if (!value || !*value) return false;
        std::string candidate(value);
        std::replace(candidate.begin(), candidate.end(), '\\', '/');
        while (candidate.size() > 1 && candidate.back() == '/') candidate.pop_back();
        std::transform(candidate.begin(), candidate.end(), candidate.begin(), [](unsigned char c) {
            return static_cast<char>(std::tolower(c));
        });
        return lower == candidate;
    };
    if ((lower.size() == 2 && lower[1] == ':') || same_path(home) ||
        same_path(system_root) || same_path(program_files) || same_path(program_files_x86)) {
        reason = "filesystem, user, system, or program root";
        return true;
    }
#else
    const char* home = std::getenv("HOME");
    std::string home_path = home ? home : "";
    while (home_path.size() > 1 && home_path.back() == '/') home_path.pop_back();
    if (normalized == "/" || (!home_path.empty() && normalized == home_path)) {
        reason = "filesystem root or user home";
        return true;
    }
#endif
    return false;
}

static void ensure_default_workspace_roots() {
    if (!s_workspace_roots.empty()) return;

    const char* env_roots = std::getenv("SYNFIG_MCP_WORKSPACE_ROOTS");
    if (env_roots && *env_roots) {
        std::string s(env_roots);
        std::stringstream ss(s);
        std::string item;
#ifdef _WIN32
        char delim = ';';
#else
        char delim = ':';
#endif
        while (std::getline(ss, item, delim)) {
            if (!item.empty()) {
                std::string reason;
                if (!is_overly_broad_root(item, reason)) {
                    s_workspace_roots.push_back(normalize_path_str(item));
                }
            }
        }
    }

#ifdef _WIN32
    const char* home = std::getenv("USERPROFILE");
    if (home && *home) {
        std::string def_dir = std::string(home) + "\\Documents\\SynfigMCP";
        s_workspace_roots.push_back(normalize_path_str(def_dir));
    }
    char tmp[MAX_PATH];
    if (GetTempPathA(MAX_PATH, tmp)) {
        s_workspace_roots.push_back(normalize_path_str(tmp));
    }
#else
    const char* home = std::getenv("HOME");
    if (home && *home) {
        std::string def_dir = std::string(home) + "/Documents/SynfigMCP";
        s_workspace_roots.push_back(normalize_path_str(def_dir));
    }
    const char* tmp = std::getenv("TMPDIR");
    s_workspace_roots.push_back(normalize_path_str(tmp ? tmp : "/tmp"));
#endif
}

bool set_workspace_roots(const std::vector<std::string>& roots, std::string& error_msg) {
    std::vector<std::string> valid_roots;
    for (const auto& r : roots) {
        if (!r.empty()) {
            std::string reason;
            if (is_overly_broad_root(r, reason)) {
                error_msg = "Overly broad workspace root rejected: '" + r + "' (" + reason + ")";
                return false;
            }
            valid_roots.push_back(normalize_path_str(r));
        }
    }
    s_workspace_roots = valid_roots;
#ifdef _WIN32
    char tmp[MAX_PATH];
    if (GetTempPathA(MAX_PATH, tmp)) {
        s_workspace_roots.push_back(normalize_path_str(tmp));
    }
#else
    const char* tmp = std::getenv("TMPDIR");
    s_workspace_roots.push_back(normalize_path_str(tmp ? tmp : "/tmp"));
#endif
    return true;
}

void set_workspace_roots(const std::vector<std::string>& roots) {
    std::string err;
    set_workspace_roots(roots, err);
}

static bool is_safe_bridge_path(const std::string& path, const std::vector<std::string>& allowed_exts, std::string& out_err) {
    if (path.empty()) {
        out_err = "Security Sandbox Error: path cannot be empty";
        return false;
    }

    std::string path_for_checks = path;
    std::replace(path_for_checks.begin(), path_for_checks.end(), '\\', '/');
    std::stringstream parts(path_for_checks);
    std::string part;
    while (std::getline(parts, part, '/')) {
        if (part == "..") {
            out_err = "Security Sandbox Error: directory traversal is not permitted";
            return false;
        }
    }

    std::string lower_path = path_for_checks;
    std::transform(lower_path.begin(), lower_path.end(), lower_path.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    const auto dot = lower_path.find_last_of('.');
    const auto slash = lower_path.find_last_of('/');
    const std::string extension =
        dot != std::string::npos && (slash == std::string::npos || dot > slash)
            ? lower_path.substr(dot)
            : "";
    if (!allowed_exts.empty()) {
        bool allowed = false;
        for (const auto& candidate : allowed_exts) {
            if (extension == candidate) {
                allowed = true;
                break;
            }
        }
        if (!allowed) {
            out_err = "Security Sandbox Error: file extension is not permitted";
            return false;
        }
    }

    ensure_default_workspace_roots();
    const std::string canonical = normalize_path_str(path);
    for (const auto& root : s_workspace_roots) {
        if (is_within_root(canonical, root)) return true;
    }

    out_err = "Security Sandbox Error: path is outside configured workspace roots";
    return false;
}

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

        if (params.contains("workspace_roots") && params["workspace_roots"].is_array()) {
            std::vector<std::string> roots;
            for (const auto& r : params["workspace_roots"]) {
                if (r.is_string()) {
                    roots.push_back(r.get<std::string>());
                }
            }
            if (!roots.empty()) {
                std::string err_reason;
                if (!set_workspace_roots(roots, err_reason)) {
                    res["error"] = {
                        {"code", 1203},
                        {"message", err_reason}
                    };
                    return res;
                }
            }
        }

        res["result"] = {
            {"protocol_version", PROTOCOL_VERSION},
            {"studio_version", STUDIO_VERSION},
            {"bridge_version", get_build_version()},
            {"commit_sha", get_build_commit_sha()},
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

                synfig::Canvas::Handle canvas = inst->get_canvas();
                synfig::RendDesc desc = canvas->rend_desc();
                double fps = static_cast<double>(desc.get_frame_rate());
                double start_t = static_cast<double>(desc.get_time_start());
                double end_t = static_cast<double>(desc.get_time_end());

                nlohmann::json doc_item;
                doc_item["doc_id"] = "doc_" + std::to_string(idx);
                doc_item["id"] = "doc_" + std::to_string(idx);
                doc_item["name"] = canvas->get_name();
                doc_item["file_path"] = inst->get_file_name().empty() ? nullptr : nlohmann::json(inst->get_file_name());
                doc_item["width"] = desc.get_w();
                doc_item["height"] = desc.get_h();
                doc_item["fps"] = fps;
                doc_item["start_time"] = start_t;
                doc_item["end_time"] = end_t;
                doc_item["duration_frames"] = static_cast<int>((end_t - start_t) * fps);
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
        std::string path_err;
        if (!is_safe_bridge_path(file_path, {".sif", ".sifz", ".sfg"}, path_err)) {
            res["error"] = {{"code", 1203}, {"message", path_err}};
            return res;
        }
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
        if (!file_path.empty()) {
            std::string path_err;
            if (!is_safe_bridge_path(file_path, {".sif", ".sifz", ".sfg"}, path_err)) {
                res["error"] = {{"code", 1203}, {"message", path_err}};
                return res;
            }
        }
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

    if (method == "doc.set_time_range") {
        std::string doc_id = params.value("doc_id", "doc_0");

        return run_on_main_thread([&, doc_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: doc.set_time_range");

            synfig::RendDesc desc = inst->get_canvas()->rend_desc();
            if (params.contains("start_time")) {
                desc.set_time_start(synfig::Time(params["start_time"].get<double>()));
            } else if (params.contains("begin_time")) {
                desc.set_time_start(synfig::Time(params["begin_time"].get<double>()));
            }
            if (params.contains("end_time")) {
                desc.set_time_end(synfig::Time(params["end_time"].get<double>()));
            }
            if (params.contains("fps")) {
                desc.set_frame_rate(params["fps"].get<double>());
            }

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
                {"start_time", static_cast<double>(desc.get_time_start())},
                {"end_time", static_cast<double>(desc.get_time_end())},
                {"fps", static_cast<double>(desc.get_frame_rate())},
                {"diff", make_diff("doc.set_time_range", {}, {doc_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"start_time", params.value("start_time", 0.0)},
                {"end_time", params.value("end_time", 5.0)},
                {"fps", params.value("fps", 24.0)},
                {"diff", make_diff("doc.set_time_range", {}, {doc_id}, {})}
            };
            return r;
#endif
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
                {"name", inst->get_canvas()->get_name()},
                {"path", "/"}
            });

            for (auto it = inst->get_canvas()->children().begin(); it != inst->get_canvas()->children().end(); ++it) {
                if (*it) {
                    canvases.push_back({
                        {"canvas_id", (*it)->get_id()},
                        {"name", (*it)->get_name()},
                        {"path", "/" + (*it)->get_name()}
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

    if (method == "canvas.rename") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string canvas_id = params.value("canvas_id", params.value("id", ""));
        std::string new_name = params.value("name", "");

        return run_on_main_thread([&, doc_id, canvas_id, new_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }
            if (new_name.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing canvas name"}};
                return r;
            }
            synfig::Canvas::Handle target = find_canvas_by_id(inst->get_canvas(), canvas_id);
            if (!target) {
                r["error"] = {{"code", 2002}, {"message", "Canvas not found: " + canvas_id}};
                return r;
            }
            const synfig::String previous = target->get_name();
            target->set_name(new_name);
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"name", new_name},
                {"previous_name", previous},
                {"diff", make_diff("canvas.rename", {}, {canvas_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"name", new_name},
                {"diff", make_diff("canvas.rename", {}, {canvas_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "canvas.delete") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string canvas_id = params.value("canvas_id", params.value("id", ""));

        return run_on_main_thread([&, doc_id, canvas_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }
            synfig::Canvas::Handle root = inst->get_canvas();
            synfig::Canvas::Handle target = find_canvas_by_id(root, canvas_id);
            if (!target || target == root) {
                r["error"] = {{"code", 2002}, {"message", "Canvas not found: " + canvas_id}};
                return r;
            }
            root->remove_child_canvas(target);
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"diff", make_diff("canvas.delete", {}, {}, {canvas_id})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"diff", make_diff("canvas.delete", {}, {}, {canvas_id})}
            };
            return r;
#endif
        });
    }

    if (method == "canvas.set_properties") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string canvas_id = params.value("canvas_id", params.value("id", ""));

        return run_on_main_thread([&, doc_id, canvas_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }
            synfig::Canvas::Handle target = find_canvas_by_id(inst->get_canvas(), canvas_id);
            if (!target) {
                r["error"] = {{"code", 2002}, {"message", "Canvas not found: " + canvas_id}};
                return r;
            }
            synfig::RendDesc& desc = target->rend_desc();
            if (params.contains("width")) desc.set_w(params["width"].get<int>());
            if (params.contains("height")) desc.set_h(params["height"].get<int>());
            if (params.contains("fps")) desc.set_frame_rate(params["fps"].get<float>());
            if (params.contains("start_time")) desc.set_time_start(synfig::Time(params["start_time"].get<double>()));
            if (params.contains("end_time")) desc.set_time_end(synfig::Time(params["end_time"].get<double>()));
            if (params.contains("background_color")) {
                const nlohmann::json& c = params["background_color"];
                desc.set_bg_color(synfig::Color(
                    c.value("r", 0.5f), c.value("g", 0.5f),
                    c.value("b", 0.5f), c.value("a", 1.0f)));
            }
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"name", target->get_name()},
                {"width", desc.get_w()},
                {"height", desc.get_h()},
                {"fps", static_cast<double>(desc.get_frame_rate())},
                {"start_time", static_cast<double>(desc.get_time_start())},
                {"end_time", static_cast<double>(desc.get_time_end())},
                {"diff", make_diff("canvas.set_properties", {}, {canvas_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_id", canvas_id},
                {"diff", make_diff("canvas.set_properties", {}, {canvas_id}, {})}
            };
            return r;
#endif
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

            synfig::Canvas::Handle canvas = inst->get_canvas();
            synfig::RendDesc desc = canvas->rend_desc();
            double fps = static_cast<double>(desc.get_frame_rate());
            double start_t = static_cast<double>(desc.get_time_start());
            double end_t = static_cast<double>(desc.get_time_end());

            nlohmann::json tree = build_layer_tree(canvas);
            // The same metadata the headless engine reports, so the tool
            // response has the same shape in both backends.
            r["result"] = {
                {"doc_id", doc_id},
                {"canvas_path", "/"},
                {"name", canvas->get_name()},
                {"width", desc.get_w()},
                {"height", desc.get_h()},
                {"fps", fps},
                {"duration_frames", static_cast<int>((end_t - start_t) * fps)},
                {"layers", tree}
            };
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
                    if (!val.is_valid()) {
                        grouper.cancel();
                        r["error"] = {{"code", -32602}, {"message", "Invalid value for parameter: " + item.key()}};
                        return r;
                    }
                    ci->change_value(synfigapp::ValueDesc(layer, item.key()), val);
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

    if (method == "scene.build") {
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
            if (!ci) {
                r["error"] = {{"code", -32000}, {"message", "Canvas interface not found"}};
                return r;
            }

            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: scene.build");
            std::vector<std::string> created_ids;

            if (params.contains("layers") && params["layers"].is_array()) {
                for (auto& l_spec : params["layers"]) {
                    std::string l_type = l_spec.value("type", "circle");
                    std::string l_id = l_spec.value("id", "");
                    int depth = l_spec.value("depth", 0);

                    synfig::Layer::Handle layer = ci->add_layer_to(l_type, inst->get_canvas(), depth);
                    if (!layer) {
                        grouper.cancel();
                        r["error"] = {{"code", -32000}, {"message", "Failed to create layer of type: " + l_type}};
                        return r;
                    }
                    if (!l_id.empty()) {
                        layer->set_description(l_id);
                    }
                    created_ids.push_back(layer->get_description().empty() ? layer->get_guid().get_string() : layer->get_description());

                    if (l_spec.contains("params") && l_spec["params"].is_object()) {
                        for (auto& item : l_spec["params"].items()) {
                            synfig::ValueBase val = json_to_valuebase(item.value());
                            if (!val.is_valid()) {
                                grouper.cancel();
                                r["error"] = {{"code", -32602}, {"message", "Invalid value for parameter: " + item.key()}};
                                return r;
                            }
                            ci->change_value(synfigapp::ValueDesc(layer, item.key()), val);
                        }
                    }

                    // Waypoints keep the animation of the declarative spec.
                    if (l_spec.contains("waypoints") && l_spec["waypoints"].is_array()) {
                        for (auto& wp_spec : l_spec["waypoints"]) {
                            std::string param_name = wp_spec.value("param", "");
                            double wp_time = wp_spec.value("time", 0.0);
                            synfig::ValueBase wp_val = json_to_valuebase(wp_spec.value("value", nlohmann::json::object()));
                            if (!wp_val.is_valid()) {
                                grouper.cancel();
                                r["error"] = {{"code", -32602}, {"message", "Invalid waypoint value for parameter: " + param_name}};
                                return r;
                            }
                            std::string interp_str = wp_spec.value("interpolation", "");
                            if (!interp_str.empty()) {
                                synfigapp::Main::set_interpolation(parse_interpolation(interp_str));
                            }
                            synfigapp::Action::Handle wp_action = synfigapp::Action::create("ValueDescSet");
                            if (wp_action) {
                                wp_action->set_param("canvas", inst->get_canvas());
                                wp_action->set_param("canvas_interface", ci);
                                wp_action->set_param("time", synfig::Time(wp_time));
                                wp_action->set_param("value_desc", synfigapp::ValueDesc(layer, param_name));
                                wp_action->set_param("new_value", wp_val);
                                wp_action->set_param("animate", true);
                                inst->perform_action(wp_action);
                            }
                        }
                    }
                }
            }

            // Groups encapsulate the referenced layers into a PasteCanvas layer.
            if (params.contains("groups") && params["groups"].is_array()) {
                for (auto& g_spec : params["groups"]) {
                    std::string g_id = g_spec.value("id", "Group");
                    std::vector<std::string> g_layer_ids = g_spec.value("layer_ids", std::vector<std::string>());

                    synfigapp::Action::Handle group_action = synfigapp::Action::create("LayerEncapsulate");
                    if (group_action) {
                        group_action->set_param("canvas", inst->get_canvas());
                        group_action->set_param("canvas_interface", ci);
                        group_action->set_param("description", synfig::String(g_id));

                        bool any = false;
                        for (const auto& lid : g_layer_ids) {
                            synfig::Layer::Handle l = find_layer_in_canvas(inst->get_canvas(), lid);
                            if (l) {
                                group_action->set_param("layer", l);
                                any = true;
                            }
                        }
                        if (any) {
                            inst->perform_action(group_action);
                            created_ids.push_back(g_id);
                        }
                    }
                }
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"diff", make_diff("scene.build", created_ids, {}, {})}
            };
            return r;
        });
    }

    if (method == "layer.remove" || method == "layer.delete") {
        std::string doc_id = safe_extract_string(params, "doc_id", "doc_0");
        std::string layer_id = safe_extract_string(params, "layer_id", "");
        if (layer_id.empty()) {
            return make_input_error(req, 2002, "Layer ID cannot be empty or null.");
        }
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

    if (method == "param.list") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");

        return run_on_main_thread([&, doc_id, layer_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }
            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }
            nlohmann::json list = nlohmann::json::array();
            for (const auto& item : layer->get_param_list()) {
                if (!item.second.is_valid()) continue;
                nlohmann::json entry = nlohmann::json::object();
                entry["name"] = item.first;
                entry["value"] = valuebase_to_json(item.second);
                list.push_back(entry);
            }
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"params", list}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"params", nlohmann::json::array()}
            };
            return r;
#endif
        });
    }

    if (method == "anim.waypoint_list") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");

        return run_on_main_thread([&, doc_id, layer_id, param_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }
            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }
            synfig::ValueNode::Handle value_node;
            {
                const synfig::Layer::DynamicParamList& dynamic = layer->dynamic_param_list();
                auto it = dynamic.find(param_name);
                if (it != dynamic.end()) value_node = it->second;
            }
            synfig::ValueNode_Animated::Handle animated =
                synfig::ValueNode_Animated::Handle::cast_dynamic(value_node);
            nlohmann::json waypoints = nlohmann::json::array();
            if (animated) {
                for (const auto& wp : animated->waypoint_list()) {
                    nlohmann::json entry = nlohmann::json::object();
                    entry["time"] = static_cast<double>(wp.get_time());
                    entry["value"] = valuebase_to_json(wp.get_value());
                    entry["interpolation_in"] = interpolation_to_string(wp.get_before());
                    entry["interpolation_out"] = interpolation_to_string(wp.get_after());
                    waypoints.push_back(entry);
                }
            }
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"waypoints", waypoints}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"waypoints", nlohmann::json::array()}
            };
            return r;
#endif
        });
    }

    if (method == "rig.bone_add") {
        std::string doc_id = safe_extract_string(params, "doc_id", "doc_0");
        std::string layer_id = safe_extract_string(params, "layer_id", safe_extract_string(params, "skeleton_layer", ""));
        double bone_time = params.value("time", 0.0);
        double origin_x = params.value("origin_x", 0.0);
        double origin_y = params.value("origin_y", 0.0);
        double bone_angle = params.value("angle", 0.0);
        double bone_width = params.value("width", 1.0);
        double tip_width = params.value("tipwidth", 1.0);
        int parent_index = params.value("parent_index", -1);

        if (layer_id.empty()) {
            return make_input_error(req, 2002, "Layer ID cannot be empty or null.");
        }

        return run_on_main_thread([&, doc_id, layer_id, bone_time, origin_x, origin_y, bone_angle,
                                   bone_width, tip_width, parent_index]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
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
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: rig.bone_add");

            // The bones of a skeleton layer live in a static list value node.
            synfigapp::ValueDesc list_desc(layer, "bones");
            synfig::ValueNode_StaticList::Handle list_node =
                synfig::ValueNode_StaticList::Handle::cast_dynamic(list_desc.get_value_node());
            if (!list_node) {
                grouper.cancel();
                r["error"] = {{"code", 2003}, {"message", "The layer has no bone list - use a skeleton or skeleton_deformation layer"}};
                return r;
            }

            synfig::Bone bone;
            bone.set_origin(synfig::Point(origin_x, origin_y));
            bone.set_width(static_cast<float>(bone_width));
            bone.set_tipwidth(static_cast<float>(tip_width));
            bone.set_angle(synfig::Angle::deg(bone_angle));
            bone.set_scalelx(synfig::Real(1.0));

            synfigapp::Action::Handle action;
            synfig::ValueNode_Bone::Handle bone_node;

            if (parent_index < 0) {
                // Root bone: inserted into the bone list itself.
                bone.set_parent(synfig::ValueNode_Bone_Root::create(synfig::Bone()));
                bone_node = synfig::ValueNode_Bone::create(bone, inst->get_canvas());

                action = synfigapp::Action::create("ValueNodeStaticListInsert");
                if (!action) {
                    grouper.cancel();
                    r["error"] = {{"code", -32000}, {"message", "Failed to create ValueNodeStaticListInsert action"}};
                    return r;
                }
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("time", synfig::Time(bone_time));
                action->set_param("item", synfig::ValueNode::Handle::cast_dynamic(bone_node));
                action->set_param("value_desc", synfigapp::ValueDesc(list_node, 0, list_desc));
            } else {
                // Child bone: created below an existing bone.
                if (parent_index >= static_cast<int>(list_node->list.size())) {
                    grouper.cancel();
                    r["error"] = {{"code", 2004}, {"message", "Parent bone index out of range"}};
                    return r;
                }
                synfig::ValueNode_Bone::Handle parent_bone =
                    synfig::ValueNode_Bone::Handle::cast_dynamic(list_node->list[parent_index]);
                if (!parent_bone) {
                    grouper.cancel();
                    r["error"] = {{"code", 2004}, {"message", "The parent index does not point at a bone"}};
                    return r;
                }
                synfigapp::ValueDesc parent_desc(list_node, parent_index, list_desc);
                synfigapp::ValueDesc child_desc(
                    parent_bone,
                    parent_bone->get_link_index_from_name("origin"),
                    parent_desc);

                action = synfigapp::Action::create("ValueDescCreateChildBone");
                if (!action) {
                    grouper.cancel();
                    r["error"] = {{"code", -32000}, {"message", "Failed to create ValueDescCreateChildBone action"}};
                    return r;
                }
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("value_desc", child_desc);
                action->set_param("time", synfig::Time(bone_time));
                action->set_param("origin", synfig::ValueBase(synfig::Point(origin_x, origin_y)));
                action->set_param("scalelx", synfig::ValueBase(synfig::Real(1.0)));
                action->set_param("angle", synfig::ValueBase(synfig::Angle::deg(bone_angle)));
                action->set_param("parent", true);
                action->set_param("width", synfig::ValueBase(synfig::Real(bone_width)));
                action->set_param("tipwidth", synfig::ValueBase(synfig::Real(tip_width)));
                action->set_param("highlight", false);
                action->set_param("prev_active_bone_node", synfig::ValueNode::Handle());
            }

            if (!action->is_ready()) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "The bone action is not ready - is the layer a skeleton?"}};
                return r;
            }

            if (!inst->perform_action(action)) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "The bone action failed"}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"time", bone_time},
                {"origin", nlohmann::json::array({origin_x, origin_y})},
                {"angle", bone_angle},
                {"width", bone_width},
                {"tipwidth", tip_width},
                {"parent_index", parent_index},
                {"diff", make_diff("rig.bone_add", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"diff", make_diff("rig.bone_add", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    // --- 5. PARAMETER METHODS ---
    if (method == "schema.list_layers") {
        // Truthful introspection: enumerate the live Synfig layer factory
        // registry instead of a hardcoded list.  Each entry instantiates the
        // factory once to read its real parameter vocabulary and defaults.
        nlohmann::json r;
        r["jsonrpc"] = "2.0";
        if (req.contains("id")) {
            r["id"] = req["id"];
        }

        nlohmann::json layers = nlohmann::json::array();
        const synfig::Layer::Book& book = synfig::Layer::book();
        for (synfig::Layer::Book::const_iterator it = book.begin(); it != book.end(); ++it) {
            const synfig::Layer::BookEntry& entry = it->second;

            nlohmann::json item;
            item["name"] = entry.name.c_str();
            item["local_name"] = entry.local_name.c_str();
            item["category"] = entry.category.c_str();
            item["version"] = entry.version.c_str();

            nlohmann::json params_json = nlohmann::json::object();
            try {
                synfig::Layer::Handle instance(entry.factory());
                if (instance) {
                    const synfig::Layer::Vocab& vocab = instance->get_param_vocab();
                    for (synfig::Layer::Vocab::const_iterator p = vocab.begin(); p != vocab.end(); ++p) {
                        nlohmann::json pj;
                        synfig::ValueBase def = instance->get_param(p->get_name());
                        pj["type"] = def.is_valid() ? def.type_name().c_str() : "unknown";
                        pj["local_name"] = p->get_local_name().c_str();
                        pj["description"] = p->get_description().c_str();
                        pj["hint"] = p->get_hint().c_str();
                        pj["origin"] = p->get_origin().c_str();
                        pj["critical"] = p->get_critical();
                        pj["hidden"] = p->get_hidden();
                        // Synfig has no runtime read-only flag on ParamDesc
                        // (read_only() is a stub upstream); hidden parameters
                        // are the only ones the GUI never exposes for writing.
                        pj["writable"] = !p->get_hidden();
                        pj["animatable"] = !p->get_static();
                        pj["enum"] = nlohmann::json::array();
                        const std::list<synfig::ParamDesc::EnumData>& enums = p->get_enum_list();
                        for (std::list<synfig::ParamDesc::EnumData>::const_iterator e = enums.begin();
                             e != enums.end(); ++e) {
                            nlohmann::json ev;
                            ev["value"] = e->value;
                            ev["name"] = e->name.c_str();
                            ev["local_name"] = e->local_name.c_str();
                            pj["enum"].push_back(ev);
                        }
                        if (def.is_valid()) {
                            pj["default"] = valuebase_to_json(def);
                        }
                        params_json[p->get_name().c_str()] = pj;
                    }
                }
            } catch (...) {
                item["params"] = params_json;
                item["error"] = "factory instantiation failed";
                layers.push_back(item);
                continue;
            }

            item["params"] = params_json;
            item["param_count"] = params_json.size();
            layers.push_back(item);
        }

        r["result"] = {
            {"count", layers.size()},
            {"layers", layers}
        };
        return r;
    }

    if (method == "param.get") {
        std::string doc_id = safe_extract_string(params, "doc_id", "doc_0");
        std::string layer_id = safe_extract_string(params, "layer_id", "");
        std::string param_name = safe_extract_string(params, "param_name", "");

        nlohmann::json early;
        if (reject_empty_identifiers(req, layer_id, param_name, early)) {
            return early;
        }

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

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfig::Time cur_time = ci ? ci->get_time() : synfig::Time(0);
            synfigapp::ValueDesc vd(layer, param_name);
            synfig::ValueBase val = vd.get_value(cur_time);
            if (!val.is_valid()) {
                val = layer->get_param(param_name);
            }
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
        std::string doc_id = safe_extract_string(params, "doc_id", "doc_0");
        std::string layer_id = safe_extract_string(params, "layer_id", "");
        std::string param_name = safe_extract_string(params, "param_name", "");
        nlohmann::json val_json = params.contains("value") && !params["value"].is_null() ? params["value"] : nlohmann::json::object();

        nlohmann::json early;
        if (reject_empty_identifiers(req, layer_id, param_name, early)) {
            return early;
        }

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

    if (method == "param.convert") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        std::string type = params.value("type", "");

        return run_on_main_thread([&, doc_id, layer_id, param_name, type]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            if (type.empty() || !synfig::ValueNodeRegistry::book().count(type)) {
                r["error"] = {{"code", -32602}, {"message", "Unsupported ValueNode conversion type: " + type}};
                return r;
            }

            synfigapp::ValueDesc vd(layer, param_name);
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: param.convert");

            synfigapp::Action::Handle action = synfigapp::Action::create("ValueDescConvert");
            if (!action) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create ValueDescConvert action"}};
                return r;
            }

            synfig::Time cur_time = ci ? ci->get_time() : synfig::Time(0);
            action->set_param("canvas", inst->get_canvas());
            action->set_param("canvas_interface", ci);
            action->set_param("value_desc", vd);
            action->set_param("type", type);
            action->set_param("time", cur_time);

            try {
                if (!inst->perform_action(action)) {
                    grouper.cancel();
                    r["error"] = {{"code", -32000}, {"message", "ValueDescConvert action rejected for parameter: " + param_name + " to " + type}};
                    return r;
                }
            } catch (const std::exception& e) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", std::string("ValueDescConvert failed: ") + e.what()}};
                return r;
            } catch (...) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "ValueDescConvert failed with unknown exception"}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"type", type},
                {"diff", make_diff("param.convert", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"type", type},
                {"diff", make_diff("param.convert", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "param.export") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        std::string export_name = params.value("name", "");

        return run_on_main_thread([&, doc_id, layer_id, param_name, export_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            if (export_name.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing export name"}};
                return r;
            }

            synfigapp::ValueDesc vd(layer, param_name);
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: param.export");

            synfigapp::Action::Handle action = synfigapp::Action::create("ValueDescExport");
            if (!action) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create ValueDescExport action"}};
                return r;
            }

            action->set_param("canvas", inst->get_canvas());
            action->set_param("canvas_interface", ci);
            action->set_param("value_desc", vd);
            action->set_param("name", export_name);

            if (!inst->perform_action(action)) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "ValueDescExport action failed for name: " + export_name}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"name", export_name},
                {"diff", make_diff("param.export", {export_name}, {}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"name", export_name},
                {"diff", make_diff("param.export", {export_name}, {}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "param.link") {
        std::string doc_id = safe_extract_string(params, "doc_id", "doc_0");
        std::string layer_id = safe_extract_string(params, "layer_id", "");
        std::string param_name = safe_extract_string(params, "param_name", "");
        std::string link_id = safe_extract_string(params, "link_id", safe_extract_string(params, "name", ""));

        nlohmann::json early;
        if (reject_empty_identifiers(req, layer_id, param_name, early)) {
            return early;
        }
        if (link_id.empty()) {
            return make_input_error(req, 2004, "Value node ID cannot be empty or null.");
        }

        return run_on_main_thread([&, doc_id, layer_id, param_name, link_id]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            if (link_id.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing value node id"}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            if (!layer->get_param(param_name).is_valid()) {
                r["error"] = {{"code", 2003}, {"message", "Parameter not found: " + param_name}};
                return r;
            }

            synfig::ValueNode::Handle value_node = inst->get_canvas()->find_value_node(link_id, true);
            if (!value_node) {
                r["error"] = {{"code", 2004}, {"message", "Value node not found: " + link_id}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: param.link");

            synfigapp::Action::Handle action = synfigapp::Action::create("LayerParamConnect");
            if (!action) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create LayerParamConnect action"}};
                return r;
            }

            action->set_param("canvas", inst->get_canvas());
            action->set_param("canvas_interface", ci);
            action->set_param("layer", layer);
            action->set_param("param", param_name);
            action->set_param("value_node", value_node);

            if (!inst->perform_action(action)) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "LayerParamConnect failed for parameter: " + param_name}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"link_id", link_id},
                {"diff", make_diff("param.link", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"link_id", link_id},
                {"diff", make_diff("param.link", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "param.unexport") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string export_name = params.value("name", "");

        return run_on_main_thread([&, doc_id, export_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            if (export_name.empty()) {
                r["error"] = {{"code", -32602}, {"message", "Missing export name"}};
                return r;
            }

            synfig::ValueNode::Handle vn = inst->get_canvas()->find_value_node(export_name, true);
            if (!vn) {
                r["error"] = {{"code", 2002}, {"message", "Exported ValueNode not found: " + export_name}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: param.unexport");

            synfigapp::Action::Handle action = synfigapp::Action::create("ValueNodeRemove");
            if (!action) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create ValueNodeRemove action"}};
                return r;
            }

            action->set_param("canvas", inst->get_canvas());
            action->set_param("canvas_interface", ci);
            action->set_param("value_node", vn);

            if (!inst->perform_action(action)) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "ValueNodeRemove action failed for name: " + export_name}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"name", export_name},
                {"diff", make_diff("param.unexport", {}, {}, {export_name})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"name", export_name},
                {"diff", make_diff("param.unexport", {}, {}, {export_name})}
            };
            return r;
#endif
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
                ci->set_time(t);
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
            const double fps = static_cast<double>(inst->get_canvas()->rend_desc().get_frame_rate());
            for (const auto& kf : inst->get_canvas()->keyframe_list()) {
                nlohmann::json kf_obj;
                kf_obj["time"] = static_cast<double>(kf.get_time());
                // The same time spelling the headless engine reports.
                kf_obj["time_string"] = kf.get_time().get_string(fps);
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

    if (method == "anim.waypoint_set" || method == "waypoint.set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        double t_sec = params.value("time", 0.0);
        nlohmann::json val_json = params.value("value", nlohmann::json::object());
        std::string interp_before_str = params.value("interpolation_in", params.value("interpolation", ""));
        std::string interp_after_str = params.value("interpolation_out", params.value("interpolation", ""));

        return run_on_main_thread([&, doc_id, layer_id, param_name, t_sec, val_json, interp_before_str, interp_after_str]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
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
            if (!val.is_valid()) {
                r["error"] = {{"code", -32602}, {"message", "Invalid value for waypoint: " + param_name}};
                return r;
            }

            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.waypoint_set");

            if (!interp_after_str.empty()) {
                synfigapp::Main::set_interpolation(parse_interpolation(interp_after_str));
            }

            synfigapp::ValueDesc vd(layer, param_name);
            synfigapp::Action::Handle action = synfigapp::Action::create("ValueDescSet");
            if (action) {
                action->set_param("canvas", inst->get_canvas());
                action->set_param("canvas_interface", ci);
                action->set_param("time", synfig::Time(t_sec));
                action->set_param("value_desc", vd);
                action->set_param("new_value", val);
                action->set_param("animate", true);
                inst->perform_action(action);
            }

            if (!interp_before_str.empty() || !interp_after_str.empty()) {
                synfigapp::ValueDesc updated_vd(layer, param_name);
                if (updated_vd.is_value_node()) {
                    synfig::ValueNode_Animated::Handle animated =
                        synfig::ValueNode_Animated::Handle::cast_dynamic(updated_vd.get_value_node());
                    if (animated) {
                        try {
                            auto it = animated->find(synfig::Time(t_sec));
                            if (it != animated->waypoint_list().end()) {
                                synfig::Waypoint wp = *it;
                                if (!interp_before_str.empty()) wp.set_before(parse_interpolation(interp_before_str));
                                if (!interp_after_str.empty()) wp.set_after(parse_interpolation(interp_after_str));
                                synfigapp::Action::Handle wp_action = synfigapp::Action::create("WaypointSet");
                                if (wp_action) {
                                    wp_action->set_param("canvas", inst->get_canvas());
                                    wp_action->set_param("canvas_interface", ci);
                                    wp_action->set_param("value_node", synfig::ValueNode::Handle(animated));
                                    wp_action->set_param("waypoint", wp);
                                    inst->perform_action(wp_action);
                                }
                            }
                        } catch (...) {}
                    }
                }
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"time", t_sec},
                {"value", val_json},
                {"interpolation_in", interp_before_str.empty() ? "tcb" : interp_before_str},
                {"interpolation_out", interp_after_str.empty() ? "tcb" : interp_after_str},
                {"diff", make_diff("anim.waypoint_set", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"time", t_sec},
                {"value", val_json},
                {"interpolation_in", interp_before_str.empty() ? "tcb" : interp_before_str},
                {"interpolation_out", interp_after_str.empty() ? "tcb" : interp_after_str},
                {"diff", make_diff("anim.waypoint_set", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "anim.waypoint_remove" || method == "waypoint.remove" || method == "waypoint.delete") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        double t_sec = params.value("time", 0.0);

        return run_on_main_thread([&, doc_id, layer_id, param_name, t_sec]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
            if (!layer) {
                r["error"] = {{"code", 2002}, {"message", "Layer not found: " + layer_id}};
                return r;
            }

            synfigapp::ValueDesc vd(layer, param_name);
            if (!vd.is_value_node()) {
                r["error"] = {{"code", 2003}, {"message", "Parameter is not animated: " + param_name}};
                return r;
            }

            synfig::ValueNode_Animated::Handle animated =
                synfig::ValueNode_Animated::Handle::cast_dynamic(vd.get_value_node());
            if (!animated) {
                r["error"] = {{"code", 2003}, {"message", "Parameter is not animated: " + param_name}};
                return r;
            }

            synfig::ValueNode_Animated::WaypointList::iterator iter;
            try {
                iter = animated->find(synfig::Time(t_sec));
            } catch (...) {
                r["error"] = {{"code", 2002}, {"message", "Waypoint not found at time: " + std::to_string(t_sec)}};
                return r;
            }

            if (iter == animated->waypoint_list().end()) {
                r["error"] = {{"code", 2002}, {"message", "Waypoint not found at time: " + std::to_string(t_sec)}};
                return r;
            }

            synfig::Waypoint wp = *iter;
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.waypoint_remove");

            synfigapp::Action::Handle action = synfigapp::Action::create("WaypointRemove");
            if (!action) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "Failed to create WaypointRemove action"}};
                return r;
            }

            action->set_param("canvas", inst->get_canvas());
            action->set_param("canvas_interface", ci);
            action->set_param("value_node", synfig::ValueNode::Handle(animated));
            action->set_param("waypoint", wp);

            if (!inst->perform_action(action)) {
                grouper.cancel();
                r["error"] = {{"code", -32000}, {"message", "WaypointRemove action failed"}};
                return r;
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"time", t_sec},
                {"diff", make_diff("anim.waypoint_remove", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"time", t_sec},
                {"diff", make_diff("anim.waypoint_remove", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "anim.animate_param") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");
        nlohmann::json waypoints = params.value("waypoints", nlohmann::json::array());

        return run_on_main_thread([&, doc_id, layer_id, param_name, waypoints]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
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
            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.animate_param");

            for (const auto& wp_json : waypoints) {
                double t = wp_json.value("time", 0.0);
                synfig::ValueBase val = json_to_valuebase(wp_json.value("value", nlohmann::json::object()));
                if (!val.is_valid()) continue;

                std::string interp_in = wp_json.value("interpolation_in", wp_json.value("interpolation", ""));
                std::string interp_out = wp_json.value("interpolation_out", wp_json.value("interpolation", ""));
                if (!interp_out.empty()) {
                    synfigapp::Main::set_interpolation(parse_interpolation(interp_out));
                }

                synfigapp::ValueDesc vd(layer, param_name);
                synfigapp::Action::Handle action = synfigapp::Action::create("ValueDescSet");
                if (action) {
                    action->set_param("canvas", inst->get_canvas());
                    action->set_param("canvas_interface", ci);
                    action->set_param("time", synfig::Time(t));
                    action->set_param("value_desc", vd);
                    action->set_param("new_value", val);
                    action->set_param("animate", true);
                    inst->perform_action(action);
                }

                if (!interp_in.empty() || !interp_out.empty()) {
                    synfigapp::ValueDesc updated_vd(layer, param_name);
                    if (updated_vd.is_value_node()) {
                        synfig::ValueNode_Animated::Handle animated =
                            synfig::ValueNode_Animated::Handle::cast_dynamic(updated_vd.get_value_node());
                        if (animated) {
                            try {
                                auto it = animated->find(synfig::Time(t));
                                if (it != animated->waypoint_list().end()) {
                                    if (!interp_in.empty()) it->set_before(parse_interpolation(interp_in));
                                    if (!interp_out.empty()) it->set_after(parse_interpolation(interp_out));
                                    synfigapp::Action::Handle wp_action = synfigapp::Action::create("WaypointSet");
                                    if (wp_action) {
                                        wp_action->set_param("canvas", inst->get_canvas());
                                        wp_action->set_param("canvas_interface", ci);
                                        wp_action->set_param("value_node", synfig::ValueNode::Handle(animated));
                                        wp_action->set_param("waypoint", *it);
                                        inst->perform_action(wp_action);
                                    }
                                }
                            } catch (...) {}
                        }
                    }
                }
            }

            grouper.finish();

            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"waypoint_count", static_cast<int>(waypoints.size())},
                {"diff", make_diff("anim.animate_param", {}, {layer_id}, {})}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"layer_id", layer_id},
                {"param_name", param_name},
                {"waypoint_count", static_cast<int>(waypoints.size())},
                {"diff", make_diff("anim.animate_param", {}, {layer_id}, {})}
            };
            return r;
#endif
        });
    }

    if (method == "anim.interpolation_set") {
        std::string doc_id = params.value("doc_id", "doc_0");
        std::string interp_str = params.value("interpolation", "tcb");
        std::string layer_id = params.value("layer_id", "");
        std::string param_name = params.value("param_name", "");

        return run_on_main_thread([&, doc_id, interp_str, layer_id, param_name]() -> nlohmann::json {
            nlohmann::json r;
            r["jsonrpc"] = "2.0";
            r["id"] = req["id"];

            etl::handle<studio::Instance> inst = resolve_instance(doc_id);
#ifndef MCP_BRIDGE_STANDALONE
            if (!inst || !inst->get_canvas()) {
                r["error"] = {{"code", 2001}, {"message", "Document not found: " + doc_id}};
                return r;
            }

            synfig::Interpolation interp = parse_interpolation(interp_str);
            etl::handle<synfigapp::CanvasInterface> ci = inst->find_canvas_interface(inst->get_canvas());

            if (layer_id.empty() || param_name.empty()) {
                synfigapp::Main::set_interpolation(interp);
            } else {
                synfig::Layer::Handle layer = find_layer_in_canvas(inst->get_canvas(), layer_id);
                if (layer) {
                    synfigapp::ValueDesc vd(layer, param_name);
                    if (vd.is_value_node()) {
                        synfig::ValueNode_Animated::Handle animated =
                            synfig::ValueNode_Animated::Handle::cast_dynamic(vd.get_value_node());
                        if (animated) {
                            synfigapp::Action::PassiveGrouper grouper(inst.get(), "mcp: anim.interpolation_set");
                            for (auto it = animated->waypoint_list().begin(); it != animated->waypoint_list().end(); ++it) {
                                synfig::Waypoint wp = *it;
                                wp.set_before(interp);
                                wp.set_after(interp);
                                synfigapp::Action::Handle wp_action = synfigapp::Action::create("WaypointSet");
                                if (wp_action) {
                                    wp_action->set_param("canvas", inst->get_canvas());
                                    wp_action->set_param("canvas_interface", ci);
                                    wp_action->set_param("value_node", synfig::ValueNode::Handle(animated));
                                    wp_action->set_param("waypoint", wp);
                                    inst->perform_action(wp_action);
                                }
                            }
                            grouper.finish();
                        }
                    }
                }
            }

            r["result"] = {
                {"doc_id", doc_id},
                {"interpolation", interp_str}
            };
            return r;
#else
            r["result"] = {
                {"doc_id", doc_id},
                {"interpolation", interp_str}
            };
            return r;
#endif
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

        std::string path_err;
        if (!is_safe_bridge_path(output_path, {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".tga"}, path_err)) {
            res["error"] = {{"code", 1203}, {"message", path_err}};
            return res;
        }

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
