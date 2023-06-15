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
    def paths_from_points(points, min_path_length = 2):
        """
        Creates a Paths that goes through neighboring points.
        It creates Path objects until every neighbor has been connected.
        Also accepts a min_path_length parameter that must be at least 2. Any paths smaller than this are not added. This is used because sometimes 2 Path objects can get close to each other, but never actually connect, so many small Path objects are created to connect them, which may not be desirable since the difference may not be noticeable but add more CNC cutting time.
        """
        if min_path_length < 2:
            raise ValueError("Parameter min_path_length must be at least 2")
        paths = Paths([])

        unexpandable_points = []
        for point in points:
            if point in unexpandable_points:
                continue

            #explore current Point in Points
            path, cur_expandable, cur_unexpandable = Path.path_from_points(
                points, start_point = point,
                explored_paths = paths, allow_loop = True,
                return_affected_points = True
            )
            if len(path) > 1:
                paths.add_path(path)
            unexpandable_points += [p for p in cur_unexpandable if p not in unexpandable_points]
            expandable_points = [p for p in cur_expandable if p not in unexpandable_points]

            #explore any possible branches from that point
            while len(expandable_points) > 0:
                cur_point = expandable_points.pop(0)
                path, cur_expandable, cur_unexpandable = Path.path_from_points(
                    points, start_point = cur_point,
                    explored_paths = paths, allow_loop = True,
                    return_affected_points = True
                )
                if len(path) > 1:
                    paths.add_path(path)
                unexpandable_points += [p for p in cur_unexpandable if p not in unexpandable_points]
                expandable_points += [p for p in cur_expandable if p not in expandable_points]
                expandable_points = [p for p in expandable_points if p not in unexpandable_points]

        #need to filter at the end so that if a connection was found in a small Path, it doesn't infinite loop for not saving that Path
        paths = Paths([path for path in paths if len(path) >= min_path_length])
        return paths

    def compress(self, **kwargs):
        for path in self._path_list:
            path.compress(**kwargs)

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

    def has_connection(self, point_a, point_b, max_dist = 1):
        for path in self:
            if path.has_connection(point_a, point_b, max_dist):
                return True
        return False

    def __iter__(self):
        return iter(self._path_list)

class Points:
    def __init__(self, point_list):
        self._point_list = point_list

    @staticmethod
    def from_image_color_edge(pil_img):
        """
        Returns a Points object showing the outline all color edges in the image.
        The border is on the side with the brighter color.
        In order to get the brighter color, the image is converted to grayscale. If two color convert to the same grayscale color, edges won't be detected.
        """
        if pil_img.mode != "L":
            pil_img = pil_img.convert("L")

        point_list = []
        for x in range(pil_img.width):
            for y in range(pil_img.height):
                color = pil_img.getpixel((x,y))
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
                        if neigh_color < color:
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

    def __contains__(self, point):
        return point in self._point_list

    def __len__(self):
        return len(self._point_list)

    def __iter__(self):
        return iter(self._point_list)

class Path:
    def __init__(self, point_list):
        self._point_list = point_list

    @staticmethod
    def path_from_points(points, start_point = None, explored_paths = None, allow_loop = False, return_affected_points = False):
        """
        Creates a path that goes through neighboring points.
        It simply chooses the first available neighbor repeatedly to create a list.
        It does not guarentee that every point will be crossed by the path.
        An optional start_point parameter can be given to define the start point, if not the first will be used.
        Also accepts an optional explore_path parameter which should be a Paths objects. It will prevent making any connections that are already present in one of these paths.
        Also can set allow_loop to True to allow it to end on the same point it started if that's where the path ends up.
        Also can set return_affected_points to True, which means that along with the Path object it will return 2 Points showing all the points in the path. The first shows Point objects that still have unexplored neighbors, while the second shows Point objects that have no unexplored neighbors. Not 100% reliable, as if a point has an unexplored neighbor that is explored later in the path, it will not be moved to the second list.
        """
        if start_point == None:
            start_point = list(points)[0]

        path = [start_point]
        found_connection = True
        if return_affected_points:
            expandable_points = []
            unexpandable_points = []
        while found_connection:
            neighbors = []
            adjacents = []
            for j, point_exploring in enumerate(points):
                if (
                    path[-1].is_neighbor(point_exploring) and
                    point_exploring not in path and
                    # allows distance of 2 so that corners don't connect both the corner piece and diagonal connection.
                    (explored_paths == None or not explored_paths.has_connection(path[-1], point_exploring, 2))
                    ):
                    if path[-1].is_adjacent(point_exploring):
                        adjacents.append(point_exploring)
                        if not return_affected_points:
                            break
                    else:
                        neighbors.append(point_exploring)

            #prioritize adjacent cells to avoid path skipping corners and leaving single points behind
            if len(adjacents) > 0:
                path.append(adjacents.pop())
            elif len(neighbors) > 0:
                path.append(neighbors.pop())
            else:
                found_connection = False

            if return_affected_points:
                if not found_connection:
                    unexpandable_points.append(path[-1])
                elif len(adjacents + neighbors) > 0:
                    expandable_points.append(path[-2])
                else:
                    unexpandable_points.append(path[-2])

            if not found_connection and path[-1].is_neighbor(start_point):
                path.append(start_point)

        if return_affected_points:
            return Path(path), Points(expandable_points), Points(unexpandable_points)
        else:
            return Path(path)

    def compress(self, max_dist = 1):
        max_dist_sqr = max_dist**2
        point_on = 1
        segment_removing = []
        while point_on < len(self._point_list) - 1:
            remove_safe = True
            segment_removing.append(self._point_list[point_on])
            #constructing standard line equation
            a = self._point_list[point_on-1].y-self._point_list[point_on+1].y
            b = self._point_list[point_on+1].x-self._point_list[point_on-1].x
            c = -(
                a*self._point_list[point_on-1].x +
                b*self._point_list[point_on-1].y
            )
            for point_check in segment_removing:
                if a == 0 and b == 0:
                    #getting distance from point
                    dist_sqr = (
                        (self._point_list[point_on-1].x - point_check.x)**2 +
                        (self._point_list[point_on-1].y - point_check.y)**2
                    )
                else:
                    #getting distance from line
                    dist_sqr = (
                        a*point_check.x +
                        b*point_check.y +
                        c
                    )**2
                    dist_sqr /= a**2 + b**2
                #checking if too far
                if dist_sqr > max_dist_sqr:
                    remove_safe = False
                    break
            #deleting point if all in segment close enough
            if remove_safe:
                del self._point_list[point_on]
            else:
                point_on += 1
                segment_removing.clear()

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

        point_count = len(self)
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

    def has_connection(self, point_a, point_b, max_dist = 1):
        for i in range(len(self._point_list)):
            if self._point_list[i] == point_a or self._point_list[i] == point_b:
                for j in range(1, max_dist + 1):
                    if (
                        (self._point_list[i] == point_a and self._point_list[(i+j)%len(self._point_list)] == point_b) or
                        (self._point_list[i] == point_b and self._point_list[(i+j)%len(self._point_list)] == point_a)
                        ):
                        return True
        return False

    def __contains__(self, point):
        return point in self._point_list

    def __len__(self):
        return len(self._point_list)

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

    def is_adjacent(self, other):
        return (
            (abs(self.x - other.x) == 1 and self.y == other.y) or
            (self.x == other.x and abs(self.y - other.y) == 1)
        )

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
