import yaml
import platform
try:
    import winreg
except ModuleNotFoundError:
    pass
import os
from yaml import Loader, Dumper

class ygPreferences(dict):
    def __init__(self, *args, **kwargs):
        super(ygPreferences, self).__init__(*args, **kwargs)
        self["top_window"] = None
        self["show_off_curve_points"] = True
        self["show_point_numbers"] = False
        self["current_glyph"] = {}
        self["current_axis"] = "y"
        self["save_points_as"] = "coord" # "coord" or "name" or "index"
        self["current_font"] = None
        self["show_metrics"] = True
        self["recents"] = []
        self["zoom_factor"] = 1.0
        self["points_as_coords"] = False
        self["auto_preview"] = True
        self["top_window_pos_x"]
        self["top_window_pos_y"]
        self["top_window_height"]
        self["top_window_width"]

    def current_axis(self):
        return self["current_axis"]

    def set_current_axis(self, a):
        self["current_axis"] = a

    def points_as_coords(self):
        return self["points_as_coords"]

    def set_points_as_coords(self, b):
        self["points_as_coords"] = b

    def auto_preview(self):
        return self["auto_preview"]

    def set_auto_preview(self, p):
        self["auto_preview"] = p

    def zoom_factor(self):
        return self["zoom_factor"]

    def set_zoom_factor(self, z):
        self["zoom_factor"] = z

    def recents(self):
        return self["recents"]

    def add_recent(self, f):
        if os.path.splitext(f)[1] in [".yaml", ".ufo"]:
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
        if platform.system() == "Windows":
          write_win_registry(self)
        config_dir = os.path.expanduser('~/.ygt/')
        if not os.path.isdir(config_dir):
            try:
                os.mkdir(config_dir)
            except Exception as e:
                print("Exception while saving preferences:")
                print(e)
                return
        config_file = os.path.join(config_dir, "ygt_config.yaml")
        save_dict = {}
        k = self.keys()
        for kk in k:
            if not kk in ["top_window", "current_font"]:
                save_dict[kk] = self[kk]
        # print(save_dict)
        with open(config_file, "w") as f:
            f.write(yaml.dump(save_dict, sort_keys=False, Dumper=Dumper))

def open_config(top_window):
    if platform.system() == "Windows":
        return read_win_registry(top_window)
    try:
        config_path = os.path.expanduser('~/.ygt/ygt_config.yaml')
        with open(config_path, 'r') as pstream:
            pref_dict = yaml.safe_load(pstream)
        p = ygPreferences()
        k = pref_dict.keys()
        for kk in k:
            p[kk] = pref_dict[kk]
        p["top_window"] = top_window
        top_window.set_axis_buttons()
        return p
    except Exception as e:
        print("Exception in open_config:")
        print(e)
        p = ygPreferences()
        p["top_window"] = top_window
        return p

def read_win_registry(top_window):
    path = winreg.HKEY_CURRENT_USER
    p = ygPreferences()
    try:
        key = winreg.OpenKeyEx(path, r"SOFTWARE\\ygt\\")
    except Exception as e:
        print("Can't open registry")
        p["top_window"] = top_window
        return p
    try:
        p["show_off_curve_points"] = bool(winreg.QueryValueEx(key, "show_off_curve_points")[0])
        p["show_point_numbers"] = bool(winreg.QueryValueEx(key, "show_point_numbers")[0])
        p["current_axis"] = winreg.QueryValueEx(key, "current_axis")[0]
        p["save_points_as"] = winreg.QueryValueEx(key, "save_points_as")[0]
        p["current_font"] = winreg.QueryValueEx(key, "current_font")[0]
        p["show_metrics"] = bool(winreg.QueryValueEx(key, "show_metrics")[0])
        p["zoom_factor"] = float(winreg.QueryValueEx(key, "zoom_factor")[0])
        p["points_as_coords"] = bool(winreg.QueryValueEx(key, "points_as_coords")[0])
        p["auto_preview"] = bool(winreg.QueryValueEx(key, "auto_preview")[0])
        p["recents"] = winreg.QueryValueEx(key, "recents")[0]
    except Exception as e:
        print(e)
    # Also need "current_glyph" (dict) and "recents" (list)
    try:
        if key:
            winreg.CloseKey(key)
        p["top_window"] = top_window
    except Exception as e:
        pass
    return p

def write_win_registry(prefs):
    path = winreg.HKEY_CURRENT_USER
    try:
        key = winreg.OpenKeyEx(path, r"SOFTWARE\\")
        yg_key = winreg.CreateKey(key,"ygt")
        winreg.SetValueEx(yg_key, "show_off_curve_points", 0, winreg.REG_DWORD,
                          int(prefs["show_off_curve_points"]))
        winreg.SetValueEx(yg_key, "show_point_numbers", 0, winreg.REG_DWORD,
                          int(prefs["show_point_numbers"]))
        winreg.SetValueEx(yg_key, "current_axis", 0, winreg.REG_SZ,
                          prefs["current_axis"])
        winreg.SetValueEx(yg_key, "save_points_as", 0, winreg.REG_SZ,
                          prefs["save_points_as"])
        winreg.SetValueEx(yg_key, "current_font", 0, winreg.REG_SZ,
                          prefs["current_font"])
        winreg.SetValueEx(yg_key, "show_metrics", 0, winreg.REG_DWORD,
                          int(prefs["show_metrics"]))
        winreg.SetValueEx(yg_key, "zoom_factor", 0, winreg.REG_SZ,
                          str(prefs["zoom_factor"]))
        winreg.SetValueEx(yg_key, "points_as_coords", 0, winreg.REG_DWORD,
                          int(prefs["points_as_coords"]))
        winreg.SetValueEx(yg_key, "auto_preview", 0, winreg.REG_DWORD,
                          int(prefs["auto_preview"]))
        winreg.SetValueEx(yg_key, "recents", 0, winreg.REG_MULTI_SZ,
                          prefs["recents"])
        if yg_key:
            winreg.CloseKey(yg_key)
        return True
    except Exception as e:
        print(e)
    return False
