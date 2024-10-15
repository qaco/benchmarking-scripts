cmake_minimum_required(VERSION 3.15.1)

project(perf-pipedream)
set(CMAKE_C_FLAGS "-Wall -Wextra -Werror -g")

add_library(perf-pipedream STATIC
    lib/perf-pipedream.c
)

install(TARGETS perf-pipedream DESTINATION lib)
install(FILES lib/perf-pipedream.h DESTINATION include)


project(perf-pipedream-example)
set(CMAKE_C_FLAGS "-Wall -Wextra -Werror -g")

add_executable(perf-pipedream-example
    examples/perf-pipedream-example.c)
target_include_directories(perf-pipedream-example PRIVATE lib)
target_link_libraries(perf-pipedream-example PUBLIC perf-pipedream -static)
