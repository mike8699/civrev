FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV IN_DOCKER=1

# Core dependencies + Xenia runtime libs
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
    # Misc
    libfuse2t64 file curl wget procps \
    && rm -rf /var/lib/apt/lists/*

# Download xenia-edge Linux AppImage (has critical Linux JIT/signal fixes over xenia-canary)
RUN cd /tmp && \
    wget -q "https://github.com/has207/xenia-edge/releases/latest/download/xenia_edge_linux.AppImage" -O xenia.AppImage && \
    chmod +x xenia.AppImage && \
    ./xenia.AppImage --appimage-extract && \
    mv squashfs-root /opt/xenia && \
    rm -f xenia.AppImage && \
    ln -sf /opt/xenia/usr/bin/xenia_edge /usr/local/bin/xenia

COPY entrypoint.sh /tools/
RUN chmod +x /tools/entrypoint.sh

WORKDIR /game
ENTRYPOINT ["/tools/entrypoint.sh"]
