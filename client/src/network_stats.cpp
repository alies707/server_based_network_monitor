#include "network_stats.h"

#include <stdexcept>

#ifdef _WIN32
#include <iphlpapi.h>
#include <windows.h>

NetworkCounters read_network_counters() {
    PMIB_IF_TABLE2 table = nullptr;
    const ULONG result = GetIfTable2(&table);
    if (result != NO_ERROR) {
        throw std::runtime_error("GetIfTable2 failed");
    }

    NetworkCounters counters;
    for (ULONG i = 0; i < table->NumEntries; ++i) {
        const MIB_IF_ROW2& row = table->Table[i];
        if (row.OperStatus == IfOperStatusUp) {
            counters.rx_bytes += row.InOctets;
            counters.tx_bytes += row.OutOctets;
        }
    }
    FreeMibTable(table);
    return counters;
}

#else
#include <dirent.h>
#include <fstream>
#include <string>

static std::uint64_t read_counter(const std::string& path) {
    std::ifstream file(path);
    std::uint64_t value = 0;
    if (file) file >> value;
    return value;
}

NetworkCounters read_network_counters() {
    NetworkCounters counters;
    DIR* dir = opendir("/sys/class/net");
    if (!dir) return counters;

    while (dirent* entry = readdir(dir)) {
        const std::string name = entry->d_name;
        if (name == "." || name == ".." || name == "lo") continue;
        const std::string base = "/sys/class/net/" + name + "/statistics/";
        counters.rx_bytes += read_counter(base + "rx_bytes");
        counters.tx_bytes += read_counter(base + "tx_bytes");
    }
    closedir(dir);
    return counters;
}
#endif
