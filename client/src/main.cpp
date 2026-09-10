#include "network_stats.h"

#include <ixwebsocket/IXWebSocket.h>

#include <chrono>
#include <cctype>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>

static std::string json_escape(const std::string& value) {
    std::string result;
    result.reserve(value.size() + 8);
    for (char c : value) {
        if (c == '\\') result += "\\\\";
        else if (c == '"') result += "\\\"";
        else result += c;
    }
    return result;
}

static std::string url_encode(const std::string& value) {
    static constexpr char hex[] = "0123456789ABCDEF";
    std::string result;
    result.reserve(value.size() * 3);
    for (unsigned char c : value) {
        if (std::isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
            result += static_cast<char>(c);
        } else {
            result += '%';
            result += hex[c >> 4];
            result += hex[c & 0x0F];
        }
    }
    return result;
}

static std::string make_heartbeat(const std::string& client_id, const NetworkCounters& counters) {
    std::ostringstream out;
    out << "{\"type\":\"heartbeat\",\"client_id\":\""
        << json_escape(client_id)
        << "\",\"rx_bytes\":" << counters.rx_bytes
        << ",\"tx_bytes\":" << counters.tx_bytes
        << ",\"timestamp\":"
        << std::chrono::duration_cast<std::chrono::seconds>(
               std::chrono::system_clock::now().time_since_epoch()).count()
        << "}";
    return out.str();
}

int main(int argc, char* argv[]) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: network-monitor-client <ws-url> <client-id> [token]\n";
        std::cerr << "Example: network-monitor-client ws://127.0.0.1:8000/ws/client PC-01 secret\n";
        return 2;
    }

    const std::string url = argv[1];
    const std::string client_id = argv[2];
    const std::string token = argc == 4 ? argv[3] : "";

    ix::initNetSystem();

    while (true) {
        ix::WebSocket web_socket;
        std::string connection_url = url;
        if (!token.empty()) {
            connection_url += (connection_url.find('?') == std::string::npos ? "?token=" : "&token=") + url_encode(token);
        }
        web_socket.setUrl(connection_url);
        web_socket.setPingInterval(15);
        web_socket.setOnMessageCallback([](const ix::WebSocketMessagePtr& message) {
            if (message->type == ix::WebSocketMessageType::Open) {
                std::cout << "Connected to server\n";
            } else if (message->type == ix::WebSocketMessageType::Close) {
                std::cout << "Disconnected from server\n";
            } else if (message->type == ix::WebSocketMessageType::Error) {
                std::cerr << "WebSocket error: " << message->errorInfo.reason << "\n";
            }
        });

        web_socket.start();
        std::this_thread::sleep_for(std::chrono::milliseconds(500));

        if (!web_socket.isConnected()) {
            web_socket.stop();
            std::this_thread::sleep_for(std::chrono::seconds(3));
            continue;
        }

        while (web_socket.isConnected()) {
            try {
                const auto counters = read_network_counters();
                web_socket.send(make_heartbeat(client_id, counters));
            } catch (const std::exception& error) {
                std::cerr << "Network counter error: " << error.what() << "\n";
            }
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        web_socket.stop();
        std::this_thread::sleep_for(std::chrono::seconds(3));
    }

    ix::uninitNetSystem();
    return 0;
}
