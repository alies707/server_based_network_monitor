cmake_minimum_required(VERSION 3.20)
project(network_monitor_client LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(ixwebsocket
  GIT_REPOSITORY https://github.com/machinezone/IXWebSocket.git
  GIT_TAG v11.4.5
)
set(USE_TLS OFF CACHE BOOL "Disable TLS for this build" FORCE)
FetchContent_MakeAvailable(ixwebsocket)

add_executable(network-monitor-client
  src/main.cpp
  src/network_stats.cpp
)

target_include_directories(network-monitor-client PRIVATE src)
target_link_libraries(network-monitor-client PRIVATE ixwebsocket)

if(WIN32)
  target_link_libraries(network-monitor-client PRIVATE iphlpapi ws2_32)
endif()

if(UNIX AND NOT APPLE)
  target_link_libraries(network-monitor-client PRIVATE pthread)
endif()
