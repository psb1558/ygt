from typing import Optional, List, TYPE_CHECKING
from .ygModel import ygPoint, ygGlyph


class stemFinder:
    def __init__(self, p1: ygPoint, p2: ygPoint, yg_glyph: ygGlyph) -> None:
        self.yg_glyph = yg_glyph
        self.counter_clockwise = bool(self.yg_glyph.yg_font.defaults.get_default("counterclockwise"))
        self.contours = []
        contour = []
        points = yg_glyph.points
        for p in points:
            contour.append(p)
            if p.end_of_contour:
                self.contours.append(contour)
                contour = []
        self.high_point = p1
        self.low_point = p2
        if self.yg_glyph.axis == "y":
            # self.high_point must have a higher y value than self.low_point.
            if self.high_point.font_y < self.low_point.font_y:
                self.high_point, self.low_point = self.low_point, self.high_point
        else:
            # self.high_point must have a lower x value than self.low_point.
            if self.high_point.font_x > self.low_point.font_x:
                self.high_point, self.low_point = self.low_point, self.high_point

    def find_point_by_index(self, i: int, c: List[ygPoint]) -> Optional[ygPoint]:
        """ Find the point with index i in contour c. Returns None if not found.
        """
        for p in c:
            if p.index == i:
                return p
        return None

    def next_point(self, p: ygPoint, c: List[ygPoint]) -> ygPoint:
        """ p a ygPoint object; c a contour. Returns the next point
            on the contour, wrapping if necessary.
        """
        last_point = c[-1]
        first_point = c[0]
        if p.index < last_point.index:
            return self.find_point_by_index(p.index + 1, c)
        else:
            return first_point
        
    def prev_point(self, p: ygPoint, c: List[ygPoint]) -> ygPoint:
        last_point = c[-1]
        first_point = c[0]
        if p.index > first_point.index:
            return self.find_point_by_index(p.index - 1, c)
        else:
            return last_point

    def which_contour(self, pt: ygPoint) -> Optional[List[ygPoint]]:
        """ Return the contour (list of ygPoint objects) containing pt.
        """
        for c in self.contours:
            if pt in c:
                return c
        return None
    
    def x_direction(self, pt: ygPoint) -> str:
        """ Find the x direction of a line or curve at the location of
            point pt. Returns "left," "right," or "same" if this pt
            has the same x location as the next pt.

            To do: if the result is going to be "same," try with a
            prev_point function (to be supplied).
        """
        contour = self.which_contour(pt)
        next_point = self.next_point(pt, contour)
        this_x = pt.font_x
        next_x = next_point.font_x
        if next_x > this_x:
            if self.counter_clockwise:
                return("left")
            else:
                return "right"
        elif this_x > next_x:
            if self.counter_clockwise:
                return "right"
            else:
                return "left"
        # If the points are aligned on this axis we're probably at the end of a stem.
        prev_point = self.prev_point(pt, contour)
        prev_x = prev_point.font_x
        if prev_x < this_x:
            if self.counter_clockwise:
                return("left")
            else:
                return "right"
        elif this_x < prev_x:
            if self.counter_clockwise:
                return "right"
            else:
                return "left"
        return "same"

        
    def y_direction(self, pt: ygPoint) -> str:
        """ Find the y direction of a line or curve at the location of
            point pt. Returns "up," "down," or "same" if this pt
            has the same y location as the next pt.
        """
        contour = self.which_contour(pt)
        next_point = self.next_point(pt, contour)
        next_y = next_point.font_y
        this_y = pt.font_y
        if next_y > this_y:
            if self.counter_clockwise:
                return "down"
            else:
                return "up"
        elif this_y > next_y:
            if self.counter_clockwise:
                return "up"
            else:
                return "down"
        prev_point = self.prev_point(pt, contour)
        prev_y = prev_point.font_y
        if prev_y > this_y:
            if self.counter_clockwise:
                return "up"
            else:
                return "down"
        elif this_y > prev_y:
            if self.counter_clockwise:
                return "down"
            else:
                return "up"
        return "same"
        
    def get_color(self) -> str:
        """ Recommends a distance type for the stem formed by self.high_point
            and self.low_point, based on this class's analysis of the stem.
        """
        result = "graydist"
        if self.yg_glyph.axis == "x":
            high_y_dir = self.y_direction(self.high_point)
            low_y_dir = self.y_direction(self.low_point)
            if high_y_dir == "up" and low_y_dir == "down":
                result = "blackdist"
            elif high_y_dir == "down" and low_y_dir == "up":
                result = "whitedist"
        else:
            high_x_dir = self.x_direction(self.high_point)
            low_x_dir  = self.x_direction(self.low_point)
            if high_x_dir == "right" and low_x_dir == "left":
                result = "blackdist"
            elif high_x_dir == "left" and low_x_dir == "right":
                result = "whitedist"
        return result

