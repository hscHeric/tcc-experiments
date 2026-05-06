cmake_minimum_required(VERSION 3.20)

project(tcc_experiments LANGUAGES CXX)

include(CheckCXXSourceCompiles)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Link simbólico do compile_commands.json
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

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Debug CACHE STRING "Tipo de build" FORCE)
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

add_compile_options(-Wall -Wextra -Wpedantic)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3")

set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")

set(CMAKE_CXX_FLAGS_RELWITHDEBINFO
    "-O2 -g -fno-omit-frame-pointer -fno-optimize-sibling-calls -march=native -pg")

option(ENABLE_DEBUG_SANITIZERS "Ativa sanitizers no build Debug" ON)

if(ENABLE_DEBUG_SANITIZERS)
  set(CMAKE_REQUIRED_QUIET TRUE)
  set(CMAKE_REQUIRED_FLAGS "-fsanitize=address,undefined")
  set(CMAKE_REQUIRED_LINK_OPTIONS "-fsanitize=address,undefined")
  check_cxx_source_compiles("int main() { return 0; }" HAS_DEBUG_SANITIZERS)
  unset(CMAKE_REQUIRED_FLAGS)
  unset(CMAKE_REQUIRED_LINK_OPTIONS)

  if(HAS_DEBUG_SANITIZERS)
    set(CMAKE_CXX_FLAGS_DEBUG
        "${CMAKE_CXX_FLAGS_DEBUG} -fsanitize=address,undefined")
    set(CMAKE_EXE_LINKER_FLAGS_DEBUG
        "${CMAKE_EXE_LINKER_FLAGS_DEBUG} -fsanitize=address,undefined")
    message(STATUS "Debug sanitizers enabled")
  else()
    message(WARNING "Sanitizers indisponíveis neste ambiente")
  endif()
endif()

option(ENABLE_LTO "Enable LTO in Release builds" OFF)

if(ENABLE_LTO)
  set(CMAKE_CXX_FLAGS_RELEASE
      "${CMAKE_CXX_FLAGS_RELEASE} -flto")
endif()

find_package(CLI11 REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(quill REQUIRED)

add_subdirectory(external/hsc-brkga-api)
add_subdirectory(external/hsc-brkga-mp-ipr_api)

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
    quill::quill
    nlohmann_json::nlohmann_json
    hscopt::hscopt
)

add_executable(brkga_runner
    src/runners/brkga_runner.cpp
)

add_executable(brkga_mp_ipr_runner
    src/runners/brkga_mp_ipr_runner.cpp
)
set_target_properties(brkga_mp_ipr_runner PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

add_executable(aco_ts_runner
    src/runners/aco_ts_runner.cpp
)

add_executable(hho_rvns_runner
    src/runners/hho_rvns_runner.cpp
)

target_link_libraries(brkga_runner PRIVATE
    core
    BRKGA::brkga
    CLI11::CLI11
)

target_link_libraries(brkga_mp_ipr_runner PRIVATE
    BRKGA::brkga_mp_ipr
)

target_link_libraries(aco_ts_runner PRIVATE
    core
    hscopt::hscopt
    CLI11::CLI11
)

target_link_libraries(hho_rvns_runner PRIVATE
    core
    hscopt::hscopt
    CLI11::CLI11
)

set(RUNNER_TARGETS
    brkga_runner
    brkga_mp_ipr_runner
    aco_ts_runner
    hho_rvns_runner
)

foreach(runner_target IN LISTS RUNNER_TARGETS)
  target_compile_definitions(${runner_target} PRIVATE
      $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>>:QUILL_COMPILE_ACTIVE_LOG_LEVEL=QUILL_COMPILE_ACTIVE_LOG_LEVEL_CRITICAL>
  )
endforeach()

message(STATUS "Projeto configurado com sucesso")
