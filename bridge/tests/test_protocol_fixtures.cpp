#include <iostream>
#include <fstream>
#include <string>
#include <vector>

int main(int argc, char* argv[])
{
    std::string fixtures_dir = "protocol/fixtures";
    if (argc > 1) {
        fixtures_dir = argv[1];
    }

    std::vector<std::string> fixture_files = {
        "handshake_request.json",
        "handshake_response.json",
        "doc_info_request.json",
        "doc_info_response.json",
        "layer_add_request.json",
        "layer_add_response.json",
        "param_set_request.json",
        "param_set_response.json",
        "event_time_changed.json",
        "event_selection_changed.json"
    };

    std::cout << "=== Running GTK-Free C++ Protocol Fixture Tests ===" << std::endl;
    std::cout << "Fixtures Dir: " << fixtures_dir << std::endl;

    int passed = 0;
    int failed = 0;

    for (const auto& file_name : fixture_files) {
        std::string full_path = fixtures_dir + "/" + file_name;
        std::ifstream file(full_path, std::ios::in | std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "FAIL: " << file_name << " (could not open: " << full_path << ")" << std::endl;
            failed++;
            continue;
        }

        std::string content((std::istreambuf_iterator<char>(file)),
                             std::istreambuf_iterator<char>());

        if (content.find("\"jsonrpc\"") == std::string::npos || content.find("\"2.0\"") == std::string::npos) {
            std::cerr << "FAIL: " << file_name << " (missing jsonrpc 2.0)" << std::endl;
            failed++;
            continue;
        }

        std::cout << "PASS: " << file_name << " (" << content.size() << " bytes)" << std::endl;
        passed++;
    }

    std::cout << "Summary: " << passed << " passed, " << failed << " failed." << std::endl;
    return failed == 0 ? 0 : 1;
}
