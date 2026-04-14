#!/usr/bin/env bash
# Build tools/dump_xex_image inside the civrev-xenonrecomp docker image
# and use it to decompress work/extracted/default.xex into
# work/extracted/default_decompressed.bin (the mapped image at VA 0x82000000).
#
# Prereq: civrev-xenonrecomp image already built via xenon_recomp/run.sh.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
RECOMP_DIR="$(dirname "$HERE")"
WORK_DIR="$RECOMP_DIR/work"

docker run --rm -v "$RECOMP_DIR:/civrev" civrev-xenonrecomp bash -c '
set -e
cd /tmp
cp /civrev/tools/dump_xex_image.cpp .
clang++-18 -std=c++20 -O2 \
    -I /opt/XenonRecomp/XenonUtils \
    dump_xex_image.cpp \
    /opt/XenonRecomp/build/XenonUtils/libXenonUtils.a \
    -o /civrev/tools/dump_xex_image

/civrev/tools/dump_xex_image \
    /civrev/work/extracted/default.xex \
    /civrev/work/extracted/default_decompressed.bin
'

ls -la "$WORK_DIR/extracted/default_decompressed.bin"
