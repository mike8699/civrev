#!/usr/bin/env bash
# Build the civrev port — works natively on the host AND inside the
# rexglue-toolchain container.
#
# A CMake build dir can only serve one path layout (the cache bakes absolute
# paths), and the container sees this repo at /work while the host sees it at
# its real path. So each environment owns a separate build dir:
#
#   native host : civrev/out/build/host-release
#   container   : civrev/out/build/linux-amd64-release   (used by run_port.sh,
#                                                          test_controls.sh)
#
# Usage:
#   ./build.sh              build natively on the host
#   ./build.sh --docker     build inside the rexglue-toolchain container
#   ./build.sh --clean      wipe the chosen build dir before configuring
#
# The finished binary always has its runtime libraries (librexruntime.so,
# librexgpu-xenos.so, libTracyClient.so) staged next to it: RUNPATH=$ORIGIN,
# so it runs from anywhere without LD_LIBRARY_PATH. Put a controls.toml in
# your working directory (or pass --mnk_config=...) for keyboard/mouse play.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE=host
CLEAN=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --docker) MODE=docker; shift ;;
        --clean) CLEAN=1; shift ;;
        *) echo "unknown arg: $1 (use --docker / --clean)" >&2; exit 2 ;;
    esac
done
# Inside the container, "host" IS the container environment.
if [ -f /.dockerenv ]; then MODE=container; fi

build_in_dir() {  # <src> <build_dir> <sdk_prefix> <cc> <cxx>
    local src="$1" bdir="$2" prefix="$3" cc="$4" cxx="$5"
    [ "$CLEAN" = 1 ] && rm -rf "$bdir"
    cmake -S "$src" -B "$bdir" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$cc" -DCMAKE_CXX_COMPILER="$cxx" \
        -DCMAKE_PREFIX_PATH="$prefix"
    cmake --build "$bdir" --parallel "$(nproc)"
    # Stage the runtime libs next to the binary (RUNPATH=$ORIGIN).
    cp "$prefix"/lib/librexruntime.so "$prefix"/lib/librexgpu-xenos.so \
          "$prefix"/lib/libTracyClient.so "$bdir/"
    echo ""
    echo "Built: $bdir/civrev"
}

case "$MODE" in
host)
    # Container builds run as root and leave root-owned dirs behind; reclaim
    # ownership of the build tree if needed so the host build can write it.
    if [ -e "$HERE/civrev/out" ] && [ ! -w "$HERE/civrev/out" ]; then
        echo "[build] civrev/out is owned by root (from a container build) - reclaiming"
        docker run --rm -v "$HERE:/work" rexglue-toolchain \
            chown -R "$(id -u):$(id -g)" /work/civrev/out
    fi
    # Pick a host compiler: the SDK targets clang-20, but any C++23 clang/gcc
    # can compile the port sources against the prebuilt SDK.
    CXX=""; CC=""
    for c in clang++-20 clang++ g++; do
        command -v "$c" >/dev/null && CXX="$c" && break
    done
    case "$CXX" in
        clang++-20) CC=clang-20 ;;
        clang++)    CC=clang ;;
        g++)        CC=gcc ;;
        *) echo "no C++ compiler found (need clang++ or g++)" >&2; exit 1 ;;
    esac
    echo "[build] native host build with $CXX"
    build_in_dir "$HERE/civrev" "$HERE/civrev/out/build/host-release" \
                 "$HERE/rexglue-sdk/out/install/linux-amd64" "$CC" "$CXX"
    ;;
container)
    echo "[build] container build (linux-amd64-release)"
    build_in_dir /work/civrev /work/civrev/out/build/linux-amd64-release \
                 /work/rexglue-sdk/out/install/linux-amd64 clang-20 clang++-20
    ;;
docker)
    echo "[build] containerized build via rexglue-toolchain image"
    docker run --rm -v "$HERE:/work" -w /work rexglue-toolchain \
        /work/build.sh $([ "$CLEAN" = 1 ] && echo --clean)
    ;;
esac
