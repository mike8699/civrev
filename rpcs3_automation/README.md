# RPCS3 Map Testing Automation

Automates packing DLC, launching RPCS3, and capturing screenshots for Civilization Revolution map testing. Runs in Docker with a virtual display.

## Quick Start

```bash
cd rpcs3_automation

# Build & run (generates textures + packs + launches + screenshots)
./docker_run.sh -g

# Just pack, no RPCS3 launch
./docker_run.sh --pack-only

# Custom timeout
./docker_run.sh -g -w 180
```

The screenshot lands in `rpcs3_automation/output/screenshot.png`.

## How It Works

1. Docker container extracts your RPCS3 AppImage, installs Mesa for software rendering
2. Xvfb provides a virtual display (`:99`) — nothing touches your real desktop
3. `fpk.py repack` packs `Pak9/` and installs to the RPCS3 game directory
4. RPCS3 launches in the virtual display
5. Frame polling detects when loading finishes (stable non-black frames)
6. Screenshot is captured and saved to `/output/`

## Prerequisites

- Docker
- RPCS3 AppImage on your Desktop
- Game installed in `~/.config/rpcs3/` (BLUS30130)

## Files

- `Dockerfile` — Container with RPCS3 + Mesa + Xvfb
- `docker_run.sh` — Build & run convenience script
- `entrypoint.sh` — Starts Xvfb, runs test
- `config.py` — Paths (auto-detects Docker vs host)
- `pack.py` — Repacks Pak9/ and installs to RPCS3
- `launch.py` — Launches RPCS3, waits for stable frame, captures screenshot
- `test_map.py` — End-to-end orchestrator

## Notes

- RPCS3 runs with Mesa software rendering inside Docker. This is slower than GPU but avoids GPU passthrough complexity.
- If you need GPU acceleration, add `--gpus all` to the `docker run` command in `docker_run.sh` (requires NVIDIA Container Toolkit).
- The boot timeout defaults to 120s. Software rendering is slow, so increase with `-w 300` if needed.
