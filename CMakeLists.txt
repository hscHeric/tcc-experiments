cmake_minimum_required(VERSION 3.20)

project(tcc_experiments LANGUAGES CXX)

include(CheckCXXSourceCompiles)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(CMAKE_EXPORT_COMPILE_COMMANDS AND NOT CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
  set(PROJECT_COMPILE_COMMANDS_LINK "${CMAKE_SOURCE_DIR}/compile_commands.json")

  if(EXISTS "${PROJECT_COMPILE_COMMANDS_LINK}" OR IS_SYMLINK "${PROJECT_COMPILE_COMMANDS_LINK}")
    file(REMOVE "${PROJECT_COMPILE_COMMANDS_LINK}")
  endif()

  file(CREATE_LINK
    "${CMAKE_BINARY_DIR}/compile_commands.json"
    "${PROJECT_COMPILE_COMMANDS_LINK}"
    SYMBOLIC
  )
endif()

# build como debug por padrão
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug CACHE STRING "Tipo de build" FORCE)
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

add_compile_options(-Wall -Wextra -Wpedantic)

option(ENABLE_DEBUG_SANITIZERS "Ativa sanitizers no build Debug quando disponiveis" ON)

#flags para debug
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
  add_compile_options(-O0 -g3)

  if(ENABLE_DEBUG_SANITIZERS)
    set(CMAKE_REQUIRED_QUIET TRUE)
    set(CMAKE_REQUIRED_FLAGS "-fsanitize=address,undefined")
    set(CMAKE_REQUIRED_LINK_OPTIONS "-fsanitize=address,undefined")
    check_cxx_source_compiles("int main() { return 0; }" HAS_DEBUG_SANITIZERS)
    unset(CMAKE_REQUIRED_FLAGS)
    unset(CMAKE_REQUIRED_LINK_OPTIONS)

    if(HAS_DEBUG_SANITIZERS)
      add_compile_options(-fsanitize=address,undefined)
      add_link_options(-fsanitize=address,undefined)
      message(STATUS "Debug sanitizers enabled")
    else()
      message(WARNING "Debug sanitizers requested but unavailable in this environment; continuing without them")
    endif()
  endif()

  #flags para release
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
  add_compile_options(-O3 -march=native -flto=auto -DNDEBUG)
  add_link_options(-flto)
endif()

find_package(CLI11 REQUIRED)
find_package(spdlog REQUIRED)
find_package(nlohmann_json REQUIRED)

add_subdirectory(external/hsc-brkga-api)

set(HSCOPT_BUILD_EXAMPLES OFF CACHE BOOL "Disable hscopt examples in parent builds" FORCE)
add_subdirectory(external/hscopt EXCLUDE_FROM_ALL)

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
    BRKGA::brkga
    CLI11::CLI11
)

message(STATUS "Projeto configurado com sucesso")
