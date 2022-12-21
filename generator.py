PRE_GCODE = """G21
M3 S{s_speed}
G90
G0 Z{hover_height}
G0 X0.000 Y0.000"""
POST_CODE = """
G0 Z{hover_height}
G0 X0.000 Y0.000
M5
M30"""

SPINDLE_SPEED = 10000
HOVER_HEIGHT = 1
VERTICAL_SPEED = 250
HORIZONTAL_SPEED = 750

class Generator:
    def __init__(self):
        self._pre_code = PRE_CODE.format(s_speed = SPINDLE_SPEED, hover_height = HOVER_HEIGHT)
        self._post_code = POST_CODE.format(hover_height = HOVER_HEIGHT)
        self._move_code = ""
