from fontTools.varLib import instancer

class instanceChecker:
    """ This class will build an instance for a variable font and check
        the y positions of points from which the cvt table was made. If
        the y positions are different, the y position of the point is
        recorded and reported.
    """
    def __init__(self, ft_font, cvt, masters):
        self.ft_font = ft_font
        self.cvt = cvt
        self.masters = masters
        self.axes = self.masters.yg_font.axes
        self.current_instance = None

    def refresh(self):
        self.delete_all_vars()
        d = self.get_all_variant_cvs()
        self.add_variants_to_cvt(d)

    def delete_all_vars(self):
        k = self.cvt.keys()
        for kk in k:
            cv = self.cvt.get_cv(kk)
            try:
                del cv["var"]
            except Exception:
                pass

    def make_instance(self, vals):
        self.current_instance = instancer.instantiateVariableFont(self.ft_font, vals)

    def get_all_variant_cvs(self):
        # We end up with a dict:
        # {master_id: {cv_name: val, ...}, ...}
        result = {}
        k = self.masters.keys()
        for kk in k:
            c = self.get_cvs_for_master(kk)
            if len(c) > 0:
                result[kk] = c
        return result

    def add_variants_to_cvt(self, d):
        # d is a dict in the format produced by get_all_variant_cvs.
        ck = self.cvt.keys()
        dk = d.keys()
        for ckk in ck:                        # iterate through CVs.
            for dkk in dk:                    # iterate through masters
                if ckk in d[dkk]:             # if the master has an entry for the current CV,
                    cv = self.cvt.get_cv(ckk) # create a "var" entry in the CV.
                    if not "var" in cv:
                        cv["var"] = {}
                    cv["var"][dkk] = d[dkk][ckk]

    def get_cvs_for_master(self, master_id):
        # Get the glyph name and point index from the "origin" field.
        # Get the list of y values (function below) and grab the
        #     value at the appropriate index.
        # Compare the new position with that of the default cv.
        # If different, store. If the same, discard.
        result = {}
        coords = self.masters.get_master_coords(master_id)
        self.make_instance(coords)
        k = self.cvt.keys()
        for kk in k:
            cv = self.cvt.get_cv(kk)
            if type(cv) is dict and cv["type"] == "pos" and "origin" in cv:
                glyph_name = cv["origin"]["glyph"]
                ptnum =      cv["origin"]["ptnum"]
                y_pos = self.y_list(glyph_name)[ptnum[0]]
                if cv["val"] != y_pos:
                    result[kk] = y_pos
                pass
        return result

    def y_list(self, glyph_name):
        gl = self.current_instance['glyf'][glyph_name].getCoordinates(self.ft_font['glyf'][glyph_name])
        y_points = []
        for p in gl[0]:
            y_points.append(p[1])
        return y_points
            