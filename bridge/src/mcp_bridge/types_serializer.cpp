#include "types_serializer.h"
#include <iostream>

namespace mcp_bridge {

#ifndef MCP_BRIDGE_STANDALONE
nlohmann::json valuebase_to_json(const synfig::ValueBase& val) {
    nlohmann::json j;
    if (!val.is_valid()) {
        j["type"] = "nil";
        j["value"] = nullptr;
        return j;
    }

    std::string type_name = val.get_type().description.name;

    if (type_name == "bool") {
        j["type"] = "bool";
        j["value"] = val.get(bool());
    } else if (type_name == "integer") {
        j["type"] = "integer";
        j["value"] = val.get(int());
    } else if (type_name == "real") {
        j["type"] = "real";
        j["value"] = static_cast<double>(val.get(synfig::Real()));
    } else if (type_name == "string") {
        j["type"] = "string";
        j["value"] = static_cast<std::string>(val.get(synfig::String()));
    } else if (type_name == "time") {
        synfig::Time t = val.get(synfig::Time());
        j["type"] = "time";
        nlohmann::json t_obj = nlohmann::json::object();
        t_obj["seconds"] = static_cast<double>(t);
        t_obj["string"] = t.get_string();
        j["value"] = t_obj;
    } else if (type_name == "angle") {
        synfig::Angle a = val.get(synfig::Angle());
        j["type"] = "angle";
        nlohmann::json a_obj = nlohmann::json::object();
        a_obj["degrees"] = static_cast<double>(synfig::Angle::deg(a).get());
        a_obj["radians"] = static_cast<double>(synfig::Angle::rad(a).get());
        j["value"] = a_obj;
    } else if (type_name == "vector") {
        synfig::Vector v = val.get(synfig::Vector());
        j["type"] = "vector";
        nlohmann::json v_obj = nlohmann::json::object();
        v_obj["x"] = static_cast<double>(v[0]);
        v_obj["y"] = static_cast<double>(v[1]);
        j["value"] = v_obj;
    } else if (type_name == "color") {
        synfig::Color c = val.get(synfig::Color());
        j["type"] = "color";
        nlohmann::json c_obj = nlohmann::json::object();
        c_obj["r"] = static_cast<double>(c.get_r());
        c_obj["g"] = static_cast<double>(c.get_g());
        c_obj["b"] = static_cast<double>(c.get_b());
        c_obj["a"] = static_cast<double>(c.get_a());
        j["value"] = c_obj;
    } else if (type_name == "gradient") {
        synfig::Gradient g = val.get(synfig::Gradient());
        nlohmann::json stops = nlohmann::json::array();
        for (synfig::Gradient::const_iterator it = g.begin(); it != g.end(); ++it) {
            nlohmann::json stop_obj = nlohmann::json::object();
            stop_obj["pos"] = static_cast<double>(it->pos);

            nlohmann::json c_obj = nlohmann::json::object();
            c_obj["r"] = static_cast<double>(it->color.get_r());
            c_obj["g"] = static_cast<double>(it->color.get_g());
            c_obj["b"] = static_cast<double>(it->color.get_b());
            c_obj["a"] = static_cast<double>(it->color.get_a());

            stop_obj["color"] = c_obj;
            stops.push_back(stop_obj);
        }
        j["type"] = "gradient";
        // The documented wire format (docs/protocol.md) uses "cpoints"; the
        // Python SynfigValue model expects the same key.
        j["cpoints"] = stops;
    } else if (type_name == "bline_point") {
        synfig::BLinePoint bp = val.get(synfig::BLinePoint());
        // The documented wire format (and the Python model) describe splines as
        // a list of points, so a single point is sent as a one element list.
        j["type"] = "bline_point_list";

        nlohmann::json bp_obj = nlohmann::json::object();

        nlohmann::json pt = nlohmann::json::object();
        pt["x"] = static_cast<double>(bp.get_vertex()[0]);
        pt["y"] = static_cast<double>(bp.get_vertex()[1]);
        bp_obj["vertex"] = pt;

        bp_obj["width"] = static_cast<double>(bp.get_width());
        bp_obj["origin"] = static_cast<double>(bp.get_origin());
        bp_obj["split_tangent_radius"] = bp.get_split_tangent_radius();
        bp_obj["split_tangent_angle"] = bp.get_split_tangent_angle();

        nlohmann::json t1 = nlohmann::json::object();
        t1["x"] = static_cast<double>(bp.get_tangent1()[0]);
        t1["y"] = static_cast<double>(bp.get_tangent1()[1]);
        bp_obj["t1"] = t1;

        nlohmann::json t2 = nlohmann::json::object();
        t2["x"] = static_cast<double>(bp.get_tangent2()[0]);
        t2["y"] = static_cast<double>(bp.get_tangent2()[1]);
        bp_obj["t2"] = t2;

        nlohmann::json points = nlohmann::json::array();
        points.push_back(bp_obj);
        j["points"] = points;
    } else if (type_name == "canvas") {
        synfig::Canvas::LooseHandle c = val.get(synfig::Canvas::LooseHandle());
        // The documented wire format calls this "canvas_ref" and carries the
        // id at the top level.
        j["type"] = "canvas_ref";
        j["canvas_id"] = c ? c->get_id() : "";
    } else {
        j["type"] = type_name;
        j["value"] = val.get_string();
    }

    return j;
}

synfig::ValueBase json_to_valuebase(const nlohmann::json& j) {
    if (!j.is_object() || !j.contains("type")) {
        return synfig::ValueBase();
    }

    std::string type_name = j["type"].get<std::string>();
    const nlohmann::json& val = j.contains("value") ? j["value"] : j;

    if (type_name == "bool" && val.is_boolean()) {
        return synfig::ValueBase(val.get<bool>());
    } else if (type_name == "integer" && val.is_number_integer()) {
        return synfig::ValueBase(val.get<int>());
    } else if (type_name == "real" && val.is_number()) {
        return synfig::ValueBase(static_cast<synfig::Real>(val.get<double>()));
    } else if (type_name == "string" && val.is_string()) {
        return synfig::ValueBase(synfig::String(val.get<std::string>()));
    } else if (type_name == "vector" && val.is_object()) {
        double x = val.value("x", 0.0);
        double y = val.value("y", 0.0);
        return synfig::ValueBase(synfig::Vector(x, y));
    } else if (type_name == "color" && val.is_object()) {
        float r = val.value("r", 0.0f);
        float g = val.value("g", 0.0f);
        float b = val.value("b", 0.0f);
        float a = val.value("a", 1.0f);
        return synfig::ValueBase(synfig::Color(r, g, b, a));
    } else if (type_name == "angle" && val.is_object()) {
        if (val.contains("degrees")) {
            return synfig::ValueBase(synfig::Angle::deg(val["degrees"].get<double>()));
        } else if (val.contains("radians")) {
            return synfig::ValueBase(synfig::Angle::rad(val["radians"].get<double>()));
        }
    } else if (type_name == "time" && val.is_object()) {
        double sec = val.value("seconds", 0.0);
        return synfig::ValueBase(synfig::Time(sec));
    } else if (type_name == "gradient") {
        // Accept the documented "cpoints" spelling as well as the older
        // "value" array so both directions of the wire format work.
        const nlohmann::json* stops = nullptr;
        if (j.contains("cpoints") && j["cpoints"].is_array()) {
            stops = &j["cpoints"];
        } else if (val.is_array()) {
            stops = &val;
        }
        if (!stops) {
            return synfig::ValueBase();
        }
        synfig::Gradient gradient;
        for (nlohmann::json::const_iterator it = stops->begin(); it != stops->end(); ++it) {
            if (!it->is_object()) continue;
            double pos = it->value("pos", 0.0);
            const nlohmann::json& c = it->contains("color") ? (*it)["color"] : nlohmann::json::object();
            float r = c.value("r", 0.0f);
            float g = c.value("g", 0.0f);
            float b = c.value("b", 0.0f);
            float a = c.value("a", 1.0f);
            gradient.push_back(synfig::Gradient::CPoint(
                static_cast<synfig::Real>(pos),
                synfig::Color(r, g, b, a)));
        }
        gradient.sort();
        return synfig::ValueBase(gradient);
    }

    return synfig::ValueBase();
}
#endif

Point2D synfig_to_pixel(double sx, double sy, int width, int height, double ppu) {
    Point2D pt;
    pt.x = (width / 2.0) + (sx * ppu);
    pt.y = (height / 2.0) - (sy * ppu);
    return pt;
}

Point2D pixel_to_synfig(double px, double py, int width, int height, double ppu) {
    Point2D pt;
    pt.x = (px - (width / 2.0)) / ppu;
    pt.y = ((height / 2.0) - py) / ppu;
    return pt;
}

} // namespace mcp_bridge
