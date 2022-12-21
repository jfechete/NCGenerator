from PIL import Image
import data_classes
import generator

INPUT_FILE = "in.png"
POINTS_VISUALIZE_COLOR = (255, 0, 0)

def main():
    image = Image.open(INPUT_FILE)
    points = data_classes.Points.from_binary_image(image)
    points.visualize_points(image, POINTS_VISUALIZE_COLOR)

if __name__ == "__main__":
    main()
