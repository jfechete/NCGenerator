import copy

class Paths:
    def __init__(self, path_list):
        self._path_list = path_list

class Points:
    def __init__(self, point_list):
        self._point_list = point_list

    @staticmethod
    def from_binary_image(pil_image):
        """
        Returns a Points object showing the outline of the white objects in this picture.
        The inner border is used, every point will be on a white pixel.
        """
        if pil_image.mode != "1":
            pil_image = pil_image.convert("1")

        point_list = []
        for x in range(pil_image.width):
            for y in range(pil_image.height):
                color = pil_image.getpixel((x,y))
                if color > 0:
                    neighs = (
                        (x+1, y),
                        (x-1, y),
                        (x, y+1),
                        (x, y-1)
                    )
                    for neigh in neighs:
                        neigh_color = pil_image.getpixel(neigh)
                        if neigh_color == 0:
                            point_list.append(Point(x, y))
                            break

        return Points(point_list)

    def visualize_points(self, background_image, color):
        """"
        Shows the background image but with every point added to it using the color parameter.
        """
        background_image = background_image.copy()
        for point in self:
            background_image.putpixel((point.x, point.y), color)
        background_image.show()

    def __iter__(self):
        return iter(self._point_list)

class Path:
    def __init__(self, point_list):
        self._point_list = point_list

    def __iter__(self):
        return iter(self._point_list)

class Point:
    def __init__(self, x, y):
        #Coordinates are currently meant to be pixels and integers
        #May be changed in the future as non-image inputs are added
        self.x = x
        self.y = y

    def __str__(self):
        return "{}, {}".format(self.x, self.y)
