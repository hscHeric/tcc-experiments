cmake_minimum_required(VERSION 3.16)
project(hscopt C)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_STANDARD_REQUIRED ON)

if (PROJECT_IS_TOP_LEVEL)
  set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
endif()

option(HSCOPT_BUILD_EXAMPLES "Compila os exemplos do projeto" ${PROJECT_IS_TOP_LEVEL})
option(HSCOPT_ENABLE_OPENMP "Habilita OpenMP quando disponivel" ON)

add_library(hscopt STATIC
  src/rng.c
  src/aco.c
  src/hho.c
  src/rvns.c
  src/ts.c
)

add_library(hscopt::hscopt ALIAS hscopt)

target_include_directories(hscopt PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

if (CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(hscopt PRIVATE
    -Wall
    -Wextra
    -Wpedantic
  )
endif()

if (HSCOPT_ENABLE_OPENMP)
  find_package(OpenMP QUIET)
  if (OpenMP_C_FOUND)
    target_link_libraries(hscopt PUBLIC OpenMP::OpenMP_C)
    target_compile_definitions(hscopt PUBLIC HSCOPT_HAVE_OPENMP=1)
  else()
    target_compile_definitions(hscopt PUBLIC HSCOPT_HAVE_OPENMP=0)
  endif()
else()
  target_compile_definitions(hscopt PUBLIC HSCOPT_HAVE_OPENMP=0)
endif()

# Math library
target_link_libraries(hscopt PUBLIC m)

if (HSCOPT_BUILD_EXAMPLES)
  add_executable(knapsack_hho_example examples/knapsack_hho_example.c)
  target_link_libraries(knapsack_hho_example PRIVATE hscopt)

  add_executable(knapsack_rvns_example examples/knapsack_rvns_example.c)
  target_link_libraries(knapsack_rvns_example PRIVATE hscopt)

  add_executable(knapsack_aco_example examples/knapsack_aco_example.c)
  target_link_libraries(knapsack_aco_example PRIVATE hscopt)

  add_executable(knapsack_ts_example examples/knapsack_ts_example.c)
  target_link_libraries(knapsack_ts_example PRIVATE hscopt)
endif()
