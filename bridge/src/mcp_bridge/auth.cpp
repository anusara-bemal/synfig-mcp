#include "auth.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <random>
#include <cstdlib>
#include <sys/stat.h>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <aclapi.h>
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

#ifdef _WIN32
static bool set_windows_owner_only_acl(const std::string& path) {
    HANDLE hToken = NULL;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken)) {
        return false;
    }

    DWORD dwSize = 0;
    GetTokenInformation(hToken, TokenUser, NULL, 0, &dwSize);
    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER || dwSize == 0) {
        CloseHandle(hToken);
        return false;
    }

    std::vector<BYTE> buffer(dwSize);
    PTOKEN_USER pTokenUser = reinterpret_cast<PTOKEN_USER>(buffer.data());
    if (!GetTokenInformation(hToken, TokenUser, pTokenUser, dwSize, &dwSize)) {
        CloseHandle(hToken);
        return false;
    }

    EXPLICIT_ACCESS_A ea;
    ZeroMemory(&ea, sizeof(EXPLICIT_ACCESS_A));
    ea.grfAccessPermissions = GENERIC_ALL;
    ea.grfAccessMode = SET_ACCESS;
    ea.grfInheritance = NO_INHERITANCE;
    ea.Trustee.TrusteeForm = TRUSTEE_IS_SID;
    ea.Trustee.TrusteeType = TRUSTEE_IS_USER;
    ea.Trustee.ptstrName = reinterpret_cast<LPSTR>(pTokenUser->User.Sid);

    PACL pAcl = NULL;
    DWORD res = SetEntriesInAclA(1, &ea, NULL, &pAcl);
    CloseHandle(hToken);

    if (res != ERROR_SUCCESS) {
        return false;
    }

    DWORD setRes = SetNamedSecurityInfoA(
        const_cast<LPSTR>(path.c_str()),
        SE_FILE_OBJECT,
        DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
        NULL,
        NULL,
        pAcl,
        NULL
    );

    if (setRes != ERROR_SUCCESS) {
        std::cerr << "[mcp_bridge] SetNamedSecurityInfoA failed with error code: " << setRes << " on path: " << path << std::endl;
    }

    LocalFree(pAcl);
    return (setRes == ERROR_SUCCESS);
}
#endif

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

#ifdef _WIN32
    if (!set_windows_owner_only_acl(path)) {
        std::cerr << "[mcp_bridge] Warning: Could not set owner-only ACL on token file: " << path << std::endl;
    }
#else
    chmod(path.c_str(), 0600);
#endif

    // Also write per-PID token file to distinguish multiple concurrent Studio instances
    unsigned long pid = 0;
#ifdef _WIN32
    pid = (unsigned long)GetCurrentProcessId();
#else
    pid = (unsigned long)getpid();
#endif
    std::string pid_path = path + "_" + std::to_string(pid);
    std::ofstream ofs_pid(pid_path.c_str(), std::ios::out | std::ios::trunc);
    if (ofs_pid.is_open()) {
        ofs_pid << token << std::endl;
        ofs_pid.close();
#ifdef _WIN32
        set_windows_owner_only_acl(pid_path);
#else
        chmod(pid_path.c_str(), 0600);
#endif
    }

    return true;
}

std::string get_config_file_path() {
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
        return "mcp_enabled";
    }

    std::string path = home;
#ifdef _WIN32
    path += "\\.synfig\\mcp_enabled";
#else
    path += "/.synfig/mcp_enabled";
#endif
    return path;
}

void clean_stale_tokens() {
    const char* home = nullptr;
#ifdef _WIN32
    home = std::getenv("USERPROFILE");
    if (!home) home = std::getenv("APPDATA");
    if (!home) return;
    std::string token_dir = std::string(home) + "\\.synfig";

    std::string pattern = token_dir + "\\mcp_token_*";
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(pattern.c_str(), &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                std::string fname = fd.cFileName;
                size_t idx = fname.rfind('_');
                if (idx != std::string::npos && idx + 1 < fname.size()) {
                    std::string pid_str = fname.substr(idx + 1);
                    try {
                        DWORD pid = (DWORD)std::stoul(pid_str);
                        HANDLE hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
                        bool is_alive = false;
                        if (hProcess) {
                            DWORD exit_code = 0;
                            if (GetExitCodeProcess(hProcess, &exit_code) && exit_code == STILL_ACTIVE) {
                                is_alive = true;
                            }
                            CloseHandle(hProcess);
                        }
                        if (!is_alive) {
                            std::string file_path = token_dir + "\\" + fname;
                            DeleteFileA(file_path.c_str());
                        }
                    } catch (...) {}
                }
            }
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }
#else
    home = std::getenv("HOME");
    if (!home) return;
    std::string token_dir = std::string(home) + "/.synfig";
    DIR* dir = opendir(token_dir.c_str());
    if (!dir) return;
    struct dirent* ent;
    while ((ent = readdir(dir)) != NULL) {
        std::string fname = ent->d_name;
        if (fname.find("mcp_token_") == 0) {
            std::string pid_str = fname.substr(10);
            try {
                pid_t pid = (pid_t)std::stol(pid_str);
                if (kill(pid, 0) == -1 && errno == ESRCH) {
                    std::string fpath = token_dir + "/" + fname;
                    unlink(fpath.c_str());
                }
            } catch (...) {}
        }
    }
    closedir(dir);
#endif
}

void remove_session_token_files() {
    std::string token_path = get_token_file_path();
    unsigned long pid = 0;
#ifdef _WIN32
    pid = (unsigned long)GetCurrentProcessId();
#else
    pid = (unsigned long)getpid();
#endif
    std::string pid_path = token_path + "_" + std::to_string(pid);
#ifdef _WIN32
    DeleteFileA(pid_path.c_str());
#else
    unlink(pid_path.c_str());
#endif

    // If mcp_token contains this session's token, remove it as well
    std::string current_token = read_token_file();
    if (!current_token.empty()) {
        std::ifstream ifs(token_path.c_str());
        if (ifs.is_open()) {
            std::string tok;
            ifs >> tok;
            ifs.close();
            if (tok == current_token) {
#ifdef _WIN32
                DeleteFileA(token_path.c_str());
#else
                unlink(token_path.c_str());
#endif
            }
        }
    }
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
