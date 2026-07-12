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

# rexglue_setup_target(civrev) inlined: the macro doesn't forward GPU_PLUGINS,
# and the nightly SDK runtime-loads GPU emulation from a plugin staged next to
# the executable (librexgpu-xenos.so) — without it the game runs headless.
target_sources(civrev PRIVATE ${REXGLUE_ENTRYPOINT_GENERATED_SOURCES})
target_include_directories(civrev PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${REXGLUE_ENTRYPOINT_INCLUDE_DIR}
)
target_link_libraries(civrev PRIVATE rex::runtime)
rexglue_configure_target(civrev GPU_PLUGINS xenos)
