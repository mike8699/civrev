import math
from pathlib import Path

from ndspy import color
from ndspy.rom import NintendoDSRom
from PIL import Image


def tileset_to_image(rom: NintendoDSRom, tileset: str) -> Image.Image:
    image_data = rom.getFileByName(f"terrain/3dtilesets/{tileset}.ntft")
    palette = color.loadPalette(rom.getFileByName(f"terrain/3dtilesets/{tileset}.ntfp"))

    print(f"Image data length: {len(image_data)}")
    print(f"Palette length: {len(palette)}")
    print(f"Expected pixels (256*128): {256 * 128}")

    # Check pixel values range
    max_pixel_value = max(image_data) if image_data else 0
    print(f"Max pixel value: {max_pixel_value}")

    # 4-bit format means each byte contains 2 pixels
    # So actual pixel count is len(image_data) * 2
    actual_pixels = len(image_data) * 2
    print(f"Actual pixel count (4-bit): {actual_pixels}")

    # Calculate dimensions for 4-bit format
    if actual_pixels == 256 * 128:
        width, height = 256, 128
    elif actual_pixels == 128 * 128:
        width, height = 128, 128
    elif actual_pixels % 128 == 0:
        width, height = actual_pixels // 128, 128
    else:
        width = int(math.sqrt(actual_pixels))
        height = actual_pixels // width

    print(f"Using dimensions: {width}x{height}")
    print()

    img = Image.new("RGB", (width, height), (0, 0, 0))
    for y in range(height):
        for x in range(width):
            pixel_index = y * width + x
            byte_index = pixel_index // 2

            if byte_index < len(image_data):
                byte_value = image_data[byte_index]

                # Extract 4-bit pixel value
                if pixel_index % 2 == 0:
                    pixel_value = byte_value & 0x0F  # Lower 4 bits
                else:
                    pixel_value = (byte_value & 0xF0) >> 4  # Upper 4 bits

                if pixel_value < len(palette):
                    px = palette[pixel_value]
                    # RGB values are off by a factor of 8 in ndspy 4.0.0 for some reason
                    px = (px[0] * 8, px[1] * 8, px[2] * 8)
                    img.putpixel((x, y), px)

    return img


def break_into_tiles(image: Image.Image, tile_size: int = 32) -> list[Image.Image]:
    """Break an image into tile_size x tile_size sub-images."""
    width, height = image.size
    tiles = []

    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            # Calculate actual tile dimensions (handle edge cases)
            tile_width = min(tile_size, width - x)
            tile_height = min(tile_size, height - y)

            # Extract the tile
            tile = image.crop((x, y, x + tile_width, y + tile_height))
            tiles.append(tile)

    return tiles


if __name__ == "__main__":
    rom = NintendoDSRom.fromFile("civrev.nds")

    for tileset in [
        "Deep_Water_3d",
        "Desert_Alpha_3d",
        # 'Fog',
        "Grass_Alpha_3d",
        "Hills_Alpha_3d",
        "Mountains_Alpha_3d",
        "Plains_Alpha_3d",
        "Rivers_Alpha_3d",
        "Trees_Alpha_3d",
        "Water_Grass_3d",
        "Water_Ice_3d",
    ]:
        img = tileset_to_image(rom, tileset)
        tiles = break_into_tiles(img, 32)

        print(f"Image size: {img.size}")
        print(f"Number of tiles: {len(tiles)}")

        dest = Path(__file__).parent / "nds_terrain_tiles"
        dest.mkdir(exist_ok=True)

        for i, tile in enumerate(tiles):  # Show first 4 tiles
            tile.save(str(dest / f"{tileset}_{i}.png"))
