FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV IN_DOCKER=1

# Core dependencies + Xenia runtime libs + Ghidra deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Virtual display, VNC & window tools
    xvfb xdotool imagemagick x11-apps x11vnc \
    # Xorg with dummy driver (fallback display)
    xserver-xorg-core xserver-xorg-video-dummy \
    # Weston compositor + Xwayland (DRI3 support for Vulkan presentation)
    weston xwayland \
    # Python
    python3 python3-pip \
    # Mesa software Vulkan (lavapipe) + OpenGL
    mesa-utils libgl1-mesa-dri libgl1 libegl-mesa0 libopengl0 libglx0 \
    mesa-vulkan-drivers vulkan-tools \
    # XCB/X11 deps
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0 \
    # GTK3 + SDL2 (Xenia deps)
    libgtk-3-0 libsdl2-2.0-0 \
    # Audio
    libasound2t64 libpulse0 \
    # JDK 21 for Ghidra
    openjdk-21-jdk-headless \
    # Build tools (Gradle for building Ghidra extensions from source)
    gradle \
    # Misc
    libfuse2t64 file curl wget procps unzip git \
    && rm -rf /var/lib/apt/lists/*

# Download xenia-edge Linux AppImage (has critical Linux JIT/signal fixes over xenia-canary)
RUN cd /tmp && \
    wget -q "https://github.com/has207/xenia-edge/releases/latest/download/xenia_edge_linux.AppImage" -O xenia.AppImage && \
    chmod +x xenia.AppImage && \
    ./xenia.AppImage --appimage-extract && \
    mv squashfs-root /opt/xenia && \
    rm -f xenia.AppImage && \
    ln -sf /opt/xenia/usr/bin/xenia_edge /usr/local/bin/xenia

# ---- Ghidra 12.0.4 ----
ENV GHIDRA_VERSION=12.0.4
ENV GHIDRA_DATE=20260303
ENV GHIDRA_HOME=/opt/ghidra

RUN cd /tmp && \
    wget -q "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_DATE}.zip" \
         -O ghidra.zip && \
    unzip -q ghidra.zip -d /opt && \
    mv /opt/ghidra_${GHIDRA_VERSION}_PUBLIC ${GHIDRA_HOME} && \
    rm ghidra.zip && \
    ln -sf ${GHIDRA_HOME}/ghidraRun /usr/local/bin/ghidra && \
    ln -sf ${GHIDRA_HOME}/support/analyzeHeadless /usr/local/bin/analyzeHeadless

# ---- XEXLoaderWV (Xbox 360 XEX file loader for Ghidra) ----
# Note: XEXLoaderWV release dates differ from Ghidra release dates
RUN cd /tmp && \
    wget -q "https://github.com/zeroKilo/XEXLoaderWV/releases/download/${GHIDRA_VERSION}/ghidra_${GHIDRA_VERSION}_PUBLIC_20260329_XEXLoaderWV.zip" \
         -O XEXLoaderWV.zip && \
    mkdir -p ${GHIDRA_HOME}/Ghidra/Extensions && \
    unzip -q XEXLoaderWV.zip -d ${GHIDRA_HOME}/Ghidra/Extensions/ && \
    rm XEXLoaderWV.zip

# ---- GhidraXenon (VMX128 Xenon PowerPC instructions + MSVC switch table recovery) ----
# Build from source against our Ghidra version
RUN cd /tmp && \
    git clone --depth 1 https://github.com/freeqaz/ghidra-xenon-extension.git && \
    cd ghidra-xenon-extension && \
    GHIDRA_INSTALL_DIR=${GHIDRA_HOME} gradle buildExtension --no-daemon 2>/dev/null && \
    unzip -q dist/*.zip -d ${GHIDRA_HOME}/Ghidra/Extensions/ && \
    cd / && rm -rf /tmp/ghidra-xenon-extension

# ---- Xbox 360 SDK Function ID Databases (auto-identify SDK library functions) ----
RUN git clone --depth 1 https://github.com/tomcl7/ghidra-fidb-xenonsdk.git /tmp/fidb && \
    mkdir -p ${GHIDRA_HOME}/Ghidra/Features/Base/data/fidb && \
    cp /tmp/fidb/*.fidb ${GHIDRA_HOME}/Ghidra/Features/Base/data/fidb/ && \
    rm -rf /tmp/fidb

COPY entrypoint.sh /tools/
RUN chmod +x /tools/entrypoint.sh

WORKDIR /game
ENTRYPOINT ["/tools/entrypoint.sh"]
