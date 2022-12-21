class Paths:
    def __init__(self, path_list):
        self._path_list = path_list

class Points:
    def __init__(self, point_list):
        self._point_list = point_list

class Path:
    def __init__(self, point_list):
        self._point_list = point_list

class Point:
    def __init__(self, x, y):
        #Coordinates are currently meant to be pixels and integers
        #May be changed in the future as non-image inputs are added
        self.x = x
        self.y = y

