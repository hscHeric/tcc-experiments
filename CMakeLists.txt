cmake_minimum_required(VERSION 3.20)

project(tcc_experiments LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

file(GLOB METAHEURISTICS_SOURCES CONFIGURE_DEPENDS
  "${CMAKE_SOURCE_DIR}/metaheuristics/*.cpp"
)

if(NOT METAHEURISTICS_SOURCES)
  message(FATAL_ERROR "Nenhum arquivo .cpp foi encontrado em metaheuristics/")
endif()

add_executable(main ${METAHEURISTICS_SOURCES})

target_include_directories(main PRIVATE
  "${CMAKE_SOURCE_DIR}/metaheuristics"
)

set(ROOT_COMPILE_COMMANDS_LINK "${CMAKE_SOURCE_DIR}/compile_commands.json")
file(REMOVE "${ROOT_COMPILE_COMMANDS_LINK}")

execute_process(
  COMMAND "${CMAKE_COMMAND}" -E create_symlink
          "${CMAKE_BINARY_DIR}/compile_commands.json"
          "${ROOT_COMPILE_COMMANDS_LINK}"
)
