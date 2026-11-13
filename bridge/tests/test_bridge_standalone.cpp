#include <iostream>
#include <cassert>
#include <cmath>

#define MCP_BRIDGE_STANDALONE 1
#include "../src/mcp_bridge/auth.h"
#include "../src/mcp_bridge/types_serializer.h"
#include "../src/mcp_bridge/dispatcher.h"
#include "../src/mcp_bridge/handlers.h"

int main() {
    std::cout << "=== Running C++ Standalone Bridge Unit Tests ===" << std::endl;

    // 1. Test Auth Token Generation & Validation
    std::string token1 = mcp_bridge::generate_session_token();
    std::string token2 = mcp_bridge::generate_session_token();
    assert(token1.length() == 32);
    assert(token2.length() == 32);
    assert(token1 != token2);
    assert(mcp_bridge::validate_token(token1, token1) == true);
    assert(mcp_bridge::validate_token(token1, token2) == false);
    assert(mcp_bridge::validate_token("", token1) == false);
    assert(mcp_bridge::validate_token(token1, "") == false);

    bool wrote = mcp_bridge::write_token_file(token1);
    assert(wrote);
    std::string read_back = mcp_bridge::read_token_file();
    assert(read_back == token1);
    std::cout << "✓ Auth tests passed" << std::endl;

    // 2. Test Coordinate Conversion
    int w = 1920, h = 1080;
    double ppu = 60.0;
    // Synfig origin (0, 0) -> screen center (960, 540)
    mcp_bridge::Point2D p1 = mcp_bridge::synfig_to_pixel(0.0, 0.0, w, h, ppu);
    assert(std::abs(p1.x - 960.0) < 1e-4);
    assert(std::abs(p1.y - 540.0) < 1e-4);

    mcp_bridge::Point2D s1 = mcp_bridge::pixel_to_synfig(960.0, 540.0, w, h, ppu);
    assert(std::abs(s1.x - 0.0) < 1e-4);
    assert(std::abs(s1.y - 0.0) < 1e-4);
    std::cout << "✓ Coordinate conversion tests passed" << std::endl;

    // 3. Test Handshake & Standalone Handlers
    mcp_bridge::set_session_token(token1);
    bool authenticated = false;

    // Hello with bad token
    nlohmann::json bad_req = {
        {"jsonrpc", "2.0"},
        {"id", 1},
        {"method", "hello"},
        {"params", {{"protocol_version", "1.0"}, {"token", "wrong_token"}}}
    };
    nlohmann::json bad_res = mcp_bridge::dispatch_request(bad_req, authenticated);
    assert(bad_res.contains("error"));
    assert(bad_res["error"]["code"] == 1002);
    assert(authenticated == false);

    // Hello with bad version
    nlohmann::json bad_ver_req = {
        {"jsonrpc", "2.0"},
        {"id", 2},
        {"method", "hello"},
        {"params", {{"protocol_version", "99.0"}, {"token", token1}}}
    };
    nlohmann::json bad_ver_res = mcp_bridge::dispatch_request(bad_ver_req, authenticated);
    assert(bad_ver_res.contains("error"));
    assert(bad_ver_res["error"]["code"] == 1003);
    assert(authenticated == false);

    // Call without authentication
    nlohmann::json unauth_req = {
        {"jsonrpc", "2.0"},
        {"id", 3},
        {"method", "doc.info"},
        {"params", {{"doc_id", "doc_0"}}}
    };
    nlohmann::json unauth_res = mcp_bridge::dispatch_request(unauth_req, authenticated);
    assert(unauth_res.contains("error"));
    assert(unauth_res["error"]["code"] == 1002);

    // Successful hello
    nlohmann::json good_req = {
        {"jsonrpc", "2.0"},
        {"id", 4},
        {"method", "hello"},
        {"params", {{"protocol_version", "1.0"}, {"token", token1}}}
    };
    nlohmann::json good_res = mcp_bridge::dispatch_request(good_req, authenticated);
    assert(good_res.contains("result"));
    assert(authenticated == true);
    assert(good_res["result"]["protocol_version"] == "1.0");

    // doc.info after auth
    nlohmann::json info_res = mcp_bridge::dispatch_request(unauth_req, authenticated);
    assert(info_res.contains("result"));
    assert(info_res["result"]["width"] == 1920);
    assert(info_res["result"]["height"] == 1080);
    std::cout << "✓ Dispatch and handler tests passed" << std::endl;

    std::cout << "=== ALL STANDALONE C++ TESTS PASSED ===" << std::endl;
    return 0;
}
