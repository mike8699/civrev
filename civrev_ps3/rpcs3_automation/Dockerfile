FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV IN_DOCKER=1

# Core dependencies + RPCS3 runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Virtual display & window tools
    xvfb xdotool xautomation imagemagick x11-apps x11vnc \
    # Python
    python3 python3-pip \
    # Mesa software rendering
    mesa-utils libgl1-mesa-dri libgl1 libegl-mesa0 libopengl0 libglx0 \
    mesa-vulkan-drivers \
    # XCB platform plugin deps (RPCS3 bundles Qt6 but needs xcb libs)
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0 \
    # Audio
    libasound2t64 libpulse0 \
    # Other RPCS3 deps
    libevdev2 libudev1 libusb-1.0-0 \
    libcurl4t64 libsqlite3-0 \
    # Misc
    libfuse2 file curl \
    # Fonts (for Qt)
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python packages
RUN pip --no-cache-dir install --break-system-packages uv
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
RUN uv pip install --no-cache-dir --system --break-system-packages numpy pillow scipy pytesseract aiohttp

# Download and extract RPCS3 AppImage
RUN curl -L -J -o /tmp/rpcs3.AppImage https://rpcs3.net/latest-linux-x64 && \
    chmod +x /tmp/rpcs3.AppImage && \
    cd /tmp && (./rpcs3.AppImage --appimage-extract || true) && \
    mv /tmp/AppDir /opt/rpcs3 && \
    rm -f /tmp/rpcs3.AppImage /tmp/squashfs-root && \
    ln -s /opt/rpcs3/usr/bin/rpcs3 /usr/local/bin/rpcs3

# Copy automation scripts
COPY config.py pack.py launch.py test_map.py test_multiplayer.py test_autoplay.py test_korea.py test_korea_play.py test_korea_soak.py test_korea_gdb.py test_korea_bp_probe.py test_gdb_smoke.py gdb_client.py entrypoint.sh /civrev/rpcs3_automation/

# Project files (fpk.py, generate_map_textures.py, Pak9/) are mounted at runtime
# RPCS3 config dir (with game data) is mounted at runtime

WORKDIR /civrev/rpcs3_automation
ENTRYPOINT ["/civrev/rpcs3_automation/entrypoint.sh"]
