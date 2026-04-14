cmake_minimum_required(VERSION 3.20)

project(tcc_experiments LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# build como debug por padrão
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug CACHE STRING "Tipo de build" FORCE)
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

# flags globais
add_compile_options(-Wall -Wextra -Wpedantic)

#flags para debug
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
  add_compile_options(-O0 -g3 -fsanitize=address,undefined)
  add_link_options(-fsanitize=address,undefined)

  #flags para release
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
  add_compile_options(-O3 -march=native -flto -DNDEBUG)
  add_link_options(-flto)
endif()

find_package(CLI11 REQUIRED)
find_package(spdlog REQUIRED)
find_package(nlohmann_json REQUIRED)

file(GLOB_RECURSE CORE_SOURCES
    src/core/*.cpp
)

add_library(core ${CORE_SOURCES})

target_include_directories(core PUBLIC
    src/core
)

target_link_libraries(core PUBLIC
    spdlog::spdlog
    nlohmann_json::nlohmann_json
)

add_executable(brkga_runner
    src/runners/brkga_runner.cpp
)

target_link_libraries(brkga_runner PRIVATE
    core
    CLI11::CLI11
)

message(STATUS "Projeto configurado com sucesso")
