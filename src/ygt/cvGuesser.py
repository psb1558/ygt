from typing import Optional
from fontTools.varLib import instancer  # type: ignore
from fontTools.ttLib.ttFont import TTFont # type: ignore


class instanceChecker:
    """This class will build an instance for a variable font and check
    the y positions of points from which the cvt table was made. If
    the y positions are different, the y position of the point is
    recorded and reported.
    """

    def __init__(self, ft_font, cvt, masters) -> None:
        self.ft_font = ft_font
        self.cvt = cvt
        self.masters = masters
        self.axes = self.masters.yg_font.axes
        self.current_instance: Optional[TTFont] = None

    def refresh(self) -> None:
        self.delete_all_vars()
        d = self.get_all_variant_cvs()
        self.add_variants_to_cvt(d)

    def delete_all_vars(self) -> None:
        k = self.cvt.keys
        for kk in k:
            cv = self.cvt.get_cv(kk)
            try:
                # if there's no "origin" in the cv, we can't replace the vars.
                if "origin" in cv:
                    del cv["var"]
            except Exception:
                pass

    def make_instance(self, vals: dict) -> None:
        self.current_instance = instancer.instantiateVariableFont(self.ft_font, vals)

    def get_all_variant_cvs(self) -> dict:
        # We end up with a dict:
        # {master_id: {cv_name: val, ...}, ...}
        result = {}
        k = self.masters.keys
        for kk in k:
            c = self.get_cvs_for_master(kk)
            if len(c) > 0:
                result[kk] = c
        return result

    def add_variants_to_cvt(self, d: dict) -> None:
        # d is a dict in the format produced by get_all_variant_cvs.
        ck = self.cvt.keys
        dk = d.keys()
        for ckk in ck:  # iterate through CVs.
            for dkk in dk:  # iterate through masters
                if ckk in d[dkk]:  # if the master has an entry for the current CV,
                    cv = self.cvt.get_cv(ckk)  # create a "var" entry in the CV.
                    if not "var" in cv:
                        cv["var"] = {}
                    cv["var"][dkk] = d[dkk][ckk]

    def get_cvs_for_master(self, master_id: str) -> dict:
        # Get the glyph name and point index (or indices) from the
        # "origin" field. Get the list of y values (function below) and
        # use those to figure out the value of the cv for this glyph.
        # Compare the new position with that of the default cv.
        # If different, store. If the same, discard.
        result = {}
        coords = self.masters.get_master_coords(master_id)
        self.make_instance(coords)
        k = self.cvt.keys
        for kk in k:
            cv = self.cvt.get_cv(kk)
            if type(cv) is dict and "origin" in cv:
                if cv["type"] == "pos":
                    glyph_name = cv["origin"]["glyph"]
                    ptnum = cv["origin"]["ptnum"]
                    y_pos = self.y_list(glyph_name)[ptnum[0]]
                    if cv["val"] != y_pos:
                        result[kk] = y_pos
                elif cv["type"] == "dist":
                    glyph_name = cv["origin"]["glyph"]
                    ptnum = cv["origin"]["ptnum"]
                    yl = self.y_list(glyph_name)
                    y_diff = abs(yl[ptnum[0]] - yl[ptnum[1]])
                    if cv["val"] != y_diff:
                        result[kk] = y_diff
        return result

    def y_list(self, glyph_name: str) -> list:
        gl = self.current_instance["glyf"][glyph_name].getCoordinates(
            self.ft_font["glyf"][glyph_name]
        )
        y_points = []
        for p in gl[0]:
            y_points.append(p[1])
        return y_points
