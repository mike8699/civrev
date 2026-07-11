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
    # Virtual gamepad for driving Xenia's hid=sdl input (oracle/virtpad.py)
    python3-evdev \
    # OCR for detecting on-screen prompts (oracle/ocr.py wait_text): the
    # tesseract binary (called directly, no pytesseract) + PIL for the
    # upscale/autocontrast that makes the stylized prompt text readable.
    tesseract-ocr python3-pil \
    # Misc (zip: packaging the GhidraXenon extension; unzip: Ghidra/AppImage)
    libfuse2t64 file curl wget procps unzip zip git \
    && rm -rf /var/lib/apt/lists/*

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
# Adds the PowerPC:BE:64:Xenon language + MSVC switch-recovery scripts. The repo
# is a prebuilt SLEIGH package: build_extension.sh just stamps the Ghidra version
# and zips it (no gradle/compilation). Pinned to a specific commit for a
# reproducible build; the version stamp must match Ghidra's application.version
# or Ghidra refuses to load the extension. Fails the build hard on any error.
ENV GHIDRA_XENON_COMMIT=3db42fe7db507f45d413b9536e259a08e427d23b
RUN cd /tmp && \
    git clone https://github.com/freeqaz/ghidra-xenon-extension.git && \
    cd ghidra-xenon-extension && \
    git checkout ${GHIDRA_XENON_COMMIT} && \
    GV=$(grep -E '^application.version=' ${GHIDRA_HOME}/Ghidra/application.properties | cut -d= -f2) && \
    ./build_extension.sh "$GV" && \
    unzip -q ghidra_*_GhidraXenon.zip -d ${GHIDRA_HOME}/Ghidra/Extensions/ && \
    test -f ${GHIDRA_HOME}/Ghidra/Extensions/GhidraXenon/data/languages/ppc_64_xenon.sla && \
    cd / && rm -rf /tmp/ghidra-xenon-extension

# ---- Xbox 360 SDK Function ID Databases (auto-identify SDK library functions) ----
RUN git clone --depth 1 https://github.com/tomcl7/ghidra-fidb-xenonsdk.git /tmp/fidb && \
    mkdir -p ${GHIDRA_HOME}/Ghidra/Features/Base/data/fidb && \
    cp /tmp/fidb/*.fidb ${GHIDRA_HOME}/Ghidra/Features/Base/data/fidb/ && \
    rm -rf /tmp/fidb

# ---- xenia-edge (PINNED) ----
# Pinned to a specific release + sha256 for a reproducible oracle (H2). xenia-edge
# has the Linux JIT/signal fixes over xenia-canary. Placed AFTER Ghidra so bumping
# the pin does not invalidate the expensive Ghidra layers. To bump: update TAG +
# SHA256 (get the sha with: curl -sL <url> | sha256sum).
# Pinned to 7acf88d (edge@7acf88d59, 2026-03-21): the build CivRev actually boots
# on (reaches the opening CG / menu). The newer d158580 black-screens this title —
# do not bump without re-verifying CivRev boots. sha256 of the linux AppImage.
ENV XENIA_EDGE_TAG=7acf88d
ENV XENIA_EDGE_SHA256=9335cdb237a8f76aecfd1504633233897a3443c11acdc3a4776e29e3c47b46ab
RUN cd /tmp && \
    wget -q "https://github.com/has207/xenia-edge/releases/download/${XENIA_EDGE_TAG}/xenia_edge_linux.AppImage" -O xenia.AppImage && \
    echo "${XENIA_EDGE_SHA256}  xenia.AppImage" | sha256sum -c - && \
    chmod +x xenia.AppImage && \
    ./xenia.AppImage --appimage-extract && \
    mv squashfs-root /opt/xenia && \
    rm -f xenia.AppImage && \
    ln -sf /opt/xenia/usr/bin/xenia_edge /usr/local/bin/xenia

COPY entrypoint.sh /tools/
RUN chmod +x /tools/entrypoint.sh

WORKDIR /game
ENTRYPOINT ["/tools/entrypoint.sh"]
