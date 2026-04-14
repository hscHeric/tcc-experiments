cmake_minimum_required(VERSION 3.16)

project(hsc_brkga LANGUAGES CXX)

option(BRKGA_ENABLE_RANGECHECK "Enable BRKGA range checks" OFF)

include(CheckCXXSourceCompiles)

find_package(OpenMP REQUIRED COMPONENTS CXX)

set(CMAKE_REQUIRED_QUIET TRUE)
set(CMAKE_REQUIRED_LIBRARIES OpenMP::OpenMP_CXX)
set(CMAKE_REQUIRED_FLAGS "${CMAKE_REQUIRED_FLAGS} ${OpenMP_CXX_FLAGS} -std=c++14")
check_cxx_source_compiles(
    "
    #include <omp.h>
    int main() {
        int total = 0;
        #pragma omp parallel reduction(+:total)
        total += 1;
        return total == 0;
    }
    "
    BRKGA_COMPILER_SUPPORTS_CXX14_WITH_OPENMP
)

if(NOT BRKGA_COMPILER_SUPPORTS_CXX14_WITH_OPENMP)
  message(FATAL_ERROR
        \"hsc_brkga requires a C++14 compiler with OpenMP support enabled.\"
  )
endif()

add_library(brkga STATIC)
add_library(BRKGA::brkga ALIAS brkga)

target_sources(brkga
    PRIVATE
        src/Population.cpp
    PUBLIC
        FILE_SET HEADERS
        BASE_DIRS
            ${CMAKE_CURRENT_SOURCE_DIR}/include
        FILES
            include/BRKGA.h
            include/MTRand.h
            include/Population.h
)

target_include_directories(brkga
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(brkga PUBLIC OpenMP::OpenMP_CXX)

target_compile_features(brkga PUBLIC cxx_std_14)

set_target_properties(brkga PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS OFF
    POSITION_INDEPENDENT_CODE ON
)

if(BRKGA_ENABLE_RANGECHECK)
  target_compile_definitions(brkga PUBLIC RANGECHECK)
endif()
