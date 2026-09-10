#pragma once

#include <cstdint>

struct NetworkCounters {
    std::uint64_t rx_bytes = 0;
    std::uint64_t tx_bytes = 0;
};

NetworkCounters read_network_counters();
