class keyPoint:
    def __init__(self, pt, desc):
        self.point = pt
        self.label = desc


class autohinter:
    def __init__(self, yg_glyph):
        points = yg_glyph.points()
        self.key_points = []
        self.contours = []
        contour = []
        for p in points:
            contour.append(p)
            if p.end_of_contour:
                self.contours.append(contour)
                contour = []

        for c in self.contours:
            for p in c:
                if p.on_curve:
                    prev_p = self.prev_point(p, c)
                    next_p = self.next_point(p, c)
                    if (
                        (prev_p.font_y == next_p.font_y == p.font_y)
                        and not prev_p.on_curve
                        and not next_p.on_curve
                    ):
                        label = "curve"
                        rightward = prev_p.font_x < prev_p.font_x
                        if rightward:
                            label += "-right"
                        else:
                            label += "-left"
                        self.key_points.append(keyPoint(p, ""))

    def prev_point(self, p, c):
        first_point = c[0].index
        if p.index > first_point:
            return self.find_point_by_index(p.index - 1, c)
        else:
            return c[-1]

    def next_point(self, p, c):
        last_point = c[-1].index
        if p.index < last_point:
            return self.find_point_by_index(p.index + 1, c)
        else:
            return c[0]

    def find_point_by_index(self, i, c):
        for p in c:
            if p.index == i:
                return p
