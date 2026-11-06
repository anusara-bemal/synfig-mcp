#ifndef MCP_BRIDGE_TYPES_SERIALIZER_H
#define MCP_BRIDGE_TYPES_SERIALIZER_H

#include <string>
#include <nlohmann/json.hpp>

#ifndef MCP_BRIDGE_STANDALONE
#include <synfig/value.h>
#include <synfig/types.h>
#include <synfig/color.h>
#include <synfig/vector.h>
#include <synfig/angle.h>
#include <synfig/time.h>
#include <synfig/gradient.h>
#include <synfig/blinepoint.h>
#include <synfig/canvas.h>
#endif

namespace mcp_bridge {

#ifndef MCP_BRIDGE_STANDALONE
/**
 * Serialize a synfig::ValueBase into a JSON tagged union according to protocol/schema/types.json.
 */
nlohmann::json valuebase_to_json(const synfig::ValueBase& val);

/**
 * Deserialize a JSON tagged union into a synfig::ValueBase.
 */
synfig::ValueBase json_to_valuebase(const nlohmann::json& j);
#endif

/**
 * Coordinate conversions between Synfig units and screen pixels.
 * Synfig coordinates: Center (0, 0), +Y is Up.
 * Screen pixels: Top-left (0, 0), +Y is Down.
 */
struct Point2D {
    double x;
    double y;
};

Point2D synfig_to_pixel(double sx, double sy, int width, int height, double ppu = 60.0);
Point2D pixel_to_synfig(double px, double py, int width, int height, double ppu = 60.0);

} // namespace mcp_bridge

#endif // MCP_BRIDGE_TYPES_SERIALIZER_H
