PRE_CODE = """G21
M3 S{s_speed}
G90
G0 Z{hover_height}
G0 X0.000 Y0.000"""
POST_CODE = """G0 Z{hover_height}
G0 X0.000 Y0.000
M5
M30"""

SPINDLE_SPEED = 10000
HOVER_HEIGHT = 1
VERTICAL_SPEED = 250
HORIZONTAL_SPEED = 750
DEPTH_STEP = 0.5
FLOAT_PRECISION = 3

class Generator:
    def __init__(self, mm_ratio, min_move_dist=0):
        """
        Creates the generator for creating nc files.
        The mm_ratio parameter is how many millimeters per pixel.
        """
        self._pre_code = PRE_CODE.format(
            s_speed=SPINDLE_SPEED, hover_height=HOVER_HEIGHT
        )
        self._post_code = POST_CODE.format(hover_height=HOVER_HEIGHT)
        self._move_code = ""
        self._mm_ratio = mm_ratio
        self._min_move_dist = 0

    def add_multipass(self, paths, depth, depth_step=DEPTH_STEP):
        """
        Creates multiple passes that follows the given Paths object.
        Each path increases in depth by the depth_step parameter
        until it reaches the desired depth.
        """
        current_depth = 0
        while current_depth < depth:
             current_depth += depth_step
             current_depth = min(current_depth, depth)
             self.add_pass(paths, current_depth)

    def add_pass(self, paths, depth):
        """
        Creates a single pass that follows the given
        Paths object at the supplied depth.
        """
        for path in paths:
            path_code = "G0 Z{hover_height}\n".format(
                hover_height=HOVER_HEIGHT
            )
            start = path.get_first_point()
            last_pos = (self._get_mm_pos(start.x), self._get_mm_pos(start.y))
            path_code += "G0 X{x} Y{y}\n".format(x=last_pos[0],y=last_pos[1])
            path_code += "G1 Z-{depth} F{speed}\n".format(
                depth=depth, speed=VERTICAL_SPEED
            )
            path_code += "G1 F{speed}\n".format(speed=HORIZONTAL_SPEED)
            for point in path:
                cur_pos = (
                    self._get_mm_pos(point.x),
                    self._get_mm_pos(point.y)
                )
                if self._is_move_far(last_pos, cur_pos):
                    path_code += "G1 X{x} Y{y}\n".format(
                        x=cur_pos[0],y=cur_pos[1]
                    )
                    last_pos = cur_pos
            if last_pos != cur_pos:
                path_code += "G1 X{x} Y{y}\n".format(
                    x=cur_pos[0],y=cur_pos[1]
                )
            path_code += "G0 Z{hover_height}\n".format(
                hover_height=HOVER_HEIGHT
            )

            self._move_code += path_code

    def export(self, out_file):
        """
        Saves the current generated code to a file.
        """
        if not self._pre_code.endswith("\n"):
            self._pre_code += "\n"
        if not self._move_code.endswith("\n"):
            self._move_code += "\n"
        with open(out_file, "w") as nc_file:
            nc_file.write(self._pre_code)
            nc_file.write(self._move_code)
            nc_file.write(self._post_code)

    def _is_move_far(self, pos_a, pos_b):
        return (
            (pos_a[0]-pos_b[0])**2 + (pos_a[1]-pos_b[1])**2 >=
            self._min_move_dist**2
        )

    def _get_mm_pos(self, pixel_pos):
        return round(pixel_pos* self._mm_ratio, FLOAT_PRECISION)
