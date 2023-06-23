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
FLOAT_PRECISION = 3

class Generator:
    def __init__(self, mm_ratio, bit_size, min_move_dist=0):
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
        self._min_move_dist = min_move_dist
        self._bit_size = bit_size

    def carve_heigtmap(
        self, heightmap, min_depth, max_depth,
        both_directions = False, single_pass = False
    ):
        """
        Carve out the given Heightmap object.
        Min and max depth show how to scale the heights.
        Set both_directions to true to have it go over each section twice,
        once in each direction.
        Set single_pass to true to carve it only at the given depth,
        without doing smaller increments beforehand.
        """
        if max_depth > self._bit_size/2 and not single_pass:
            self.carve_heigtmap(
                heightmap, max(0, min_depth - self._bit_size/2),
                max_depth - self._bit_size/2,
                both_directions = both_directions
            )

        rows = heightmap.get_rows()
        row_points, cross_direction_points = self._split_points([
            self._get_mm_pos(point) for point in rows
        ])
        row_counts = [len(points) for points in row_points]
        carve_direction_points = []
        carve_direction_points.append(
            self._convert_heightmap_line(heightmap.get_rows_max(
                rows[0:row_counts[0]]
            ), min_depth, max_depth)
        )
        for i in range(1,len(row_counts)):
            carve_direction_points.append(
                self._convert_heightmap_line(heightmap.get_rows_max(
                    rows[sum(row_counts[0:i])-1:sum(row_counts[0:i+1])]
                ), min_depth, max_depth)
            )

        self._carve_heightmap_pass(
            "X", carve_direction_points,
            "Y", cross_direction_points
        )

        if both_directions:
            columns = heightmap.get_columns()
            column_points, cross_direction_points = self._split_points([
                self._get_mm_pos(point) for point in columns
            ])
            column_counts = [len(points) for points in column_points]
            carve_direction_points = []
            carve_direction_points.append(
                self._convert_heightmap_line(heightmap.get_columns_max(
                    columns[0:column_counts[0]]
                ), min_depth, max_depth)
            )
            for i in range(1,len(column_counts)):
                carve_direction_points.append(
                    self._convert_heightmap_line(heightmap.get_columns_max(
                        columns[
                            sum(column_counts[0:i])-1:
                            sum(column_counts[0:i+1])
                        ]
                    ), min_depth, max_depth)
                )

            self._carve_heightmap_pass(
                "Y", carve_direction_points,
                "X", cross_direction_points
            )

    def carve_paths(self, paths, depth, single_pass = False):
        """
        Carves along every path in the given Paths object.
        Set single_pass to true to carve it only at the given depth,
        without doing smaller increments beforehand.
        """
        if depth > self._bit_size/2 and not single_pass:
            self.carve_paths(paths, depth - self._bit_size/2)
        for path in paths:
            self.carve_path(path, depth, single_pass = True)

    def carve_path(self, path, depth, single_pass = False):
        """
        Carves along the given Path object.
        Set single_pass to true to carve it only at the given depth,
        without doing smaller increments beforehand.
        """
        if depth > self._bit_size/2 and not single_pass:
            self.carve_path(path, depth - self._bit_size/2)

        path_code = "G0 Z{hover_height}\n".format(
            hover_height=HOVER_HEIGHT
        )
        start = path.get_first_point()
        last_pos = self._get_mm_pos(start.to_tuple())
        path_code += "G0 X{x} Y{y}\n".format(x=last_pos[0],y=last_pos[1])
        path_code += "G1 Z-{depth} F{speed}\n".format(
            depth=depth, speed=VERTICAL_SPEED
        )
        path_code += "G1 F{speed}\n".format(speed=HORIZONTAL_SPEED)
        for point in path:
            cur_pos = self._get_mm_pos(point.to_tuple())
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

    def _carve_heightmap_pass(
        self, carve_direction, carve_direction_points,
        cross_direction, cross_direction_points
    ):
        path_code = "G0 Z{hover_height}\n".format(
            hover_height=HOVER_HEIGHT
        )
        reverse = False
        for cross_pos, line in zip(
            cross_direction_points, carve_direction_points
        ):
            if reverse:
                line = list(reversed(line))
            #Get the bit in position for the line
            path_code += "G0 {cross_dir}{cross_pos} ".format(
                cross_dir=cross_direction, cross_pos=cross_pos
            )
            path_code += "{carve_dir}{carve_start}\n".format(
                carve_dir=carve_direction, carve_start=line[0][0]
            )
            path_code += "G1 Z-{depth} F{speed}\n".format(
                depth=line[0][1], speed=VERTICAL_SPEED
            )
            path_code += "G1 F{speed}\n".format(speed=HORIZONTAL_SPEED)
            #Carve out the line
            last_pos = line[0][0]
            for pos, height in line:
                if self._is_move_far((0,last_pos),(0,pos)):
                    next_pos = "G1 {carve_dir}{carve_pos} Z-{depth}\n".format(
                        carve_dir=carve_direction, carve_pos=pos,
                        depth=height
                    )
                    path_code += next_pos
            #Hover to prepare for next line
            path_code += "G0 Z{hover_height}\n".format(
                hover_height=HOVER_HEIGHT
            )
            reverse = not reverse

        self._move_code += path_code

    def _split_points(self, points):
        """
        Gets a list of points along a single axis,
        and splits them so that each section is completely covered by the bit.
        Returns two lists.
        One is a list of lists showing all the points in each section.
        The second is a list showing where to put the bit in each section,
        so that it covers all of the corresponding points in the other list.
        """
        cover_points = []
        bit_pos = []
        cr_cover_points = []
        cr_bit_pos = None
        cr_start = points[0]
        for point in points:
            if point - cr_start > self._bit_size/2 and cr_bit_pos == None:
                cr_bit_pos = cr_cover_points[-1]
            if point - cr_start > self._bit_size:
                cr_start = cr_cover_points[-1]
                cover_points.append(cr_cover_points.copy())
                bit_pos.append(cr_bit_pos)
                cr_cover_points.clear()
                cr_bit_pos = None
            cr_cover_points.append(point)
        if cr_bit_pos == None:
            cr_bit_pos = cr_cover_points[-1]
        cover_points.append(cr_cover_points.copy())
        bit_pos.append(cr_bit_pos)
        return cover_points, bit_pos

    def _convert_heightmap_line(self, line, min_depth, max_depth):
        line = [
            (
                self._get_mm_pos(pos),
                (max_depth - min_depth)*height + min_depth
            ) for pos, height in line
        ]
        return line

    def _is_move_far(self, pos_a, pos_b):
        return (
            (pos_a[0]-pos_b[0])**2 + (pos_a[1]-pos_b[1])**2 >=
            self._min_move_dist**2
        )

    def _get_mm_pos(self, pixel_pos):
        if isinstance(pixel_pos, tuple):
            return tuple(
                self._get_mm_pos(d) for d in pixel_pos
            )
        elif isinstance(pixel_pos, list):
            return list(
                self._get_mm_pos(d) for d in pixel_pos
            )
        return round(pixel_pos* self._mm_ratio, FLOAT_PRECISION)
