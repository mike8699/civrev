#!/usr/bin/env python3
import json
import os

import numpy as np
from desmume.emulator import DeSmuME, DeSmuME_SDL_Window
from PIL import Image, ImageDraw


def setup_emulator():
    """Initialize the DeSmuMe emulator"""
    emu = DeSmuME()
    emu.open("civrev.nds")
    window = emu.create_sdl_window()
    return emu, window


def advance_frames(emu: DeSmuME, window: DeSmuME_SDL_Window, frames=60):
    """Advance the emulator by a number of frames"""
    for _ in range(frames):
        emu.cycle()
        window.draw()
        window.process_input()


def press_key(emu, window, key, duration=0.1):
    """Press a key for a given duration"""
    emu.input.keypad_add_key(key)
    advance_frames(emu, window, int(60 * duration))
    emu.input.keypad_rm_key(key)
    advance_frames(emu, window, 1)


def touch_screen(emu: DeSmuME, window: DeSmuME_SDL_Window, x, y, duration=0.1):
    """Touch the screen at a specific position"""
    emu.input.touch_set_pos(x, y)
    advance_frames(emu, window, int(60 * duration))
    emu.input.touch_release()
    advance_frames(emu, window, 5)


def quick_start_game(emu: DeSmuME, window):
    """Quickly start a game with minimal navigation"""
    print("Quick starting game...")

    # Wait for initial loading
    print("Waiting for game to load...")
    advance_frames(emu, window, 300)  # 5 seconds

    # Touch "Start A New Game"
    print("Starting new game...")
    touch_screen(emu, window, 128, 40)
    advance_frames(emu, window, 60)

    # Touch "Random Map"
    print("Selecting Random Map...")
    touch_screen(emu, window, 128, 40)
    advance_frames(emu, window, 60)

    # Select first difficulty
    print("Selecting difficulty...")
    touch_screen(emu, window, 128, 40)
    advance_frames(emu, window, 60)
    touch_screen(emu, window, 128, 40)  # Confirm
    advance_frames(emu, window, 60)

    # Select first civilization
    print("Selecting civilization...")
    touch_screen(emu, window, 128, 120)
    advance_frames(emu, window, 180)

    # Confirm all
    touch_screen(emu, window, 128, 160)
    advance_frames(emu, window, 300)
    touch_screen(emu, window, 128, 160)
    advance_frames(emu, window, 300)

    # Wait for game to load
    print("Waiting for game to load...")
    advance_frames(emu, window, 600)  # 10 seconds


def capture_screens(emu):
    """Capture both screens and split them"""
    full_screen = emu.screenshot()

    # NDS has two 256x192 screens
    if full_screen.height >= 384:
        top_screen = full_screen.crop((0, 0, 256, 192))
        bottom_screen = full_screen.crop((0, 192, 256, 384))
    else:
        top_screen = full_screen
        bottom_screen = full_screen

    return top_screen, bottom_screen


def load_tileset_images():
    """Load all tileset images from nds_terrain_tiles directory"""
    tilesets = {}
    tiles_dir = "nds_terrain_tiles"

    for filename in os.listdir(tiles_dir):
        if filename.endswith(".png"):
            filepath = os.path.join(tiles_dir, filename)
            img = Image.open(filepath)
            tilename = filename.replace(".png", "")
            tilesets[tilename] = img
            print(f"Loaded tileset: {tilename} - Size: {img.size}")

    return tilesets


def analyze_tile_at_position(image, x, y, tile_size, tilesets):
    """Analyze a specific tile position against all tilesets"""
    if x + tile_size > image.width or y + tile_size > image.height:
        return None

    tile = image.crop((x, y, x + tile_size, y + tile_size))
    tile_array = np.array(tile.convert("RGB"))

    results = {}

    for tileset_name, tileset_img in tilesets.items():
        tileset_width, tileset_height = tileset_img.size
        best_score = float("inf")
        best_pos = None

        # Scan tileset in steps
        step = 1  # Check every pixel for accuracy
        for ty in range(0, tileset_height - tile_size + 1, step):
            for tx in range(0, tileset_width - tile_size + 1, step):
                region = tileset_img.crop((tx, ty, tx + tile_size, ty + tile_size))
                region_array = np.array(region.convert("RGB"))

                if tile_array.shape == region_array.shape:
                    diff = np.mean(
                        np.abs(tile_array.astype(float) - region_array.astype(float))
                    )

                    if diff < best_score:
                        best_score = diff
                        best_pos = (tx, ty)

        results[tileset_name] = {"score": best_score, "position": best_pos}

    # Return the best matching tileset
    best_tileset = min(results.items(), key=lambda x: x[1]["score"])
    return {
        "tileset": best_tileset[0],
        "score": best_tileset[1]["score"],
        "tileset_position": best_tileset[1]["position"],
    }


def analyze_screen_tiles(image, tile_size, tilesets):
    """Analyze all tiles in a screen"""
    print(f"\nAnalyzing tiles of size {tile_size}x{tile_size}...")

    cols = image.width // tile_size
    rows = image.height // tile_size

    grid = []

    for row in range(rows):
        row_data = []
        for col in range(cols):
            x = col * tile_size
            y = row * tile_size

            result = analyze_tile_at_position(image, x, y, tile_size, tilesets)
            row_data.append(result)

            if result and col % 4 == 0 and row % 2 == 0:  # Sample output
                print(
                    f"  Tile at ({col},{row}): {result['tileset'][:10]} (score: {result['score']:.1f})"
                )

        grid.append(row_data)

    return grid


def visualize_grid(grid, tile_size, output_file):
    """Create a visual representation of the tile grid"""
    if not grid or not grid[0]:
        return

    rows = len(grid)
    cols = len(grid[0])

    # Create color map for different tilesets
    colors = {
        "Deep_Water_3d": (0, 0, 200),
        "Desert_Alpha_3d": (255, 200, 100),
        "Grass_Alpha_3d": (0, 200, 0),
        "Hills_Alpha_3d": (150, 100, 50),
        "Mountains_Alpha_3d": (100, 100, 100),
        "Plains_Alpha_3d": (200, 200, 100),
        "Rivers_Alpha_3d": (0, 100, 200),
        "Trees_Alpha_3d": (0, 100, 0),
        "Water_Grass_3d": (0, 150, 150),
        "Water_Ice_3d": (200, 200, 255),
        None: (255, 255, 255),
    }

    # Create image
    img_width = cols * tile_size
    img_height = rows * tile_size
    img = Image.new("RGB", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    for row_idx, row in enumerate(grid):
        for col_idx, tile_info in enumerate(row):
            x = col_idx * tile_size
            y = row_idx * tile_size

            if tile_info and tile_info["score"] < 30:  # Only show good matches
                tileset = tile_info["tileset"]
                color = colors.get(tileset, (255, 255, 255))
                draw.rectangle(
                    [x, y, x + tile_size - 1, y + tile_size - 1],
                    fill=color,
                    outline=(0, 0, 0),
                )

    img.save(output_file)
    print(f"Saved grid visualization to {output_file}")


def save_grid_data(grid, tile_size, output_file):
    """Save grid data to JSON for further analysis"""
    data = {
        "tile_size": tile_size,
        "rows": len(grid),
        "cols": len(grid[0]) if grid else 0,
        "grid": [],
    }

    for row in grid:
        row_data = []
        for tile_info in row:
            if tile_info:
                row_data.append(
                    {
                        "tileset": tile_info["tileset"],
                        "score": float(tile_info["score"]),
                        "pos": tile_info["tileset_position"],
                    }
                )
            else:
                row_data.append(None)
        data["grid"].append(row_data)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved grid data to {output_file}")


def main():
    """Main function"""
    print("Starting Civilization Revolution tile analysis (simple version)...")

    # Load tilesets
    tilesets = load_tileset_images()
    print(f"\nLoaded {len(tilesets)} tilesets")

    # Setup emulator
    print("\nSetting up emulator...")
    emu, window = setup_emulator()

    try:
        # Start game quickly
        quick_start_game(emu, window)

        # Capture screens
        print("\nCapturing screens...")
        top_screen, bottom_screen = capture_screens(emu)

        top_screen.save("current_top_screen.png")
        bottom_screen.save("current_bottom_screen.png")
        print("Saved current screens")

        # Analyze different tile sizes
        # NDS commonly uses 8x8 or 16x16 tiles
        tile_sizes = [8, 16, 32]

        for tile_size in tile_sizes:
            print(f"\n{'=' * 50}")
            print(f"Analyzing with tile size {tile_size}x{tile_size}")

            # Analyze bottom screen (map view)
            grid = analyze_screen_tiles(bottom_screen, tile_size, tilesets)

            # Save results
            visualize_grid(grid, tile_size, f"grid_visual_{tile_size}.png")
            save_grid_data(grid, tile_size, f"grid_data_{tile_size}.json")

            # Print summary
            if grid and grid[0]:
                tileset_counts = {}
                good_matches = 0

                for row in grid:
                    for tile_info in row:
                        if tile_info and tile_info["score"] < 30:
                            good_matches += 1
                            tileset_counts[tile_info["tileset"]] = (
                                tileset_counts.get(tile_info["tileset"], 0) + 1
                            )

                print(f"\nSummary for {tile_size}x{tile_size}:")
                print(f"  Good matches: {good_matches}/{len(grid) * len(grid[0])}")
                print("  Tileset distribution:")
                for tileset, count in sorted(
                    tileset_counts.items(), key=lambda x: -x[1]
                )[:5]:
                    print(f"    {tileset}: {count}")

        print("\n" + "=" * 50)
        print("Analysis complete! Check the output files.")

    finally:
        # Clean up
        emu.destroy()
        print("\nEmulator closed.")


if __name__ == "__main__":
    main()
