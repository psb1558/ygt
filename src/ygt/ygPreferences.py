import yaml
from yaml import Loader, Dumper
import sys

class ygPreferences(dict):
    def __init__(self, *args, **kwargs):
        super(ygPreferences, self).__init__(*args, **kwargs)
        self["top_window"] = None
        self["show_off_curve_points"] = True
        self["show_point_numbers"] = False
        self["current_glyph"] = {}
        self["current_vector"] = "y"
        self["save_points_as"] = "indices"
        self["current_font"] = None
        self["show_metrics"] = True
        self["recents"] = []

    def recents(self):
        return self["recents"]

    def add_recent(self, f):
        fl = self["recents"]
        if not f in fl:
            fl = [f] + fl
        if len(fl) > 5:
            fl.pop()
        self["recents"] = fl

    def top_window(self):
        return self["top_window"]

    def show_off_curve_points(self):
        return self["show_off_curve_points"]

    def set_show_off_curve_points(self, b):
        self["show_off_curve_points"] = b

    def show_point_numbers(self):
        return self["show_point_numbers"]

    def set_show_point_numbers(self, b):
        self["show_point_numbers"] = b

    def current_glyph(self, fontfile):
        try:
            return self["current_glyph"][fontfile]
        except Exception:
            return "A"

    def set_current_glyph(self, k, gname):
        self["current_glyph"][k] = gname

    def current_font(self):
        return self["current_font"]

    def set_current_font(self, f):
        self["current_font"] = f

    def points_as(self):
        return self["save_points_as"]

    def set_points_as(self, val):
        if val in ["indices", "coordinates"]:
            self["points_as"] = val

    def save_config(self):
        save_dict = {}
        k = self.keys()
        for kk in k:
            if not kk in ["top_window", "current_font"]:
                save_dict[kk] = self[kk]
        with open("yg_config.yaml", "w") as f:
            f.write(yaml.dump(save_dict, sort_keys=False, Dumper=Dumper))

def open_config(top_window):
    try:
        with open("yg_config.yaml", 'r') as pstream:
            pref_dict = yaml.safe_load(pstream)
        p = ygPreferences()
        k = pref_dict.keys()
        for kk in k:
            p[kk] = pref_dict[kk]
        p["top_window"] = top_window
        return p
    except Exception as e:
        print("Exception in open_config:")
        print(e)
        p = ygPreferences()
        p["top_window"] = top_window
        return p
