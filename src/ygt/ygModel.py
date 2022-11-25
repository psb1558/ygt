from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from fontTools import ttLib
import yaml
import os
from yaml import Dumper
import uuid
import sys
import copy
from functools import cmp_to_key
from .ygPreferences import ygPreferences

hint_type_nums  = {"anchor": 0, "align": 1, "shift": 1, "interpolate": 2,
                   "stem": 3, "whitespace": 3, "blackspace": 3, "grayspace": 3,
                   "move": 3, "macro": 4, "function": 4}

# Classes in this file:

# SourceFile: The yaml source read from and written to by this program.
# FontFiles: Input and output font files.
# ygSourceable: Superclass for various chunks of ygt source code.
# ygFont: Keeps the fontTools representation of a font and provides an
#                     interface for the YAML code.
# ygprep(ygSourceable): Holds the cvt program/pre-program.
# ygDefaults(ygSourceable): Keeps defaults for this font's hints.
# ygcvt(ygSourceable): Keeps the control values for this font.
# ygcvar(ygSourceable): Keeps the cvar table.
# ygFunctions(ygSourceable): Holds the functions (fpgm table) for this font.
# ygMacros(ygSourceable): Holds the macros for this font.
# ygCaller: superclass for ygFunction and ygMacro.
# ygFunction(ygCaller): A function call.
# ygMacro(ygCaller): A macro call.
# ygPoint: One point.
# ygParams: For functions and macros, holds their parameters.
# ygSet: A set of points, for SLOOP instructions like shift and interpolate.
# ygGlyph(QObject): Keeps data for the current glyph.
# ygGlyphs: Collection of this font's glyphs.
# Comparable: superclass for ygHintSource: for ordering hints.
# ygHintSource(Comparable): Wrapper for hint source: use when sorting.
# ygHint(QObject): One hint (including a function or macro)
# ygHintSorter: Sorts hints into their proper order.
# ygPointSorter: Utility for sorting points on the x or y axis.

class SourceFile:
    """ The yaml source read from and written to by this program.
    """
    def __init__(self, yaml_source, yaml_filename=None):
        """ The constructor reads the yaml source into the internal structure
            y_doc. If yaml_source is a dict, it is the skeleton yaml source
            generated for a new program. Otherwise, yaml_source will be a
            filename.
        """
        if type(yaml_source) is dict:
            self.y_doc = copy.deepcopy(yaml_source)
            if yaml_filename:
                self.filename = yaml_filename
            else:
                self.filename = "NewFile.yaml"
        else:
            self.filename = yaml_source
            y_stream = open(yaml_source, 'r')
            self.y_doc = yaml.safe_load(y_stream)
            y_stream.close()

    def get_source(self):
        return self.y_doc

    def save_source(self):
        f = open(self.filename, "w")
        f.write(yaml.dump(self.y_doc, sort_keys=False, width=float("inf"), Dumper=Dumper))
        f.close()



class FontFiles:
    """ Keeps references to the font to be read (ufo or ttf) and the one to be
        written.
    """
    def __init__(self, source):
        """ Source is an internal representation of a yaml file, from which
            the names of the input and output font files can be retrieved.
        """
        self.data = source["font"]

    def in_font(self):
        if "in" in self.data:
            return self.data["in"]
        return None

    def out_font(self):
        if "out" in self.data:
            return self.data["out"]
        return None



class ygSourceable:
    def __init__(self, font, source):
        self.data = source
        self.font = font
        self._clean = True

    def clean(self):
        return self._clean

    def set_clean(self, c):
        self._clean = c
        if not self._clean:
            self.font.set_dirty()

    def source(self):
        return self.data

    def save(self, c):
        self.data = c
        self.set_clean(True)



class ygFont:
    """ Keeps all the font's data, including a fontTools representation of the
        font, the "source" structure built from the yaml file, and a structure
        for each section of the yaml file. All of the font data can be accessed
        through this class.

        Call this directly to open a font for the first time. After that,
        you only have to open the yaml file.
    """
    def __init__(self, source_file, yaml_filename=None):
        #
        # Open the font
        #
        self.source_file = SourceFile(source_file, yaml_filename=yaml_filename)
        d = None
        if isinstance(source_file, str) and source_file:
            d = os.path.dirname(source_file)
        elif yaml_filename:
            d = os.path.dirname(yaml_filename)
        if d and os.path.isdir(d) and d != os.getcwd():
            os.chdir(d)
        self.source      = self.source_file.get_source()
        self.font_files  = FontFiles(self.source)
        fontfile = self.font_files.in_font()
        try:
            self.ft_font = ttLib.TTFont(fontfile)
        except FileNotFoundError:
            raise Exception("Can't find font file " + str(fontfile))
        #
        # If it's a variable font, get a list of instances
        #
        try:
            self.instances = {}
            for inst in self.ft_font['fvar'].instances:
                nm = self.ft_font['name'].getName(inst.subfamilyNameID,3,1,0x409).toUnicode()
                self.instances[nm] = inst.coordinates
            self.is_variable_font = True
        except Exception as e:
            self.is_variable_font = False
        #
        # Set up access to YAML font data (if there is no cvt table yet, get some
        # values from the font).
        #
        self.glyphs      = ygGlyphs(self.source).data
        self.defaults    = ygDefaults(self, self.source)
        if len(self.source["cvt"]) == 0:
            cvt = self.source["cvt"]
            cvt["baseline"] = {"val": 0, "type": "pos", "vector": "y"}
            try:
                os2 = self.ft_font['OS/2']
                cvt["cap-height"] = {"val": os2.sCapHeight,
                                     "type": "pos",
                                     "vector": "y"}
                cvt["cap-height-overshoot"] = {"val": self.extreme_points("O")[0],
                                               "type": "pos",
                                               "vector": "y"}
                cvt["cap-baseline-undershoot"] = {"val": self.extreme_points("O")[1],
                                                "type": "pos",
                                                "vector": "y"}
                cvt["xheight"] = {"val": os2.sxHeight,
                                  "type": "pos",
                                  "vector": "y"}
                cvt["xheight-overshoot"] = {"val": self.extreme_points("o")[0],
                                            "type": "pos",
                                            "vector": "y"}
                cvt["lc-baseline-undershoot"] = {"val": self.extreme_points("o")[1],
                                            "type": "pos",
                                            "vector": "y"}
                cvt["lc-ascender"] = {"val": self.extreme_points("b")[0],
                                      "type": "pos",
                                      "vector": "y"}
                cvt["lc-descender"] = {"val": self.extreme_points("p")[1],
                                       "type": "pos",
                                       "vector": "y"}
            except Exception as e:
                print("Error while building cvt:")
                print(e)
                # pass
        self.cvt         = ygcvt(self, self.source)
        self.cvar        = ygcvar(self, self.source)
        self.prep        = ygprep(self, self.source)
        if "functions" in self.source:
            self.functions = self.source["functions"]
        else:
            self.functions = {}
        self.functions_func = ygFunctions(self, self.functions)
        if "macros" in self.source:
            self.macros = self.source["macros"]
        else:
            self.macros = {}
        self.macros_func = ygMacros(self, self.macros)
        #
        # Set up lists, indexes, and other data
        #
        self.glyph_list  = []
        self._clean       = True
        glyph_names = self.ft_font.getGlyphNames()
        cmap = self.ft_font['cmap'].buildReversed()
        # This dict is for using a glyph name to look up a glyph's index.
        # Composites are left out, since this program doesn't deal with them
        # (may decide, though, to display previews of them)
        self.name_to_index = {}
        raw_order_list = self.ft_font.getGlyphOrder()
        for order_index, gn in enumerate(raw_order_list):
            g = self.ft_font['glyf'][gn]
            if not g.isComposite():
                self.name_to_index[gn] = order_index
        # Get a list of tuples containing unicodes and glyph names. Still
        # omitting composites.
        for gn in glyph_names:
            g = self.ft_font['glyf'][gn]
            if not g.isComposite():
                cc = g.getCoordinates(self.ft_font['glyf'])
                if len(cc) > 0:
                    try:
                        u = cmap[gn]
                    except Exception:
                        u = 65535
                    if type(u) is set:
                        u = next(iter(u))
                    self.glyph_list.append((u, gn))
        self.glyph_list.sort(key = lambda x : x[1])
        self.glyph_list.sort(key = lambda x : x[0])
        self.glyph_index = {}
        for glyph_counter, g in enumerate(self.glyph_list):
            self.glyph_index[g[1]] = glyph_counter

    def extreme_points(self, glyph_name):
        """ Helper for setting up an initial cvt.

        """
        g = ygGlyph(None, self, glyph_name)
        highest = -10000
        lowest = 10000
        plist = g.point_list
        for p in plist:
            highest = max(highest, p.font_y)
            lowest = min(lowest, p.font_y)
        return highest, lowest

    def family_name(self):
        return self.ft_font['name'].getName(1,3,1,0x409)

    def style_name(self):
        return self.ft_font['name'].getName(2,3,1,0x409)

    def full_name(self):
        return str(self.family_name()) + "-" + str(self.style_name())

    def set_dirty(self):
        self._clean = False

    def set_clean(self):
        self._clean = True

    def clean(self):
        return self._clean

    def has_hints(self, gname):
        if not gname in self.glyphs:
            return False
        glyph_program = self.glyphs[gname]
        if not ("y" in glyph_program or "x" in glyph_program):
            return False
        y_len = 0
        x_len = 0
        if "y" in glyph_program and "points" in glyph_program["y"]:
            y_len = len(glyph_program["y"]["points"])
        if y_len == 0 and "x" in glyph_program and "points" in glyph_program["y"]:
            x_len = len(glyph_program["x"]["points"])
        if y_len == 0 and x_len == 0:
            return False
        return True

    def get_glyph(self, gname):
        """ Get the source for a glyph's hints. If the glyph has no hints yet,
            return an empty hint program.

        """
        try:
            return self.glyphs[gname]
        except KeyError:
            return {"y": {"points": []}}

    def get_glyph_index(self, gname):
        return self.name_to_index[gname]

    def save_glyph_source(self, source, vector, gname):
        """ Save a y or x block to the in-memory source.
        """
        if not gname in self.glyphs:
            self.glyphs[gname] = {}
        self.glyphs[gname][vector] = source



class ygprep(ygSourceable):
    def __init__(self, font, source):
        if "prep" in source:
            data = source["prep"]
        else:
            data = {}
        super().__init__(font, data)

    def save(self, c):
        self.data = c
        self.font.source["prep"] = c
        self.set_clean(True)



class ygDefaults(ygSourceable):
    def __init__(self, font, source):
        if "defaults" in source:
            data = source["defaults"]
        else:
            data = {}
        super().__init__(font, data)

    def get_default(self, *args):
        if args[0] in self.data:
            return self.data[args[0]]
        return None

    def set_default(self, **kwargs):
        for key, value in kwargs.items():
            self.data[key] = value

    def save(self, c):
        self.data = c
        self.font.source["defaults"] = c
        self.set_clean(True)



class ygcvt(ygSourceable):
    def __init__(self, font, source):
        if "cvt" in source:
            data = source["cvt"]
        else:
            data = {}
        super().__init__(font, data)

    def save(self, c):
        self.data = c
        self.font.source["cvt"] = c
        self.set_clean(True)

    def get_cvs(self, cvtype, vector):
        """ Get a list of control values filtered by type and vector.
        """
        result = {}
        keys = self.data.keys()
        for key in keys:
            entry = self.data[key]
            if type(entry) is dict:
                if "type" in entry and "vector" in entry:
                    if entry["type"] == cvtype and entry["vector"] == vector:
                        result[key] = entry["val"]
        return result

    def get_list(self, type, vector):
        """ Run get_cvs, then format for presentation in a menu
        """
        result = []
        cvt_matches = self.get_cvs(type, vector)
        for key in cvt_matches:
            result.append(key)
        return result

    def get_cv(self, name):
        """ Retrieve a control value by name. This will usually be a dict
            rather than just a number.

        """
        if name in self.data:
            return self.data[name]
        return None



class ygFunctions(ygSourceable):
    def __init__(self, font, source):
        super().__init__(font, source)

    def save(self, c):
        self.data = c
        self.font.source["functions"] = c
        self.set_clean(True)



class ygMacros(ygSourceable):
    def __init__(self, font, source):
        super().__init__(font, source)

    def save(self, c):
        self.data = c
        self.font.source["macros"] = c
        self.set_clean(True)



class ygcvar(ygSourceable):
    def __init__(self, font, source):
        try:
            data = source["cvar"]
        except Exception as e:
            data = []
        super().__init__(font, data)

    def save(self, c):
        self.data = c
        self.font.source["cvar"] = c
        self.set_clean(True)



class ygCaller:
    """ Superclass for function and macro calls.

    """
    def __init__(self, callable_type, name, font):
        if callable_type == "function":
            callables = font.functions
        else:
            callables = font.macros
        self.data = callables[name]

    def get_param(self, name):
        try:
            return self.data[name]
        except Exception:
            return None

    def number_of_point_params(self):
        keys = self.data.keys()
        param_count = 0
        for k in keys:
            if type(self.data[k]) is dict and "type" in self.data[k]:
                if self.data[k]["type"] == "point":
                    param_count += 1
        return param_count

    def point_params_range(self):
        """ The max in this range is the total number of point params. The
            min is the number of required point params (those without val
            attributes)
        """
        max_count = self.number_of_point_params()
        min_count = 0
        keys = self.data.keys()
        for k in keys:
            if type(self.data[k]) is dict and "type" in self.data[k] and not "val" in self.data[k]:
                if self.data[k]["type"] == "point":
                    min_count += 1
        return range(min_count, max_count+1)

    def point_list(self):
        """ Get a list of points (identifiers, not objects) from the dict of
            this callable's parameters.

        """
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k]:
                    if self.data[k]['type'] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def required_point_list(self):
        """ Get a list of points in this glyph's required parameters.

        """
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k] and not "val" in self.data[k]:
                    if self.data[k]['type'] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def optional_point_list(self):
        """ Get a list of points in this glyph's optional parameters.

        """
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k] and "val" in self.data[k]:
                    if self.data[k]['type'] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def non_point_params(self):
        """ Get a list of params that do not refer to points. For this to work
            properly, the params in the function definition have got to be
            defined carefully, with correct "type" attributes. This will return
            an empty list if there are no eligible params.

        """
        pdict = {}
        # These keys are for the list of params. Step through this and
        # select the non-point params.
        keys = self.data.keys()
        for k in keys:
            if k != "code" and k != "stack-safe" and  not ("type" in self.data[k] and self.data[k]['type'] == "point"):
                pdict[k] = self.data[k]
        return pdict



class ygFunction(ygCaller):
    def __init__(self, name, font):
        super().__init__("function", name, font)



class ygMacro(ygCaller):
    def __init__(self, name, font):
        super().__init__("macro", name, font)



class ygPoint:
    def __init__(self, name, index, x, y, _xoffset, _yoffset, on_curve, label_pref=None):
        self.id = uuid.uuid1()
        self.name = name
        self.index = index
        self.font_x = x
        self.font_y = y
        self.coord = "{" + str(self.font_x - _xoffset) + ";" + str(self.font_y - _yoffset) + "}"
        self.on_curve = on_curve
        self.label_pref = label_pref

    def preferred_label(self):
        if self.label_pref == "coord":
            return self.coord
        elif self.label_pref == "name" and self.name != None:
            return self.name
        elif self.label_pref == "index":
            return self.index
        if self.name != None:
            return self.name
        return self.index

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False



class ygParams:
    """ Parameters to be sent to a macro or function. There are two sets of
        these: one consisting of points, the other anything else (e.g. cvt
        indexes).

    """
    def __init__(self, hint_type, name, point_dict, other_params):
        self.hint_type = hint_type
        self.name = name
        self.point_dict = point_dict
        self.other_params = other_params

    def point_list(self):
        result = []
        k = self.point_dict.keys()
        for kk in k:
            result.append(self.point_dict[kk])
        return result



class ygSet:
    """ Xgridfit has a structure called a 'set'--just a simple list of points.
        This can be the target for a shift, align or interpolate instruction,
        and a two-member set can be reference for interpolate.

    """
    def __init__(self, point_list):
        self._point_list = point_list
        self.id = uuid.uuid1()
        # The main point is the one the arrow is connected to. It shouldn't be
        # needed now, but the editor uses it against the possibility that a set
        # will contain another set. See if this can be safely removed.
        self._main_point = None

    def point_list(self):
        return self._point_list

    def id_list(self):
        l = []
        for p in self._point_list:
            l.append(p.preferred_label())
        return l

    def main_point(self):
        """ Our use of an on-screen box may have made this useless. See if we
            can get rid of it.

        """
        if self._main_point:
            return self._main_point
        else:
            return self._point_list[0]

    def point_at_index(self, index):
        """ Instead of failing when index is out of range, return the last
            item in the list.
        """
        try:
            return self.point_list[index]
        except Exception:
            return self.point_list[-1]



class ygGlyph(QObject):
    """ Keeps all the data for one glyph and provides an interface for
        changing it.

        Parameters:

        preferences (ygPreferences.ygPreferences): Preferences for the app.

        yg_font (ygFont): The font object, providing access to the fontTools
        representation and the whole of the hinting source.

        gname (str): The name of this glyph.

    """

    sig_hints_changed = pyqtSignal(object)
    sig_glyph_source_ready = pyqtSignal(object)

    def __init__(self, preferences, yg_font, gname):
        """ Requires a ygFont object and the name of the glyph. Also access to preferences
            as a convenience.
        """
        super().__init__()
        self.preferences = preferences
        self.yaml_editor = None
        self.yg_font = yg_font
        self.gsource = yg_font.get_glyph(gname)
        self.gname = gname
        if "names" in self.gsource:
            self.names = copy.deepcopy(self.gsource["names"])
        else:
            self.names = {}
        if "props" in self.gsource:
            self.props = copy.deepcopy(self.gsource["props"])
        else:
            self.props = {}
        if "y" in self.gsource:
            self.y_block = self.combine_point_blocks(copy.deepcopy(self.gsource["y"]))
        else:
            self.y_block = []
        if "x" in self.gsource:
            self.x_block = self.combine_point_blocks(copy.deepcopy(self.gsource["x"]))
        else:
            self.x_block = []
        self.set_clean()
        try:
            self.ft_glyph = yg_font.ft_font['glyf'][gname]
        except KeyError:
            # This shouldn't happen: we should intercept bad gnames before we
            # get here.
            raise Exception("Tried to load nonexistent glyph " + gname)

        # Going to run several indexes for this glyph's points. This is because
        # Xgridfit is permissive about naming, so we need several ways to look
        # up points. (Check later to make sure all these are being used.)

        # Extract points from the fontTools Glyph object and store them in a list.
        self.point_list = self._make_point_list()
        # Dict for looking up points with uuid-generated id.
        self.point_id_dict = {}
        for p in self.point_list:
            self.point_id_dict[p.id] = p
        # Dict for looking up points by coordinates
        self.point_coord_dict = {}
        for p in self.point_list:
            self.point_coord_dict[p.coord] = p
        if self.preferences:
            self._current_vector = self.preferences["current_vector"]
        else:
            self._current_vector = "y"
        # Fix up the source and build a tree of ygHhint objects.
        self._yaml_add_parents(self.current_block())
        self._yaml_supply_refs(self.current_block())
        # This is the QGraphicsScene wrapper for this glyph object. But
        # do we need a reference here in the __init__? It's only used once,
        # in setting up a signal, and there are other ways to do that.
        self.glyph_viewer = None

        self.sig_hints_changed.connect(self.hints_changed)

    #
    # Ordering and structuring YAML source
    #

    def _flatten_yaml_tree(self, tree):
        """ Helper for rebuild_current_block

        """
        flat = []
        for t in tree:
            if "parent" in t:
                del t["parent"]
            flat.append(t)
            if "points" in t:
                flat.extend(self._flatten_yaml_tree(t["points"]))
        return flat

    def place_all(self, hl):
        block = []
        unplaced = copy.copy(hl)
        placed = []
        placed_len = 0
        while True:
            last_placed_len = placed_len
            for h in hl:
                if not h in placed:
                    r = self._add_hint(h, block, conditional=True)
                    if r:
                        placed.append(h)
                        if h in unplaced:
                            unplaced.remove(h)
                    else:
                        unplaced.append(h)
            # There are two ways this loop breaks: 1) when nothing has been
            # done on this iteration (the length of "placed" has not changed)
            # and 2) the length of "unplaced" is zero
            # if last_placed_len == placed_len:
            if last_placed_len == len(placed):
                break
            if len(unplaced) == 0:
                break
        # If there are still unplaced hints after the while loop, append them
        # to the top level of the tree.
        if len(unplaced) > 0:
            for u in unplaced:
                block.append(u)
        return block

    def rebuild_current_block(self):
        print("running rebuild_current_block")
        flattened_tree = self._flatten_yaml_tree(copy.deepcopy(self.current_block()))
        for f in flattened_tree:
            if "points" in f:
                del f["points"]
        new_tree = ygHintSorter(self.place_all(flattened_tree)).sort()
        if self.current_vector() == "y":
            self.y_block = new_tree
        else:
            self.x_block = new_tree
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    def _yaml_mk_hint_list(self, source):
        """ 'source' is a yaml "points" block--a list.

        """
        flist = []
        for pt in source:
            flist.append(ygHint(self, pt))
            if ("points" in pt) and pt["points"]:
                flist.extend(self._yaml_mk_hint_list(pt['points']))
        return flist

    def _yaml_add_parents(self, node):
        """ Walk through the yaml source for one 'points' block, adding 'parent'
            items to each point dict so that we can easily climb the tree if we
            have to.

            We do this (and also supply refs) when we copy a "y" or "x" block
            from the main source file so we don't have to do it elsewhere.

        """
        for pt in node:
            if "points" in pt:
                for ppt in pt["points"]:
                    ppt["parent"] = pt
                self._yaml_add_parents(pt['points'])
        if self._current_vector == "y":
            self.y_block = node
        else:
            self.x_block = node

    def _yaml_supply_refs(self, node):
        """ After "parent" properties have been added, walk the tree supplying
            implicit references. If we can't find a reference, let it go (it
            doesn't seem to actually happen).

        """
        if type(node) is list:
            for n in node:
                type_num = hint_type_nums[self._yaml_hint_type(n)]
                if type_num in [1, 3]:
                    if "parent" in n and not "ref" in n:
                        n['ref'] = self._yaml_get_single_target(n['parent'])
                    else:
                        pass
                if type_num == 2:
                    reflist = []
                    if "parent" in n:
                        reflist.append(self._yaml_get_single_target(n['parent']))
                        if "parent" in n["parent"]:
                            reflist.append(self._yaml_get_single_target(n["parent"]["parent"]))
                    if len(reflist) == 2 and not "ref" in n:
                        n["ref"] = reflist
                if "points" in n:
                    self._yaml_supply_refs(n['points'])
            if self._current_vector == "y":
                self.y_block = node
            else:
                self.x_block = node

    def yaml_strip_extraneous_nodes(self, node):
        """ Walks the yaml tree, stripping out parent references and
            explicit statements of implicit refs.

        """
        for pt in node:
            if "parent" in pt:
                h = ygHint(self, pt["parent"])
                if ((not h.hint_type() in ["function", "macro"]) and
                    len(h.target_list()) == 1):
                    del pt["ref"]
                del pt["parent"]
            if "points" in pt:
                self.yaml_strip_extraneous_nodes(pt["points"])

    def _yaml_get_single_target(self, node):
        """ This is for building the yaml tree. We need a single point (not a
            list or dict) to hook a ref to. As we go through the possiblities
            here, the returns become less plausible, but are always valid. The
            caller doesn't have to deal with a null point.

        """
        if type(node["ptid"]) is str or type(node["ptid"]) is int:
            return node["ptid"]
        if type(node["ptid"]) is list:
            return node["ptid"][0]
        if type(node["ptid"]) is dict:
            k = node["ptid"].keys()
            random_point = 0
            for kk in k:
                random_point = node["ptid"][kk]
                if type(random_point) is not list:
                    break
            if type(random_point) is list:
                return(random_point[0])
            else:
                return random_point
        return 0

    #
    # Accessing glyph data
    #

    def current_vector(self):
        return self._current_vector

    def current_block(self):
        if self._current_vector == "y":
            return self.y_block
        else:
            return self.x_block

    def hints(self):
        """ Get a list of hints for the current vector, wrapped in ygHint
            objects.

        """
        return self._yaml_mk_hint_list(self.current_block())

    def points(self):
        return self.point_list

    def search_source(self, block, pt, ptype):
        """ Search the yaml source for a point.

            Parameters:
            block (list): At the top level, should be self.current_block().

            pt (ygPoint, int, or str): The point we're searching for

            ptype (str): "ptid" to search for target points, "ref" to search
            for ref points.

        """

        def pt_to_index(ppp):
            if type(ppp) is ygPoint:
                return ppp.index
            return ppp

        result = []
        yaml_tree = self.current_block()
        yg_pt = self.resolve_point_identifier(pt)
        if type(yg_pt) is ygSet:
            yg_pt = yg_pt.point_list()
        elif type(yg_pt) is ygPoint:
            yg_pt = [yg_pt.index]
        else:
            yg_pt = []
        yg_pt = list(map(pt_to_index, yg_pt))
        for ppt in block:
            pppt = []
            if ptype in ppt:
                if ptype == "ref":
                    if type(ppt["ref"]) is not list:
                        pppt = [ppt["ref"]]
                else:
                    pppt = ygHint(self, ppt).target_list()
                if any(elem in pppt for elem in yg_pt):
                    result.append(ppt)
            if "points" in ppt and len(ppt["points"]) > 0:
                result.extend(self.search_source(ppt["points"], yg_pt, ptype))
        return result

    def glyph_name(self):
        return self.gname

    def xoffset(self):
        if "xoffset" in self.props:
            return self.props["xoffset"]
        return 0

    def yoffset(self):
        if "yoffset" in self.props:
            return self.props["yoffset"]
        return 0

    def _yaml_hint_type(self, n):
        if "function" in n:
            return "function"
        if "macro" in n:
            return "macro"
        if "rel" in n:
            return n["rel"]
        return "anchor"

    def _is_pt_obj(self, o):
        """ Whether an object is a 'point object' (a point or a container for
            points), which can appear in a ptid or ref field.

        """
        return type(o) is ygPoint or type(o) is ygSet or type(o) is ygParams

    def _make_point_list(self):
        """ Make a list of the points in a fontTools glyph structure.

            Returns:
            A list of ygPoint objects.

        """
        pt_list = []
        gl = self.ft_glyph.getCoordinates(self.yg_font.ft_font['glyf'])
        for point_index, p in enumerate(zip(gl[0], gl[2])):
            is_on_curve = p[1] & 0x01 == 0x01
            pt = ygPoint(None, point_index, p[0][0], p[0][1], self.xoffset(), self.yoffset(), is_on_curve)
            pt_list.append(pt)
        return(pt_list)

    #
    # Navigation
    #

    def switch_to_vector(self, new_vector):
        if self._current_vector == new_vector:
            return
        self.save_source()
        self._current_vector = new_vector
        self.preferences["current_vector"] = new_vector
        self._yaml_add_parents(self.current_block())
        self._yaml_supply_refs(self.current_block())
        # self.sig_hints_changed.emit(self.hints())
        self._hints_changed(self.hints(), dirty=False)
        self.send_yaml_to_editor()

    #
    # Saving
    #

    def save_editor_source(self, s):
        """ When the user has typed Ctrl+R to compile the contents of the
            editor pane, this function gets called to do the rest. It
            massages the yaml source exactly as the __init__for this class
            does (calling the same functions) and installs new source
            in self.current_block(). Finally it
            sends sig_hints_changed to notify that the hints are ready to
            render and sends reconstituted source back to the editor.
        """
        try:
            if self.current_vector() == "y":
                self.y_block = s
            else:
                self.x_block = s
            self._yaml_add_parents(self.current_block())
            self._yaml_supply_refs(self.current_block())
            self.sig_hints_changed.emit(self.hints())
            self.send_yaml_to_editor()
        except Exception as e:
            self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])

    def save_source(self):
        """ Saves the current block (y or x) to the in-memory yaml source.
            This does not save to disk, but it must be run before saving to
            disk.

        """
        if not self.clean():
            tcopy = copy.deepcopy(self.current_block())
            self.yaml_strip_extraneous_nodes(tcopy)
            self.yg_font.save_glyph_source({"points": tcopy},
                                           self.current_vector(),
                                           self.gname)
            self.set_clean()
        # Also save the other things (cvt, etc.) if dirty.

    #
    # Editing
    #

    def combine_point_blocks(self, block):
        if len(block) > 0:
            new_block = []
            k = block.keys()
            for kk in k:
                new_block.extend(block[kk])
            return new_block
        return None

    def _add_hint(self, h, block, conditional=False):
        """ If conditional=False, function will always place a hint somewhere
            in the tree (in the top level when it can't find another place).
            When True, function will return False when it fails to place the
            hint in the tree.
        """
        ref = None
        if type(h) is ygHint:
            h = h.source()
        if "ref" in h:
            ref = h["ref"]
        if ref == None or type(ref) is list:
            block.append(h)
        else:
            matches = self.search_source(block, ref, "ptid")
            if len(matches) > 0:
                if not "points" in matches[0]:
                    matches[0]["points"] = []
                matches[0]["points"].append(h)
                h["parent"] = matches[0]
            else:
                if conditional:
                    return False
                else:
                    block.append(h)
        return True

    def add_hint(self, h):
        self._add_hint(h, self.current_block())
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    def delete_hints(self, l):
        """ l: a list of ygHint objects
        """
        for h in l:
            s = h._source
            if "parent" in s:
                try:
                    s["parent"]["points"].remove(s)
                except Exception as e:
                    pass
            else:
                try:
                    self.current_block().remove(s)
                except Exception as e:
                    pass
            if "points" in s:
                for hh in s["points"]:
                    try:
                        if not "rel" in hh or hint_type_nums[hh["rel"]] == 4:
                            self.add_hint(ygHint(self, hh))
                    except Exception as e:
                        pass
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    def set_dirty(self):
        self._clean = False
        self.yg_font.set_dirty()

    def set_clean(self):
        self._clean = True

    def clean(self):
        return self._clean

    def points_to_labels(self, pts):
        """ Accepts a ygPoint, ygSet or ygParams object and converts it to a
            thing digestible by the yaml processor.

        """
        if type(pts) is str or type(pts) is int:
            return pts
        if type(pts) is list:
            result = []
            for p in pts:
                if type(p) is ygPoint:
                    result.append(p.preferred_label())
            return result
        if type(pts) is ygSet:
            return self.points_to_labels(pts.point_list())
        if type(pts) is ygParams:
            pp = pts.point_list()
            result = []
            for p in pp:
                if type(p) is ygPoint:
                    result.append(p.preferred_label())
                elif type(p) is list:
                    result.extend(self.points_to_labels(p))
            return result
        if type(pts) is ygPoint:
            return(pts.preferred_label())
        return 0

    def resolve_point_identifier(self, ptid, depth=0):
        """ Get the ygPoint object identified by ptid. ***Failures are very
            possible here, since there may be nonsense in a source file or in
            the editor. Figure out how to handle failures gracefully.

            (Instead of crashing, return None. Caller can respond by marking a
            hint invalid, to be skipped over when generating xgf or rendering
            on screen)

            Parameters:
            ptid (int, str): An identifier for a point. Xgridfit allows them
            to be in any of three styles: int (the raw index of the point),
            coordinates (in the format "{100;100}"), or name (from the
            glyph's "names" section). The identifier may point to a single
            point, a list of points, or a dict (holding named parameters for
            a macro or function).

            depth (int): How deeply nested we are. We give up if we get to 20.

            Returns:
            ygPoint, ygSet, ygParams: Depending whether the input was a point,
            a list of points, or a dict of parameters for a macro or function
            call.

        """
        result = ptid
        if self._is_pt_obj(ptid):
            return result
        if type(ptid) is list:
            new_list = []
            for p in ptid:
                new_list.append(self.resolve_point_identifier(p, depth=depth+1))
            return ygSet(new_list)
        elif type(ptid) is dict:
            new_dict = {}
            key_list = ptid.keys()
            for key in key_list:
                p = self.resolve_point_identifier(ptid[key], depth=depth+1)
                new_dict[key] = p
            return ygParams(None, None, new_dict, None)
        elif type(ptid) is int:
            try:
                result = self.point_list[ptid]
                if self._is_pt_obj(result):
                    return result
            except IndexError:
                m =  "A point index is out of range. This glyph may have been "
                m += "edited since its hints were written, and if so, they "
                m += "will have to be redone."
                self.preferences.top_window().show_error_message(["Error", "Error", m])
                # Return an erroneous but safe number (it shouldn't make the
                # program crash).
                return self.point_list[0]
        elif ptid in self.point_coord_dict:
            result = self.point_coord_dict[ptid]
            if self._is_pt_obj(result):
                return result
        elif self.names != None and ptid in self.names:
            result = self.names[ptid]
            if self._is_pt_obj(result):
                return result
        if result == None:
            raise Exception("obj " + str(ptid) + " resolved to None")
        if depth > 20:
            raise Exception("Failed to resolve point identifier " + str(ptid) + " (" + str(result) + ")")
        result = self.resolve_point_identifier(result, depth=depth+1)
        if self._is_pt_obj(result):
            return result

    #
    # Signals and slots
    #

    def set_yaml_editor(self, ed):
        """ Registers a slot in a ygYAMLEditor object, for installing source.

        """
        self.sig_glyph_source_ready.connect(ed.install_source)
        self.send_yaml_to_editor()

    def send_yaml_to_editor(self):
        """ Sends yaml source for the current x or y block to the editor pane.

        """
        new_yaml = copy.deepcopy(self.current_block())
        self.yaml_strip_extraneous_nodes(new_yaml)
        self.sig_glyph_source_ready.emit(yaml.dump(new_yaml, sort_keys=False, Dumper=Dumper))

    def hint_changed(self, h):
        """ Called by signal from ygHint. Rebuilds the hint tree in response.

        """
        self.set_dirty()
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    def refresh_hints(self):
        self.sig_hints_changed.emit(self.hints())

    @pyqtSlot(object)
    def hints_changed(self, hint_list):
        self._hints_changed(hint_list)

    def _hints_changed(self, hint_list, dirty=True):
        """ Called by signal. *** Is this the best way to do this? Calling
            ygGlyphView directly? Figure out something else (compare
            sig_glyph_source_ready, for which we didn't have to import
            anything).***

        """
        if dirty:
            self.set_dirty()
        from .ygHintEditor import ygGlyphViewer
        if self.glyph_viewer:
            self.glyph_viewer.install_hints(hint_list)



class ygGlyphs:
    """ The "glyphs" section of a yaml file.

    """
    def __init__(self, source):
        self.data = source["glyphs"]

    def get_glyph(self, gname):
        if gname in self.data:
            return self.data[gname]
        else:
            return {}



class Comparable(object):
    """ For ordering hints.
    """
    def _compare(self, other, method):
        try:
            return method(self._cmpkey(), other._cmpkey())
        except (AttributeError, TypeError):
            return NotImplemented

    def _mk_point_list(self, obj, key):
        """ Helper for comparison functions. For target points, this will
            recurse into dependent hints to build a complete list.

        """
        hint = ygHint(None, obj)
        if key == "ptid":
            p = hint.target()
        else:
            p = hint.ref()
        result = []
        if type(p) is dict:
            k = p.keys()
            for kk in k:
                if type(p[kk]) is list:
                    result.extend(p[kk])
                else:
                    result.append(p[kk])
        elif type(p) is list:
            result.extend(p)
        else:
            result.append(p)
        if "points" in obj and key == "ptid":
            for o in obj["points"]:
                result.extend(self._mk_point_list(o, key))
        return(result)

    def _comparer(self, obj1, obj2):
        """ Helper for comparison functions. A return value of zero doesn't
            mean "equal," but rather "no match," which should (like "equal")
            result in no reordering of hints. Actually equal hints should not
            ordinarily occur.

        """
        p1 = self._mk_point_list(obj1, "ptid")
        p2 = self._mk_point_list(obj2, "ptid")
        r1 = self._mk_point_list(obj1, "ref")
        r2 = self._mk_point_list(obj2, "ref")

        if r2 != None:
            for r in r2:
                if r != None and r in p1:
                    return -1
        if r1 != None:
            for r in r1:
                if r != None and r in p2:
                    return 1
        return 0

    def __eq__(self, other):
        return self == other

    def __ne__(self, other):
        return self != other

    def __lt__(self, other):
        return self._comparer(self._source, other._source) < 0

    def __gt__(self, other):
        return self._comparer(self._source, other._source) > 0

    def __ge__(self, other):
        return (self._comparer(self._source, other._source) > 0 or
                self._source == other._source)

    def __le__(self, other):
        return (self._comparer(self._source, other._source) < 0 or
                self._source == other._source)



class ygHintSource(Comparable):
    def __init__(self, s):
        self._source = s

    def _cmpkey(self):
        return (self._source,)

    def __hash__(self):
        return hash(self._cmpkey())



class ygHint(QObject):
    """ A hint. This wraps a point from the yaml source tree and provides
        a number of functions for accessing and altering it.

        Parameters:

        glyph (ygGlyph): The glyph for which this is a hint.

        point: The point, list or dict that is the target of this hint.

    """

    hint_changed_signal = pyqtSignal(object)

    def __init__(self, glyph, point):
        super().__init__()
        self.id = uuid.uuid1()
        self._source = point
        self.yg_glyph = glyph

        if self.yg_glyph != None:
            self.hint_changed_signal.connect(self.yg_glyph.hint_changed)

    def source(self):
        return(self._source)

    def parent(self):
        if "parent" in self.source:
            return self._source["parent"]
        return None

    def children(self):
        if "points" in self._source:
            return self._source["points"]

    def target(self):
        """ May return a point identifier (index, name, coordinate-pair), a list,
            or a dict.

        """
        return self._source["ptid"]

    def target_list(self):
        """ Always returns a list. Does not recurse.

        """
        t = self.target()
        if type(t) is list:
            return t
        elif type(t) is dict:
            result = []
            v = t.values()
            for vv in v:
                if type(vv) is list:
                    result.extend(vv)
                else:
                    result.append(vv)
            return result
        else:
            return [t]

    def ref(self):
        if "ref" in self._source:
            return self._source["ref"]
        return None

    def set_target(self, tgt):
        """ tgt can be a point identifier or a set of them. no ygPoint objects.
        """
        self._source["ptid"] = tgt

    def hint_type(self):
        if "macro" in self._source:
            return "macro"
        if "function" in self._source:
            return "function"
        if "rel" in self._source:
            return self._source["rel"]
        return "anchor"

    def can_be_reversed(self):
        no_func = not "function" in self._source
        no_macro = not "macro" in self._source
        has_eligible_ref = "ref" in self._source and (type(self._source["ref"]) is not list)
        has_eligible_target = "ptid" in self._source and (type(self._source["ptid"]) is not list)
        return has_eligible_ref and has_eligible_target and no_func and no_macro

    def reverse_hint(self, h):
        if self.can_be_reversed():
            self._source["ptid"], self._source["ref"] = self._source["ref"], self._source["ptid"]
            self.hint_changed_signal.emit(h)

    def swap_macfunc_points(self, new_name, old_name):
        if type(self._source["ptid"]) is dict:
            try:
                self._source["ptid"][new_name], self._source["ptid"][old_name] = self._source["ptid"][old_name], self._source["ptid"][new_name]
            except Exception as e:
                self._source["ptid"][new_name] = self._source["ptid"][old_name]
                del self._source["ptid"][old_name]
            self.hint_changed_signal.emit(self)

    def change_hint_color(self, new_color):
        self._source["rel"] = new_color
        self.hint_changed_signal.emit(self)

    def rounded(self):
        if "round" in self._source:
            return self._source["round"]
        return self.round_is_default()

    def toggle_rounding(self):
        if "round" in self._source:
            current_round = self._source["round"]
        else:
            current_round = self.round_is_default()
        current_round = not current_round
        if current_round == self.round_is_default():
            if "round" in self._source:
                del self._source["round"]
        else:
            self._source["round"] = current_round
        self.hint_changed_signal.emit(self)

    def round_is_default(self):
        return hint_type_nums[self.hint_type()] in [0, 3]

    def ref_is_implicit(self):
        """ Whether it's okay to delete the ref for this hint. If the yaml
            point structure has a parent, the ref here can be deleted.

        """
        return "parent" in self._source

    def cv(self):
        if "pos" in self._source:
            return self._source["pos"]
        if "dist" in self._source:
            return self._source["dist"]
        if "cv" in self._source:
            return self._source["cv"]
        return None

    def required_cv_type(self):
        hnum = hint_type_nums[self.hint_type()]
        if hnum == 0:
            return("pos")
        if hnum == 3:
            return("dist")
        return None

    def set_cv(self, new_cv):
        """ Does not work for functions and macros. Those must be changed
            through the GUI.

        """
        cvtype = self.required_cv_type()
        if cvtype:
            if new_cv == "None":
                if cvtype in self._source:
                    del self._source[cvtype]
            else:
                self._source[cvtype] = new_cv
        self.hint_changed_signal.emit(self)

    def hint_has_changed(self, h):
        self.hint_changed_signal.emit(h)

    def add_hint(self, hint):
        """ Add a hint. This simply calls add_hint in the glyph

        """
        self.yg_glyph.add_hint(hint)
        # ygGlyph.add_hint will emit the hint changed signal.

    def delete_hints(self, hint_list):
        """ Delete a hint from the hint tree.

        """
        self.yg_glyph.delete_hints(hint_list)

    def _hint_string(self):
        result = "Hint target: "
        result += str(self._source["ptid"])
        if "ref" in self._source:
            result += "; ref: "
            result += str(self._source["ref"])
        if "parent" in self._source:
            result += "; parent: "
            result += str(self._source["parent"]["ptid"])
        return result

    def _get_macfunc(self):
        if "function" in self._source:
            return self._source["function"]
        elif "macro" in self._source:
            return self._source["macro"]
        return None

    def macfunc_name(self):
        macfunc = self._get_macfunc()
        if type(macfunc) is dict:
            return(macfunc["nm"])
        if type(macfunc) is str:
            return(macfunc)
        return None

    def macfunc_other_args(self):
        macfunc = self._get_macfunc()
        other_params = {}
        if type(macfunc) is dict:
            other_params = {key: val for key, val in macfunc.items() if not key in ['nm', 'code']}
        if len(other_params) > 0:
            return other_params
        return None

    def print(*args, **kwargs):
        __builtin__.print(self._hint_string)
        return __builtin__.print(*args, **kwargs)

    def __str__(self):
        return self._hint_string()

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False



class ygHintSorter:
    """ Will sort a (flat) list of hints into an order where hints with touched
        points occur earlier in the list than hints with refs pointing to those
        touched points. This sometimes fails, and I'm not sure why. See classes
        ygModel.Comparable and ygModel.ygHintSource, helpers for this class.

    """
    def __init__(self, list):
        self.list = list

    def sort(self):
        sortable = []
        for l in self.list:
            sortable.append(ygHintSource(l))
        ll = sorted(sortable)
        result = []
        for l in ll:
            result.append(l._source)
        return result



class ygPointSorter:
    """ Will sort a list of points into left-to-right or up-to-down order,
        depending on the current vector.

    """
    def __init__(self, vector):
        self.vector = vector

    def _ptcoords(self, p):
        if self.vector == "y":
            return p.font_x
        else:
            return p.font_y

    def sort(self, pt_list):
        pt_list.sort(key=self._ptcoords)
