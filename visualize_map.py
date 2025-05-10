import matplotlib.pyplot as plt
import numpy as np

# Define the map size (32x32)
map_size = 32

terrain_colors = {
    0x00: [0, 0, 255],  # Ocean (Deep Blue)
    0x01: [34, 139, 34],  # Grassland (Forest Green)
    0x02: [255, 255, 0],  # Plains (Yellow)
    0x03: [139, 69, 19],  # Mountains (Saddle Brown)
    0x04: [34, 139, 34],  # Forest (Forest Green)
    0x05: [255, 228, 181],  # Desert (Light Khaki)
    0x06: [169, 169, 169],  # Hills (Dark Gray)
    0x07: [255, 250, 250],  # Ice (Snow White)
    0x13: [],  # Trees with a coastline on left, top, and right
    0x21: [144, 238, 144],  # Grassland with river on the left (Light Green)
    0x42: [255, 223, 186],  # Plains with river on the right (Peach)
    0x43: [34, 139, 34],  # Grassland with river on the right (Forest Green)
    0x44: [139, 69, 19],  # Mountain with river on the right (Saddle Brown)
    0x45: [
        255,
        228,
        181,
    ],  # Desert with river on the right and coastline on top (Light Khaki)
    0x46: [],  # Mountain with river on right
    0x81: [70, 130, 180],  # Grassland with coastline on the left (Steel Blue)
    0x83: [],  # Hill with river on bottom left
    0x84: [139, 69, 19],  # Mountain with river on left and bottom (Saddle Brown)
}


# Path to the binary map file
binary_map_path = "Pak9/the_world.map"


# Function to parse the binary file
def parse_map_binary(binary_map_path):
    with open(binary_map_path, "rb") as f:
        data = f.read()[:0x400:]  # Read the relevant data (0x400 bytes)

    # Map the data (0x400 bytes) to a 32x32 grid
    map_data = np.frombuffer(data, dtype=np.uint8).reshape((map_size, map_size))

    return map_data


def render_map(map_data):
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
    # Parse the binary map and render it
    map_data = parse_map_binary(binary_map_path)
    render_map(map_data)
