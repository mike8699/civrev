import argparse

import matplotlib.pyplot as plt
import numpy as np

# Define the map size (32x32)
map_size = 32

terrain_colors: dict[int, tuple[int, int, int]] = {
    0x00: (0, 0, 139),  # Ocean (Dark Blue - deeper look)
    0x01: (124, 252, 0),  # Grassland (Lawn Green - brighter than forest)
    0x02: (238, 232, 170),  # Plains (Pale Goldenrod)
    0x03: (105, 105, 105),  # Mountains (Dim Gray - more rugged)
    0x04: (34, 139, 34),  # Forest (Forest Green)
    0x05: (210, 180, 140),  # Desert (Tan)
    0x06: (160, 160, 160),  # Hills (Medium Gray)
    0x07: (240, 248, 255),  # Ice (Alice Blue)
    0x13: (
        60,
        179,
        113,
    ),  # Forested coastline (Medium Sea Green - natural + near water)
    0x21: (144, 238, 144),  # Grassland w/ river left (Light Green)
    0x41: (102, 205, 170),  # Grassland w/ river on right + top (Medium Aquamarine)
    0x42: (255, 218, 185),  # Plains w/ river right (Peach Puff - warm, soft)
    0x43: (107, 142, 35),  # Grassland w/ river right (Olive Drab - earthy variation)
    0x44: (139, 115, 85),  # Mountain w/ river right (Brownish-gray)
    0x45: (244, 164, 96),  # Desert w/ river + coastline (Sandy Brown)
    0x46: (120, 110, 100),  # Mountain w/ river right (Cool Slate Brown)
    0x81: (46, 139, 87),  # Grassland w/ coast left (Sea Green)
    0x82: (
        222,
        184,
        135,
    ),  # Plains w/ river on bottom (Burly Wood - warm earth tone with a soft, natural feel)
    0x83: (128, 128, 105),  # Hill w/ river bottom left (Gray-Green - terrain + water)
    0x84: (112, 128, 144),  # Mountain w/ river left + bottom (Slate Gray)
    0x86: (100, 100, 120),  # Mountain with river on bottom (Cool Slate)
    0xA4: (
        123,
        108,
        135,
    ),  # Hill with river on bottom, mountain on left (Dusty Purple-Gray)
    0xC2: (
        210,
        180,
        160,
    ),  # Plains w/ river on bottom and right (Dusty Beige - softened earth tone with water influence)
}


# Function to parse the binary file
def parse_map_binary(binary_map_path: str) -> np.ndarray:
    with open(binary_map_path, "rb") as f:
        data = f.read()[:0x400:]  # Read the relevant data (0x400 bytes)

    # Map the data (0x400 bytes) to a 32x32 grid
    map_data = np.frombuffer(data, dtype=np.uint8).reshape((map_size, map_size))

    return map_data


def render_map(map_data: np.ndarray) -> None:
    terrain_image = np.zeros((map_size, map_size, 3), dtype=np.uint8)
    unknown_coords = []

    for row in range(map_size):
        for col in range(map_size):
            terrain_value = map_data[row, col]

            rgb_value = terrain_colors.get(terrain_value, None)
            if rgb_value is not None:
                terrain_image[row, col] = rgb_value
            else:
                terrain_image[row, col] = [128, 0, 128]
                unknown_coords.append((row, col, terrain_value))

    # Flip and rotate the map image
    terrain_image = np.flipud(terrain_image)
    terrain_image = np.rot90(terrain_image, k=3)

    plt.imshow(terrain_image)
    plt.axis("off")

    # Correct text placement: apply same transformation to coordinates
    for row, col, val in unknown_coords:
        # Step 1: Flip vertically
        flipped_row = map_size - 1 - row
        # Step 2: Rotate 90° clockwise
        x = map_size - 1 - flipped_row
        y = col

        plt.text(
            x,
            y,
            f"{hex(val)}",
            color="white",
            ha="center",
            va="center",
            fontsize=6,
            weight="bold",
            bbox=dict(facecolor="black", alpha=0.5, boxstyle="round,pad=0.2"),
        )

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize a CivRev .map file.")
    parser.add_argument(
        "-m",
        "--map-file",
        type=str,
        help="Path to the binary map file.",
        default="Pak9/the_world.map",
        required=False,
    )
    args = parser.parse_args()

    map_file: str = args.map_file

    map_data = parse_map_binary(map_file)
    render_map(map_data)
