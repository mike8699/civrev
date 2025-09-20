#!/usr/bin/env python3
import os

import numpy as np
import pytesseract
from desmume.emulator import DeSmuME, DeSmuME_SDL_Window
from PIL import Image, ImageDraw


def setup_emulator():
    """Initialize the DeSmuMe emulator"""
    emu = DeSmuME()
    emu.open("civrev.nds")

    # Create SDL window to display the game
    window = emu.create_sdl_window()

    return emu, window


def press_key(emu, window, key, duration=0.1):
    """Press a key for a given duration"""
    emu.input.keypad_add_key(key)
    advance_frames(emu, window, int(60 * duration))  # Convert duration to frames
    emu.input.keypad_rm_key(key)
    advance_frames(emu, window, 1)


def touch_screen(emu: DeSmuME, window: DeSmuME_SDL_Window, x, y, duration=0.1):
    """Touch the screen at a specific position"""
    emu.input.touch_set_pos(x, y)
    advance_frames(emu, window, int(60 * duration))
    emu.input.touch_release()
    advance_frames(emu, window, 5)


def advance_frames(emu: DeSmuME, window: DeSmuME_SDL_Window, frames=60):
    """Advance the emulator by a number of frames"""
    for _ in range(frames):
        emu.cycle()
        window.draw()  # Update the SDL window display
        window.process_input()


def detect_text_in_screenshot(emu, search_text="Catherine"):
    """Use OCR to detect if specific text is visible on screen"""
    screenshot = emu.screenshot()

    # Convert to format better for OCR (grayscale, higher contrast)
    screenshot = screenshot.convert("L")  # Convert to grayscale

    # Use OCR to extract text
    try:
        text = pytesseract.image_to_string(screenshot, config="--psm 11")
        print(
            f"OCR detected text: {text[:100]}..."
        )  # Print first 100 chars for debugging
        return search_text.lower() in text.lower()
    except Exception as e:
        print(f"OCR error: {e}")
        return False


def navigate_to_game_start(emu: DeSmuME, window):
    """Navigate through menus to start a game as Russians using touch screen"""
    print("Starting game navigation using touch screen...")

    # Wait for initial loading
    print("Waiting for game to load...")
    advance_frames(emu, window, 250)  # 10 seconds at 60fps

    # Take screenshot to see current state
    capture_screenshot(emu, "debug_1_menu.png")

    # Touch "Start A New Game" button
    print("Touching 'Start A New Game'...")
    touch_screen(emu, window, 128, 40)
    advance_frames(emu, window, 50)

    # Now at game type selection (Random Map, Play A Scenario, etc.)
    capture_screenshot(emu, "debug_2_game_type.png")

    # Touch "Random Map" (first option)
    print("Selecting 'Random Map'...")
    touch_screen(emu, window, 128, 40)
    advance_frames(emu, window, 50)

    # Now at difficulty selection
    capture_screenshot(emu, "debug_3_difficulty.png")

    # Select difficulty (Deity to avoid tutorials)
    print("Selecting Deity difficulty...")
    # advance_frames(emu, window, 500)
    # Deity is at the bottom of the list, need to scroll or touch lower
    touch_screen(emu, window, 128, 180)  # Touch Deity at bottom to select it
    advance_frames(emu, window, 60)

    # Now confirm the Deity selection
    print("Confirming Deity selection...")
    touch_screen(emu, window, 128, 180)  # Touch again to confirm
    advance_frames(emu, window, 180)

    advance_frames(emu, window, 60)

    # NOW we should be at civilization selection
    capture_screenshot(emu, "debug_4_civ_select.png")

    # advance_frames(emu, window, 3000)

    # Navigate through civilizations to find Russians (Catherine)
    print("Looking for Russians (Catherine)...")
    max_attempts = 20  # Maximum civilizations to cycle through
    found_russians = False

    for i in range(max_attempts):
        # Check if Catherine is visible
        if detect_text_in_screenshot(emu, "Catherine"):
            print(f"Found Catherine/Russians after {i} clicks!")
            found_russians = True
            capture_screenshot(emu, "debug_5_catherine_found.png")
            break

        # Not found yet, go to next civilization
        print(f"Checking civilization {i + 1}...")
        # Touch the right arrow to go to next civilization
        touch_screen(emu, window, 220, 100)  # Right arrow position
        advance_frames(emu, window, 30)

        if i == 9:  # Take a screenshot after 10 attempts
            capture_screenshot(emu, "debug_6_still_searching.png")

    if not found_russians:
        print("Warning: Could not find Catherine/Russians, proceeding anyway...")
        capture_screenshot(emu, "debug_7_no_russians.png")
    else:
        # Select Russians by touching the center
        print("Selecting Russians...")
        touch_screen(emu, window, 128, 120)  # Touch center to select
        advance_frames(emu, window, 180)
        capture_screenshot(emu, "debug_7_russians_selected.png")

    # Confirm selection
    print("Confirming civilization selection...")
    touch_screen(emu, window, 128, 160)  # Touch bottom area for confirm
    advance_frames(emu, window, 300)

    # May have additional options (era, etc.)
    print("Accepting any additional options...")
    touch_screen(emu, window, 128, 160)
    advance_frames(emu, window, 300)

    # Game should be loading now
    print("Waiting for game to fully load...")
    advance_frames(emu, window, 900)  # 15 seconds for game world to load

    # Take final screenshot
    capture_screenshot(emu, "debug_8_in_game.png")
    print("Navigation complete - check debug screenshots to verify game state")


def capture_screenshot(emu, filename="screenshot.png"):
    """Capture a screenshot from the emulator"""
    img = emu.screenshot()  # Already returns a PIL Image
    img = img.convert("RGB")
    img.save(filename)
    print(f"Screenshot saved to {filename}")
    return img


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


def extract_tile_regions(screenshot, tile_size=32):
    """Extract potential tile regions from the screenshot"""
    width, height = screenshot.size
    tiles = []

    # The NDS screen is 256x192 pixels per screen
    # Civ Rev uses the bottom screen for the map
    # Let's focus on the bottom screen area
    bottom_screen_y = height // 2 if height > 192 else 0

    # Extract tiles in a grid pattern
    for y in range(bottom_screen_y, height - tile_size, tile_size):
        for x in range(0, width - tile_size, tile_size):
            tile = screenshot.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(
                {
                    "image": tile,
                    "position": (x, y),
                    "coords": (x, y, x + tile_size, y + tile_size),
                }
            )

    return tiles


def compare_tile_with_tileset(tile_img, tileset_img, tile_size=32):
    """Compare a tile from the game with regions in a tileset image"""
    tileset_width, tileset_height = tileset_img.size
    tile_array = np.array(tile_img)

    best_match = None
    best_score = float("inf")

    # Scan through the tileset
    for y in range(
        0, tileset_height - tile_size + 1, 4
    ):  # Step by 4 pixels for efficiency
        for x in range(0, tileset_width - tile_size + 1, 4):
            region = tileset_img.crop((x, y, x + tile_size, y + tile_size))
            region_array = np.array(region)

            # Ensure both arrays have the same shape
            if tile_array.shape == region_array.shape:
                # Calculate difference
                diff = np.mean(
                    np.abs(tile_array.astype(float) - region_array.astype(float))
                )

                if diff < best_score:
                    best_score = diff
                    best_match = {"position": (x, y), "score": diff}

    return best_match


def analyze_tiles(screenshot, tilesets):
    """Analyze tiles in the screenshot and match them with tilesets"""
    print("\nAnalyzing tiles in screenshot...")

    # Try different tile sizes (Civ Rev might use 16x16, 32x32, or other sizes)
    tile_sizes = [16, 24, 32, 48]

    results = {}

    for tile_size in tile_sizes:
        print(f"\nTrying tile size: {tile_size}x{tile_size}")
        tiles = extract_tile_regions(screenshot, tile_size)

        matches = []
        for tile_data in tiles[:10]:  # Analyze first 10 tiles as sample
            tile_img = tile_data["image"]

            for tileset_name, tileset_img in tilesets.items():
                match = compare_tile_with_tileset(tile_img, tileset_img, tile_size)

                if match and match["score"] < 50:  # Threshold for good match
                    matches.append(
                        {
                            "tile_position": tile_data["position"],
                            "tileset": tileset_name,
                            "tileset_position": match["position"],
                            "score": match["score"],
                            "tile_size": tile_size,
                        }
                    )

        if matches:
            results[tile_size] = matches
            print(f"Found {len(matches)} potential matches with tile size {tile_size}")

    return results


def save_analysis_results(results, screenshot):
    """Save analysis results with visual annotations"""
    if not results:
        print("No matches found")
        return

    # Create annotated image
    annotated = screenshot.copy()
    draw = ImageDraw.Draw(annotated)

    # Draw rectangles around matched tiles
    for tile_size, matches in results.items():
        for match in matches[:20]:  # Limit to first 20 matches for clarity
            x, y = match["tile_position"]
            draw.rectangle([x, y, x + tile_size, y + tile_size], outline="red", width=2)
            # Add label
            draw.text((x, y - 10), f"{match['tileset'][:10]}", fill="yellow")

    annotated.save("annotated_screenshot.png")
    print("Saved annotated screenshot to annotated_screenshot.png")

    # Save detailed results to text file
    with open("tile_analysis_results.txt", "w") as f:
        f.write("Tile Analysis Results\n")
        f.write("=" * 50 + "\n\n")

        for tile_size, matches in results.items():
            f.write(f"Tile Size: {tile_size}x{tile_size}\n")
            f.write(f"Number of matches: {len(matches)}\n")
            f.write("-" * 30 + "\n")

            for match in matches[:10]:  # Save first 10 matches per size
                f.write(f"  Game position: {match['tile_position']}\n")
                f.write(f"  Tileset: {match['tileset']}\n")
                f.write(f"  Tileset position: {match['tileset_position']}\n")
                f.write(f"  Match score: {match['score']:.2f}\n")
                f.write("\n")

            f.write("\n")

    print("Saved analysis results to tile_analysis_results.txt")


def main():
    """Main function to run the tile analysis"""
    print("Starting Civilization Revolution tile analysis...")

    # Load tilesets
    tilesets = load_tileset_images()
    print(f"\nLoaded {len(tilesets)} tilesets")

    # Setup emulator
    print("\nSetting up emulator...")
    emu, window = setup_emulator()

    # Navigate to game start
    navigate_to_game_start(emu, window)

    # Wait a bit more for the game world to render
    print("\nWaiting for world to render...")
    advance_frames(emu, window, 180)  # 3 more seconds

    # Capture screenshot
    print("\nCapturing screenshot...")
    screenshot = capture_screenshot(emu, "game_screenshot.png")

    # Also capture just the bottom screen (main game view)
    # The screenshot contains both screens stacked vertically
    # NDS resolution is 256x192 per screen, so total is 256x384
    # Bottom screen starts at y=192
    if screenshot.height >= 384:
        bottom_img = screenshot.crop((0, 192, 256, 384))
    else:
        bottom_img = screenshot  # Use full screenshot if size is unexpected
    bottom_img.save("bottom_screen.png")
    print("Saved bottom screen to bottom_screen.png")

    # Analyze tiles
    results = analyze_tiles(bottom_img, tilesets)

    # Save results
    save_analysis_results(results, bottom_img)

    print("\nAnalysis complete!")

    # Clean up
    emu.destroy()


if __name__ == "__main__":
    main()
