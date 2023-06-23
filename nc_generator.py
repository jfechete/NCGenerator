from PIL import Image
import data_classes
import generator

INPUT_FILE = "in.png"
OUTPUT_FILE = "out.nc"
POINTS_VISUALIZE_COLOR = (255, 0, 0)
PATH_VISUALIZE_COLOR = (0, 255, 0)
PATH_VISUALIZE_FIRST_COLOR = (0, 0, 255)
DEPTH = 2
SIZE = 100

def main():
    image = Image.open(INPUT_FILE)
    heightmap = data_classes.Heightmap.from_image(image)

    nc_generator = generator.Generator(SIZE/max(image.size), 2)
    nc_generator.carve_heigtmap(heightmap, 0, DEPTH, both_directions=True)
    nc_generator.export(OUTPUT_FILE)

if __name__ == "__main__":
    main()
