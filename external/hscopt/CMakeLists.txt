cmake_minimum_required(VERSION 3.16)
project(hscopt C)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)
include(ProjectSetup)

add_library(hscopt STATIC
  src/alloc.c
  src/rng.c
  src/aco.c
  src/hho.c
  src/rvns.c
)

target_include_directories(hscopt PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

hscopt_setup_target(hscopt)

# Math library
target_link_libraries(hscopt PUBLIC m)

if (HSCOPT_BUILD_EXAMPLES)
  add_executable(knapsack_hho_example examples/knapsack_hho_example.c)
  target_link_libraries(knapsack_hho_example PRIVATE hscopt)
  hscopt_setup_target(knapsack_hho_example)

  add_executable(knapsack_rvns_example examples/knapsack_rvns_example.c)
  target_link_libraries(knapsack_rvns_example PRIVATE hscopt)
  hscopt_setup_target(knapsack_rvns_example)

  add_executable(knapsack_aco_example examples/knapsack_aco_example.c)
  target_link_libraries(knapsack_aco_example PRIVATE hscopt)
  hscopt_setup_target(knapsack_aco_example)
endif()
