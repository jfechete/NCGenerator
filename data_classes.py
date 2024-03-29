import copy
import math
from PIL import Image, ImageDraw

TEMP_GIF_FILE = "temp.gif"
GIF_FPS = 60
MAX_GIF_LINE_FRAMES = 120
DOT_PIXEL_SIZE = 5

class Heightmap:
    def __init__(self, heightmap_list):
        """
        For now heightmap should be a 2d list, heightmap[row/y][column/x].
        Values should be a float from 0 to 1.
        I chose this since it seems like it would be the easiest to use.
        This does mean that it isn't possible to omit certain positions.
        As such, this is not stable and may change in the future.
        That shouldn't be a problem as most common creation should be using
        from_image, not the constructor.
        """
        self._rows = list(range(len(heightmap_list)))
        self._columns = list(range(len(heightmap_list[0])))
        self._heights = {}
        for y in self._rows:
            for x in self._columns:
                self._heights[(x, y)] = heightmap_list[y][x]

    @staticmethod
    def from_image(pil_img):
        """
        Returns a heightmap created from this image.
        The image is converted to grayscale to create it.
        """
        if pil_img.mode != "L":
            pil_img = pil_img.convert("L")

        heightmap_list = []
        for y in range(pil_img.height):
            heightmap_list.append([])
            for x in range(pil_img.width):
                color = pil_img.getpixel((x,y))
                heightmap_list[y].append(color/255)

        return Heightmap(heightmap_list)

    def get_rows(self):
        """
        Gets all rows with a value.
        """
        return self._rows.copy()

    def get_columns(self):
        """
        Gets all columns with a value.
        """
        return self._columns.copy()

    def get_row(self, row):
        """
        Gets a list of all points along a row.
        Returns a list of tuples with (x, height).
        """
        row_return = []
        for x in self._columns:
            if (x, row) in self._heights:
                row_return .append((x, self._heights[(x,row)]))
        return row_return

    def get_column(self, column):
        """
        Gets a list of all points along a column.
        Returns a list of tuples with (y, height).
        """
        column_return = []
        for y in self._rows:
            if (column, y) in self._heights:
                column_return.append((y, self._heights[(column, y)]))
        return column_return

    def get_rows_max(self, rows):
        """
        Gets a list of points along multiple rows,
        where each height will be the maximum for that column across all
        the given rows.
        Returns a list of tuples with (x, height).
        """
        rows = [self.get_row(row) for row in rows]
        return Heightmap._maximize_points(rows)

    def get_columns_max(self, columns):
        """
        Gets a list of points along multiple columns,
        where each height will be the maximum for that row across all
        the given columns.
        Returns a list of tuples with (y, height).
        """
        columns = [self.get_column(column) for column in columns]
        return Heightmap._maximize_points(columns)

    def visualize(self, background_img, color):
        """"
        Shows the background image, but with the heightmap added to it.
        """
        background_img = background_img.copy()
        background_img = background_img.convert("RGBA")
        self.apply_to_img(background_img, color)
        background_img.show()

    def apply_to_img(self, background_img, color):
        """
        Applies the heightmap to the picture using the color parameter.
        background_img should be mode RGBA.
        """
        image_applying = Image.new(
            "RGBA",
            (background_img.width, background_img.height)
        )
        for y in self.get_rows():
            for x, value in self.get_row(y):
                image_applying.putpixel((x,y), color + (int(value*255),))
        background_img.alpha_composite(image_applying)

    @staticmethod
    def _maximize_points(list_of_points):
        points = sum(list_of_points, [])
        points.sort()
        cr_point = 0
        while cr_point < len(points) - 1:
            if points[cr_point][0] == points[cr_point + 1][0]:
                del points[cr_point]
            else:
                cr_point += 1
        return points


class Paths:
    def __init__(self, path_list):
        self._path_list = path_list

    @staticmethod
    def from_points(points, min_path_length=2):
        """
        Creates a Paths that goes through neighboring points.
        It creates Path objects until every neighbor has been connected.
        Also accepts a min_path_length parameter that must be at least 2,
        any paths smaller than this are not added.
        This is used because sometimes 2 Path objects can get close to each
        other, but never actually connect, so many small Path objects are
        created to connect them, which may not be desirable since the
        difference may not be noticeable but add more CNC cutting time.
        """
        if min_path_length < 2:
            raise ValueError("Parameter min_path_length must be at least 2")
        paths = Paths([])

        unexpandable_points = {}
        for point in points:
            if point.to_tuple() in unexpandable_points:
                continue

            #explore current Point in Points
            path, cr_expandable, cr_unexpandable = Path.from_points(
                points, start_point=point,
                explored_paths=paths, allow_loop=True,
                return_affected_points=True
            )
            if len(path) > 1:
                paths.add_path(path)
            for point in cr_unexpandable:
                unexpandable_points[point.to_tuple()] = True

        #need to filter at the end
        #that way if a connection was found in a small Path,
        #it doesn't infinite loop for not saving that Path
        paths = Paths(
            [path for path in paths if len(path) >= min_path_length]
        )
        return paths

    def compress(self, **kwargs):
        for path in self._path_list:
            path.compress(**kwargs)

    def visualize(self, background_img, line_color, start_color=None):
        """
        Shows the background image with an animated .gif showing the paths.
        Also saves to a file that isn't deleted,
        because showing an animated .gif doesn't seem to show the animation.
        """
        background_img = background_img.copy()
        imgs = self.apply_to_img(background_img, line_color, start_color)
        imgs[0].save(
            TEMP_GIF_FILE, save_all=True, append_images=imgs[1:],
            duration=1000/GIF_FPS, loop=0
        )
        anim_img = Image.open(TEMP_GIF_FILE)
        anim_img.show()

    def apply_to_img(self, background_img, line_color, start_color=None):
        """
        Applies the paths to the picture using the color parameters.
        Also returns a list of frames for animation purposes.
        """
        frames = []
        for path in self:
            frames += path.apply_to_img(
                background_img, line_color, start_color
            )
        return frames

    def add_path(self, path):
        """
        Adds another Path to this Paths object.
        """
        self._path_list.append(path)

    def has_connection(self, point_a, point_b, max_dist=1):
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
        Returns a Points object showing the outline
        of all color edges in the image.
        The border is on the side with the brighter color.
        In order to get the brighter color,
        the image is converted to grayscale.
        If two colors convert to the same grayscale color,
        edges won't be detected.
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
                    if (
                        neigh[0] >= 0 and neigh[0] < pil_img.width and
                        neigh[1] >= 0 and neigh[1] < pil_img.height
                    ):
                        neigh_color = pil_img.getpixel(neigh)
                        if neigh_color < color:
                            point_list.append(Point(x, y))
                            break

        return Points(point_list)

    @staticmethod
    def from_image_trace(pil_img):
        """
        Returns a points object showing the center of
        the lines in the image.
        The image is converted to 1 bit pixels.
        0 is treated as line, and 255 as background.
        """
        if pil_img.mode != "1":
            pil_img = pil_img.convert("1")

        remove_queue = []
        #for optimization so doesn't have to search long list
        remove_queue_dict = {}
        for x in range(pil_img.width):
            for y in range(pil_img.height):
                if (
                    pil_img.getpixel((x,y)) == 0 and
                    is_pixel_unneeded(pil_img, (x,y))
                ):
                    remove_queue.append((x,y))
                    remove_queue_dict[(x,y)] = True

        while len(remove_queue) > 0:
            cr_pixel = remove_queue.pop(0)
            del remove_queue_dict[cr_pixel]
            #checking again incase state changed since removing pixels ahead
            if is_pixel_unneeded(pil_img, cr_pixel):
                pil_img.putpixel(cr_pixel, 255)
                neighs = (
                    (cr_pixel[0], cr_pixel[1]+1),
                    (cr_pixel[0]+1, cr_pixel[1]+1),
                    (cr_pixel[0]+1, cr_pixel[1]),
                    (cr_pixel[0]+1, cr_pixel[1]-1),
                    (cr_pixel[0], cr_pixel[1]-1),
                    (cr_pixel[0]-1, cr_pixel[1]-1),
                    (cr_pixel[0]-1, cr_pixel[1]),
                    (cr_pixel[0]-1, cr_pixel[1]+1),
                )
                for neigh in neighs:
                    if (
                        neigh not in remove_queue_dict and
                        neigh[0] >= 0 and neigh[0] < pil_img.width and
                        neigh[1] >= 0 and neigh[1] < pil_img.height
                    ):
                        if (
                            pil_img.getpixel(neigh) == 0 and
                            is_pixel_unneeded(pil_img, neigh)
                        ):
                            remove_queue.append(neigh)
                            remove_queue_dict[neigh] = True

        point_list = []
        for x in range(pil_img.width):
            for y in range(pil_img.height):
                if pil_img.getpixel((x,y)) == 0:
                    point_list.append(Point(x, y))
        return Points(point_list)

    def visualize(self, background_img, color):
        """"
        Shows the background image,
        but with every point added to it using the color parameter.
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
    def from_points(
        points, start_point=None, explored_paths=None,
        allow_loop=False, return_affected_points=False
    ):
        """
        Creates a path that goes through neighboring points.
        It simply chooses the first available neighbor repeatedly to create
        a list.
        It does not guarentee that every point will be crossed by the path.
        An optional start_point parameter can be given to define the
        start point, if not the first will be used.
        Also accepts an optional explore_path parameter,
        which should be a Paths objects.
        It will prevent making any connections that are already present
        in one of these paths.
        Also can set allow_loop to True to allow it to end on the same point
        it started if that's where the path ends up.
        Also can set return_affected_points to True,
        which means that along with the Path object it will return 2 Points
        showing all the points in the path.
        The first shows Point objects that still have unexplored neighbors,
        while the second shows Point objects that have no unexplored
        neighbors.
        Not 100% reliable, as if a point has an unexplored neighbor that is
        explored later in the path, it will not be moved to the second list.
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
                    #allows distance of 2 so that corners don't connect
                    #both the corner piece and diagonal connection.
                    (
                        explored_paths == None or
                        not explored_paths.has_connection(
                            path[-1], point_exploring, 2
                        )
                    )
                ):
                    if path[-1].is_adjacent(point_exploring):
                        adjacents.append(point_exploring)
                        if not return_affected_points:
                            break
                    else:
                        neighbors.append(point_exploring)

            #prioritize adjacent cells to avoid path skipping corners
            #and leaving single points behind
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
            return (
                Path(path),
                Points(expandable_points),
                Points(unexpandable_points)
            )
        else:
            return Path(path)

    def compress(self, max_dist=1):
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

    def visualize(self, background_img, line_color, start_color=None):
        """
        Shows the background image with an animated .gif showing the path.
        Also saves to a file that isn't deleted,
        because showing an animated .gif doesn't seem to show the animation.
        """
        background_img = background_img.copy()
        imgs = self.apply_to_img(background_img, line_color, start_color)
        imgs[0].save(
            TEMP_GIF_FILE, save_all=True, append_images=imgs[1:],
            duration=1000/GIF_FPS, loop=0
        )
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

    def has_connection(self, point_a, point_b, max_dist=1):
        for i in range(len(self._point_list)):
            if (
                self._point_list[i] == point_a or
                self._point_list[i] == point_b
            ):
                for j in range(1, max_dist + 1):
                    if (
                        (
                            self._point_list[i] == point_a and
                            self._point_list[
                                (i+j)%len(self._point_list)
                            ] == point_b
                        ) or
                        (
                            self._point_list[i] == point_b and
                            self._point_list[
                                (i+j)%len(self._point_list)
                            ] == point_a
                        )
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
        return (
            abs(self.x - other.x) <= 1 and
            abs(self.y - other.y) <= 1 and
            self != other
        )

    def is_adjacent(self, other):
        return (
            (abs(self.x - other.x) == 1 and self.y == other.y) or
            (self.x == other.x and abs(self.y - other.y) == 1)
        )

    def to_tuple(self):
        return (self.x, self.y)

    def visualize(self, background_img, color):
        """
        Shows the background image,
        but with the point added to it using the color parameter.
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
            ), fill=color)

    def __eq__(self, other):
        return (
            isinstance(other, Point) and
            self.x == other.x and
            self.y == other.y
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "{}, {}".format(self.x, self.y)

#helper functions
def is_pixel_unneeded(pil_img, pixel):
    """
    Returns if the pixel can be removed without breaking any lines.
    Assumes pil_img is mode "1".
    """
    neighs = (
        (pixel[0], pixel[1]+1),
        (pixel[0]+1, pixel[1]+1),
        (pixel[0]+1, pixel[1]),
        (pixel[0]+1, pixel[1]-1),
        (pixel[0], pixel[1]-1),
        (pixel[0]-1, pixel[1]-1),
        (pixel[0]-1, pixel[1]),
        (pixel[0]-1, pixel[1]+1)
    )
    neigh_values = []
    for neigh in neighs:
        if (
            neigh[0] < 0 or
            neigh[0] >= pil_img.width or
            neigh[1] < 0 or
            neigh[1] >= pil_img.height
        ):
            neigh_values.append(255)
        else:
            neigh_values.append(pil_img.getpixel(neigh))

    if neigh_values.count(0) <= 1:
        #the pixel is either a single point, or the edge of a line
        return False

    if neigh_values.count(255) <= 1:
        #inner pixel, should be removed later
        #I tested with 0 to so that it only removes if no background,
        #but that can sometimes give bad results
        return False

    segments = 0
    for i in range(len(neigh_values)):
        if neigh_values[i-1] == 0 and neigh_values[i] == 255:
            segments += 1
    if segments >= 2:
        #the pixel connects multiple sides
        return False

    return True
