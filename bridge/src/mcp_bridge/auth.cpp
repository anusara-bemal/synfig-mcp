#include "auth.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <random>
#include <cstdlib>
#include <sys/stat.h>

#ifdef _WIN32
#include <direct.h>
#define MKDIR(dir) _mkdir(dir)
#else
#include <unistd.h>
#define MKDIR(dir) mkdir(dir, 0700)
#endif

namespace mcp_bridge {

std::string generate_session_token() {
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dist;

    uint64_t part1 = dist(gen);
    uint64_t part2 = dist(gen);

    std::ostringstream ss;
    ss << std::hex << std::setfill('0')
       << std::setw(16) << part1
       << std::setw(16) << part2;
    return ss.str();
}

std::string get_token_file_path() {
    const char* home = nullptr;
#ifdef _WIN32
    home = std::getenv("USERPROFILE");
    if (!home) {
        home = std::getenv("APPDATA");
    }
#else
    home = std::getenv("HOME");
#endif
    if (!home) {
        return "mcp_token";
    }

    std::string path = home;
#ifdef _WIN32
    path += "\\.synfig\\mcp_token";
#else
    path += "/.synfig/mcp_token";
#endif
    return path;
}

static bool ensure_directory_exists(const std::string& filepath) {
    size_t last_slash = filepath.find_last_of("/\\");
    if (last_slash == std::string::npos) {
        return true;
    }
    std::string dir = filepath.substr(0, last_slash);
    struct stat info;
    if (stat(dir.c_str(), &info) != 0) {
        if (MKDIR(dir.c_str()) != 0) {
            return false;
        }
    }
    return true;
}

bool write_token_file(const std::string& token) {
    std::string path = get_token_file_path();
    if (!ensure_directory_exists(path)) {
        std::cerr << "[mcp_bridge] Failed to create directory for token file: " << path << std::endl;
        return false;
    }

    std::ofstream ofs(path.c_str(), std::ios::out | std::ios::trunc);
    if (!ofs.is_open()) {
        std::cerr << "[mcp_bridge] Failed to open token file for writing: " << path << std::endl;
        return false;
    }

    ofs << token << std::endl;
    ofs.close();

#ifndef _WIN32
    chmod(path.c_str(), 0600);
#endif

    return true;
}

std::string read_token_file() {
    std::string path = get_token_file_path();
    std::ifstream ifs(path.c_str());
    if (!ifs.is_open()) {
        return "";
    }
    std::string token;
    ifs >> token;
    return token;
}

bool validate_token(const std::string& received_token, const std::string& expected_token) {
    if (expected_token.empty() || received_token.empty()) {
        return false;
    }
    if (received_token.length() != expected_token.length()) {
        return false;
    }
    // Constant-time comparison to prevent timing attacks
    unsigned char result = 0;
    for (size_t i = 0; i < expected_token.length(); ++i) {
        result |= static_cast<unsigned char>(received_token[i] ^ expected_token[i]);
    }
    return result == 0;
}

} // namespace mcp_bridge
