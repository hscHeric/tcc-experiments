cmake_minimum_required(VERSION 3.16)
project(tcc_experiments LANGUAGES C CXX)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(TccProjectSetup)
include(TccLinkCompileCommands)

set(HSCOPT_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory(external/hscopt)

add_library(tcc_graph STATIC
  metaheuristic/graph.cpp
)

target_include_directories(tcc_graph
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/metaheuristic
    ${CMAKE_CURRENT_SOURCE_DIR}/external/hscopt/include
)

target_link_libraries(tcc_graph
  PUBLIC
    hscopt
)

tcc_setup_target(tcc_graph)

if (TCC_BUILD_METAHEURISTICS)
  add_executable(aco_ts
    metaheuristic/aco_ts_main.cpp
  )

  target_link_libraries(aco_ts
    PRIVATE
      tcc_graph
      hscopt
  )

  tcc_setup_target(aco_ts)

  add_executable(hho_rvns
    metaheuristic/hho_rvns_main.cpp
  )

  target_link_libraries(hho_rvns
    PRIVATE
      tcc_graph
      hscopt
  )

  tcc_setup_target(hho_rvns)

  add_executable(brkga
    metaheuristic/brkga_main.cpp
  )

  target_link_libraries(brkga
    PRIVATE
      tcc_graph
      hscopt
  )

  tcc_setup_target(brkga)
endif()

tcc_link_compile_commands(
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_BINARY_DIR}
)
