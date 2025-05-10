import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Define the map size (32x32)
map_size = 32

terrain_names: dict[int, str] = {
    0x0: "Ocean",
    0x1: "Grassland",
    0x2: "Plains",
    0x3: "Mountains",
    0x4: "Forest",
    0x5: "Desert",
    0x6: "Hills",
    0x7: "Ice",
    0x13: "Forested coastline",
    0x21: "Grassland w/ river left",
    0x23: "Forest w/ river bottom right",
    0x41: "Grassland w/ river on right + top",
    0x42: "Plains w/ river right",
    0x43: "Grassland w/ river right",
    0x44: "Mountain w/ river right",
    0x45: "Desert w/ river + coastline",
    0x46: "Mountain w/ river right",
    0x81: "Grassland w/ coast left",
    0x82: "Plains w/ river on bottom",
    0x83: "Hill w/ river bottom left",
    0x84: "Mountain w/ river left + bottom",
    0x86: "Mountain with river on bottom",
    0xA4: "Hill with river on bottom, mountain on left",
    0xC2: "Plains w/ river on bottom and right",
}

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
    0x23: (60, 179, 113),  # Forest w/ river bottom right (Medium Sea Green)
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
    0xC2: (210, 180, 160),  # Plains w/ river on bottom and right (Dusty Beige)
}


# Function to parse the binary file
def parse_map_binary(binary_map_path: str) -> np.ndarray:
    with open(binary_map_path, "rb") as f:
        data = f.read(0x400)  # Read the relevant data (0x400 bytes)

    # Map the data (0x400 bytes) to a 32x32 grid
    map_data = np.frombuffer(data, dtype=np.uint8).reshape((map_size, map_size))

    return map_data


def render_map(map_data: np.ndarray) -> None:
    terrain_image = np.zeros((map_size, map_size, 3), dtype=np.uint8)
    unknown_coords = []
    used_terrains = set()

    for row in range(map_size):
        for col in range(map_size):
            terrain_value = map_data[row, col]

            rgb_value = terrain_colors.get(terrain_value, None)
            if rgb_value is not None:
                terrain_image[row, col] = rgb_value
                used_terrains.add(terrain_value)
            else:
                terrain_image[row, col] = [128, 0, 128]  # Purple for unknown
                unknown_coords.append((row, col, terrain_value))

    # Flip and rotate the map image
    terrain_image = np.flipud(terrain_image)
    terrain_image = np.rot90(terrain_image, k=3)

    plt.figure(figsize=(10, 10))
    plt.imshow(terrain_image)
    plt.axis("off")

    # Add labels for unknown tiles
    for row, col, val in unknown_coords:
        flipped_row = map_size - 1 - row
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

    # Create legend entries
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(
            facecolor=np.array(terrain_colors[tid]) / 255.0,
            edgecolor="black",
            label=terrain_names.get(tid, f"0x{tid:02X}"),
        )
        for tid in sorted(used_terrains)
    ]

    plt.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=3,
        fontsize=8,
        frameon=True,
        framealpha=0.9,
        title="Terrain Legend",
    )

    plt.tight_layout()

    output_path = Path(map_file).with_suffix(".bmp")
    plt.imsave(output_path, terrain_image)
    print(f"Map image exported to {output_path}")

    plt.show()


def convert_bmp_to_map(bmp_file: str) -> None:
    raise NotImplementedError("BMP to MAP conversion is not implemented yet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize or convert a CivRev map file."
    )
    parser.add_argument(
        "-m",
        "--map-file",
        type=str,
        help="Path to the binary map file.",
        required=False,
    )
    parser.add_argument(
        "-b",
        "--bmp-file",
        type=str,
        help="Path to the BMP file.",
        required=False,
    )
    args = parser.parse_args()

    if args.bmp_file and not args.map_file:
        print("Error: --map-file is required when using --bmp-file.")
        parser.print_help()
        exit(1)

    if args.bmp_file and args.map_file:
        convert_bmp_to_map(args.bmp_file)
    else:
        map_file = args.map_file or "Pak9/the_world.map"
        map_data = parse_map_binary(map_file)
        render_map(map_data)
