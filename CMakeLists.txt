cmake_minimum_required(VERSION 3.20)

project(tcc_experiments LANGUAGES CXX)

include(CheckCXXSourceCompiles)
include(CheckIPOSupported)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE
      Debug
      CACHE STRING "Tipo de build" FORCE)
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

option(ENABLE_DEBUG_SANITIZERS "Ativa sanitizers no build Debug" ON)
option(ENABLE_RELEASE_LTO "Ativa LTO nos builds Release" ON)
option(ENABLE_NATIVE_OPTIMIZATIONS "Otimiza Release para a CPU local" ON)

add_compile_definitions($<$<CONFIG:Debug>:DEBUG>)

if(CMAKE_EXPORT_COMPILE_COMMANDS
   AND NOT CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
  set(PROJECT_COMPILE_COMMANDS_LINK "${CMAKE_SOURCE_DIR}/compile_commands.json")

  if(EXISTS "${PROJECT_COMPILE_COMMANDS_LINK}"
     OR IS_SYMLINK "${PROJECT_COMPILE_COMMANDS_LINK}")
    file(REMOVE "${PROJECT_COMPILE_COMMANDS_LINK}")
  endif()

  file(CREATE_LINK
       "${CMAKE_BINARY_DIR}/compile_commands.json"
       "${PROJECT_COMPILE_COMMANDS_LINK}"
       SYMBOLIC)
endif()

set(HSC_DEBUG_COMPILE_OPTIONS -O0 -g3)
set(HSC_RELEASE_COMPILE_OPTIONS -O3)
set(HSC_PERF_COMPILE_OPTIONS -O2 -g -fno-omit-frame-pointer
                             -fno-optimize-sibling-calls -pg)
set(HSC_PERF_LINK_OPTIONS -pg)

if(ENABLE_NATIVE_OPTIMIZATIONS)
  list(APPEND HSC_RELEASE_COMPILE_OPTIONS -march=native -mtune=native)
  list(APPEND HSC_PERF_COMPILE_OPTIONS -march=native -mtune=native)
endif()

if(ENABLE_DEBUG_SANITIZERS)
  set(CMAKE_REQUIRED_QUIET TRUE)
  set(CMAKE_REQUIRED_FLAGS "-fsanitize=address,undefined")
  set(CMAKE_REQUIRED_LINK_OPTIONS "-fsanitize=address,undefined")
  check_cxx_source_compiles("int main() { return 0; }" HAS_DEBUG_SANITIZERS)
  unset(CMAKE_REQUIRED_FLAGS)
  unset(CMAKE_REQUIRED_LINK_OPTIONS)

  if(HAS_DEBUG_SANITIZERS)
    list(APPEND HSC_DEBUG_COMPILE_OPTIONS -fsanitize=address,undefined)
    set(HSC_DEBUG_LINK_OPTIONS -fsanitize=address,undefined)
    message(STATUS "Debug sanitizers enabled")
  else()
    message(WARNING "Sanitizers indisponíveis neste ambiente")
  endif()
endif()

if(ENABLE_RELEASE_LTO)
  check_ipo_supported(RESULT HSC_IPO_SUPPORTED OUTPUT HSC_IPO_ERROR)
  if(HSC_IPO_SUPPORTED)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)
    message(STATUS "Release LTO enabled")
  else()
    message(WARNING "LTO indisponível: ${HSC_IPO_ERROR}")
  endif()
endif()

find_package(CLI11 REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(quill REQUIRED)

add_subdirectory(external/hsc-brkga-api)
add_subdirectory(external/hsc-brkga-mp-ipr_api)

set(HSCOPT_BUILD_EXAMPLES
    OFF
    CACHE BOOL "Disable hscopt examples in parent builds" FORCE)
add_subdirectory(external/hscopt EXCLUDE_FROM_ALL)

file(GLOB_RECURSE CORE_SOURCES CONFIGURE_DEPENDS src/core/*.cpp)

add_library(core ${CORE_SOURCES})
target_include_directories(core PUBLIC src/core)
target_link_libraries(core PUBLIC quill::quill nlohmann_json::nlohmann_json
                                  hscopt::hscopt)

function(hsc_apply_project_options target_name)
  set_target_properties(${target_name} PROPERTIES CXX_STANDARD 20
                                                  CXX_STANDARD_REQUIRED ON
                                                  CXX_EXTENSIONS OFF)

  target_compile_options(
    ${target_name}
    PRIVATE -Wall
            -Wextra
            -Wpedantic
            $<$<CONFIG:Debug>:${HSC_DEBUG_COMPILE_OPTIONS}>
            $<$<CONFIG:Release>:${HSC_RELEASE_COMPILE_OPTIONS}>
            $<$<CONFIG:RelWithDebInfo>:${HSC_PERF_COMPILE_OPTIONS}>)

  target_link_options(
    ${target_name}
    PRIVATE $<$<CONFIG:Debug>:${HSC_DEBUG_LINK_OPTIONS}>
            $<$<CONFIG:RelWithDebInfo>:${HSC_PERF_LINK_OPTIONS}>)
endfunction()

hsc_apply_project_options(core)

add_executable(brkga_runner src/runners/brkga_runner.cpp)
target_link_libraries(brkga_runner PRIVATE core BRKGA::brkga CLI11::CLI11)

add_executable(brkga_mp_ipr_runner src/runners/brkga_mp_ipr_runner.cpp)
target_link_libraries(brkga_mp_ipr_runner PRIVATE BRKGA::brkga_mp_ipr)
set_target_properties(brkga_mp_ipr_runner PROPERTIES CXX_STANDARD 20
                                                     CXX_STANDARD_REQUIRED ON
                                                     CXX_EXTENSIONS OFF)

add_executable(aco_ts_runner src/runners/aco_ts_runner.cpp)
target_link_libraries(aco_ts_runner PRIVATE core hscopt::hscopt CLI11::CLI11)

add_executable(hho_rvns_runner src/runners/hho_rvns_runner.cpp)
target_link_libraries(hho_rvns_runner PRIVATE core hscopt::hscopt CLI11::CLI11)

set(RUNNER_TARGETS brkga_runner brkga_mp_ipr_runner aco_ts_runner
                   hho_rvns_runner)

foreach(runner_target IN LISTS RUNNER_TARGETS)
  hsc_apply_project_options(${runner_target})

  target_compile_definitions(
    ${runner_target}
    PRIVATE
      $<$<CONFIG:Release>:QUILL_COMPILE_ACTIVE_LOG_LEVEL=QUILL_COMPILE_ACTIVE_LOG_LEVEL_CRITICAL>
      $<$<CONFIG:RelWithDebInfo>:QUILL_COMPILE_ACTIVE_LOG_LEVEL=QUILL_COMPILE_ACTIVE_LOG_LEVEL_CRITICAL>)
endforeach()

set_target_properties(brkga_mp_ipr_runner PROPERTIES CXX_STANDARD 20
                                                     CXX_STANDARD_REQUIRED ON
                                                     CXX_EXTENSIONS OFF)

message(STATUS "Projeto configurado com sucesso")
