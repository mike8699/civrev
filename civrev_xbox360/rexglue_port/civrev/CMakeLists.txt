# civrev - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(civrev LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(CIVREV_SOURCES
    src/main.cpp
    src/kernel_stubs.cpp
)

if(WIN32)
    add_executable(civrev WIN32 ${CIVREV_SOURCES})
else()
    add_executable(civrev ${CIVREV_SOURCES})
endif()

rexglue_setup_target(civrev)
