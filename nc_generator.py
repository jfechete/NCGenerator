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
    points = data_classes.Points.from_binary_image(image)
    
    paths = data_classes.Paths.paths_from_points(points)
    paths.visualize(image, PATH_VISUALIZE_COLOR, PATH_VISUALIZE_FIRST_COLOR)

    nc_generator = generator.Generator(SIZE/max(image.size))
    nc_generator.add_multipass(paths, DEPTH)
    nc_generator.export(OUTPUT_FILE)

if __name__ == "__main__":
    main()
