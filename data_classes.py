import copy
import math
from PIL import Image, ImageDraw

TEMP_GIF_FILE = "temp.gif"
GIF_FPS = 60
MAX_GIF_LINE_FRAMES = 120
DOT_PIXEL_SIZE = 5

class Paths:
    def __init__(self, path_list):
        self._path_list = path_list

    @staticmethod
    def paths_from_points(points):
        """
        Creates a Paths that goes through neighboring points.
        It creates Path objects until every neighbor has been connected.
        """
        paths = Paths([])
        for point in points:
            made_path = True
            while made_path:
                made_path = False
                path = Path.path_from_points(points, start_point = point, explored_paths = paths)
                if len(list(path)) > 1:
                    paths.add_path(path)
                    made_path = True
        return paths

    def visualize(self, background_img, line_color, start_color = None):
        """
        Shows the background image with an animated .gif showing the paths.
        Also saves to a file that isn't deleted, because showing an animated .gif doesn't seem to show the animation.
        """
        background_img = background_img.copy()
        imgs = self.apply_to_img(background_img, line_color, start_color)
        imgs[0].save(TEMP_GIF_FILE, save_all=True, append_images=imgs[1:], duration=1000/GIF_FPS, loop=0)
        anim_img = Image.open(TEMP_GIF_FILE)
        anim_img.show()

    def apply_to_img(self, background_img, line_color, start_color = None):
        """
        Applies the paths to the picture using the color parameters.
        Also returns a list of frames for animation purposes.
        """
        frames = []
        for path in self:
            frames += path.apply_to_img(background_img, line_color, start_color)
        return frames

    def add_path(self, path):
        """
        Adds another Path to this Paths object.
        """
        self._path_list.append(path)

    def has_connection(self, point_a, point_b):
        for path in self:
            if path.has_connection(point_a, point_b):
                return True
        return False

    def __iter__(self):
        return iter(self._path_list)

class Points:
    def __init__(self, point_list):
        self._point_list = point_list

    @staticmethod
    def from_binary_image(pil_img):
        """
        Returns a Points object showing the outline of the white objects in this picture.
        The inner border is used, every point will be on a white pixel.
        """
        if pil_img.mode != "1":
            pil_img = pil_img.convert("1")

        point_list = []
        for x in range(pil_img.width):
            for y in range(pil_img.height):
                color = pil_img.getpixel((x,y))
                if color > 0:
                    neighs = (
                        (x+1, y),
                        (x-1, y),
                        (x, y+1),
                        (x, y-1)
                    )
                    for neigh in neighs:
                        if (neigh[0] >= 0 and neigh[0] < pil_img.width and
                            neigh[1] >= 0 and neigh[1] < pil_img.height):
                            neigh_color = pil_img.getpixel(neigh)
                            if neigh_color == 0:
                                point_list.append(Point(x, y))
                                break

        return Points(point_list)

    def visualize(self, background_img, color):
        """"
        Shows the background image but with every point added to it using the color parameter.
        """
        background_img = background_img.copy()
        self.apply_to_img(background_img, color)
        background_img.show()

    def apply_to_img(self, background_img, color):
        """
        Applies points to the picture using the color parameter
        """
        for point in self:
            point.apply_to_img(background_img, color)

    def __iter__(self):
        return iter(self._point_list)

class Path:
    def __init__(self, point_list):
        self._point_list = point_list

    @staticmethod
    def path_from_points(points, start_point = None, explored_paths = None):
        """
        Creates a path that goes through neighboring points.
        It simply chooses the first available neighbor repeatedly to create a list.
        It does not guarentee that every point will be crossed by the path.
        An optional start_point parameter can be given to define the start point, if not the first will be used.
        Also accepts an optional explore_path parameter which should be a Paths objects. It will prevent making any connections that are already present in one of these paths.
        """
        if start_point == None:
            start_point = list(points)[0]
        
        path = [start_point]
        found_connection = True
        while found_connection:
            found_connection = False
            for point_exploring in points:
                if path[-1].is_neighbor(point_exploring) and point_exploring not in path:
                    if explored_paths == None or not explored_paths.has_connection(path[-1], point_exploring):
                        path.append(point_exploring)
                        found_connection = True
                        break
        return Path(path)
                    

    def visualize(self, background_img, line_color, start_color = None):
        """
        Shows the background image with an animated .gif showing the path.
        Also saves to a file that isn't deleted, because showing an animated .gif doesn't seem to show the animation.
        """
        background_img = background_img.copy()
        imgs = self.apply_to_img(background_img, line_color, start_color)
        imgs[0].save(TEMP_GIF_FILE, save_all=True, append_images=imgs[1:], duration=1000/GIF_FPS, loop=0)
        anim_img = Image.open(TEMP_GIF_FILE)
        anim_img.show()

    def apply_to_img(self, background_img, line_color, start_color = None):
        """
        Applies the path to the picture using the color parameters.
        Also returns a list of frames for animation purposes.
        """
        if start_color == None:
            start_color = line_color

        point_count = len(list(self))
        frames = []
        for i, point in enumerate(self):
            point.apply_to_img(
                background_img, start_color if i == 0 else line_color
            )
            if i % math.ceil(point_count/MAX_GIF_LINE_FRAMES) == 0:
                frames.append(background_img.copy())
        return frames

    def get_first_point(self):
        return self._point_list[0]

    def has_connection(self, point_a, point_b):
        for i in range(len(self._point_list) - 1):
            if (self._point_list[i] == point_a and self._point_list[i+1] == point_b or
                self._point_list[i] == point_b and self._point_list[i+1] == point_a):
                return True
        return False

    def __iter__(self):
        return iter(self._point_list)

class Point:
    def __init__(self, x, y):
        #Coordinates are currently meant to be pixels and integers
        #May be changed in the future as non-image inputs are added
        self.x = x
        self.y = y

    def is_neighbor(self, other):
        return abs(self.x - other.x) <= 1 and abs(self.y - other.y) <= 1 and self != other

    def visualize(self, background_img, color):
        """
        Shows the background image but with the point added to it using the color parameter.
        """
        background_img = background_img.copy()
        self.apply_to_img(background_img, color)
        background_img.show()

    def apply_to_img(self, background_img, color):
        """
        Applies point to the picture using the color parameter
        """
        if DOT_PIXEL_SIZE == 1:
            background_img.putpixel((self.x, self.y), color)
        else:
            draw = ImageDraw.Draw(background_img)
            draw.ellipse((
                self.x+1-DOT_PIXEL_SIZE, self.y+1-DOT_PIXEL_SIZE,
                self.x-1+DOT_PIXEL_SIZE, self.y-1+DOT_PIXEL_SIZE
            ), fill = color)

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "{}, {}".format(self.x, self.y)
