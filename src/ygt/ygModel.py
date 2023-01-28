from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QUndoCommand, QUndoStack
from fontTools import ttLib
import yaml
from yaml import Dumper
import os
import uuid
import copy
import unicodedata
from .ygPreferences import ygPreferences

hint_type_nums  = {"anchor": 0, "align": 1, "shift": 1, "interpolate": 2,
                   "stem": 3, "whitespace": 3, "blackspace": 3, "grayspace": 3,
                   "move": 3, "macro": 4, "function": 4}

unicode_categories = ["Lu", "Ll", "Lt", "LC", "Lm", "Lo", "L", "Mn", "Mc",
                      "Me", "M", "Nd", "Nl", "No", "N", "Pc", "Pd", "Ps",
                      "Pe", "Pi", "Pf", "Po", "P", "Sm", "Sc", "Sk", "So",
                      "S", "Zs", "Zl", "Zp", "Z", "Cc", "Cf", "Cs", "Co",
                      "Cn", "C"]

unicode_cat_names = {"Lu":   "Letter, uppercase",
                     "Ll":   "Letter, lowercase",
                     "Lt":   "Letter, titlecase",
                     "LC":   "Letter, cased",
                     "Lm":   "Letter, modifier",
                     "Lo":   "Letter, other",
                     "L":    "Letter",
                     "Mn":   "Mark, nonspacing",
                     "Mc":   "Mark, spacing",
                     "Me":   "Mark, enclosing",
                     "M":    "Mark",
                     "Nd":   "Number, decimal",
                     "Nl":   "Number, letter",
                     "No":   "Number, other",
                     "N":    "Number",
                     "Pc":   "Punctuation, connector",
                     "Pd":   "Punctuation, dash",
                     "Ps":   "Punctuation, open",
                     "Pe":   "Punctuation, close",
                     "Pi":   "Punctuation, initial quote",
                     "Pf":   "Punctuation, final quote",
                     "Po":   "Punctuation, other",
                     "P":    "Punctuation",
                     "Sm":   "Symbol, math",
                     "Sc":   "Symbol, currency",
                     "Sk":   "Symbol, modifier",
                     "So":   "Symbol, other",
                     "S":    "Symbol",
                     "Zs":   "Separator, space",
                     "Zl":   "Separator, line",
                     "Zp":   "Separator, paragraph",
                     "Z":    "Separator",
                     "Cc":   "Other, control",
                     "Cf":   "Other, format",
                     "Cs":   "Other, surrogate",
                     "Co":   "Other, private use",
                     "Cn":   "Other, not assigned",
                     "C":    "Other"}

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
# ygGlyphProperties: Keeps miscellaneous properties for a glyph.
# ygGlyphNames: Keeps named points and sets.
# glyphSaver: Utility for undo/redo system.
# glyphEditCommand(QUndoCommand): superclass for most editing commands.
# changePointNumbersCommand(glyphEditCommand): Glyph editing command
# updateSourceCommand(glyphEditCommand): Glyph editing command
# replacePointNamesCommand(glyphEditCommand): Glyph editing command.
# replaceGlyphPropsCommand(glyphEditCommand): Glyph editing command.
# addPointSetNameCommand(glyphEditCommand): Glyph editing command.
# setMacFuncOtherArgsCommand(glyphEditCommand): Glyph editing command.
# swapMacFuncPointsCommand(glyphEditCommand): Glyph editing command.
# changeDistanceTypeCommand(glyphEditCommand): Glyph editing command.
# toggleMinDistCommand(glyphEditCommand): Glyph editing command.
# changeCVCommand(glyphEditCommand): Glyph editing command.
# toggleRoundingCommand(glyphEditCommand): Glyph editing command.
# makeSetCommand(glyphEditCommand): Glyph editing command.
# addHintCommand(glyphEditCommand): Glyph editing command.
# cleanupGlyphCommand(glyphEditCommand): Glyph editing command.
# deleteHintsCommand(glyphEditCommand): Glyph editing command.
# reverseHintCommand(glyphEditCommand): Glyph editing command.
# switchAxisCommand(QUndoCommand): Glyph editing command.
# glyphAddPropertyCommand(QUndoCommand): Glyph editing command.
# glyphDeletePropertyCommand(QUndoCommand): Glyph editing command.
# ygGlyph(QObject): Keeps data for the current glyph.
# ygGlyphs: Collection of this font's glyphs.
# Comparable: superclass for ygHintSource: for ordering hints.
# ygHintSource(Comparable): Wrapper for hint source: use when sorting.
# ygHint(QObject): One hint (including a function or macro call).
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
    """ Superclass for a number of ygt classes that represent chunks
        of source code.
    """
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
    def __init__(self, main_window, source_file, yaml_filename=None):
        self.main_window = main_window
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
        self.preview_font = copy.deepcopy(self.ft_font)
        #
        # If it's a variable font, get instances and axes
        #
        try:
            self.instances = {}
            for inst in self.ft_font['fvar'].instances:
                nm = self.ft_font['name'].getName(inst.subfamilyNameID,3,1,0x409).toUnicode()
                self.instances[nm] = inst.coordinates
            self.axes = self.ft_font['fvar'].axes
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
            cvt["baseline"] = {"val": 0, "type": "pos", "axis": "y"}
            try:
                os2 = self.ft_font['OS/2']
                cvt["cap-height"] =              {"val": os2.sCapHeight,
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Lu"}
            except Exception:
                pass
            try:
                os2 = self.ft_font['OS/2']
                cvt["xheight"] =                 {"val": os2.sxHeight,
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Ll"}
            except Exception:
                pass
            try:
                cvt["cap-height-overshoot"] =    {"val": self.extreme_points("O")[0],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Lu",
                                                  "same-as": {"below": {"ppem": 40, "cv": "cap-height"}}}
                cvt["cap-baseline-undershoot"] = {"val": self.extreme_points("O")[1],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Lu",
                                                  "same-as": {"below": {"ppem": 40, "cv": "baseline"}}}
            except Exception:
                pass
            try:
                cvt["xheight-overshoot"] =       {"val": self.extreme_points("o")[0],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Ll",
                                                  "same-as": {"below": {"ppem": 40, "cv": "xheight"}}}
                cvt["lc-baseline-undershoot"] =  {"val": self.extreme_points("o")[1],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Ll",
                                                  "same-as": {"below": {"ppem": 40, "cv": "baseline"}}}
            except Exception:
                pass
            try:
                cvt["lc-ascender"] =             {"val": self.extreme_points("b")[0],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Ll"}
            except Exception:
                pass
            try:
                cvt["lc-descender"] =            {"val": self.extreme_points("p")[1],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Ll"}
            except Exception:
                pass
            try:
                cvt["num-round-top"] =           {"val": self.extreme_points("eight")[0],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Nd",
                                                  "same-as": {"below": {"ppem": 40, "cv": "num-flat-top"}}}
                cvt["num-baseline-undershoot"] = {"val": self.extreme_points("eight")[1],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Nd",
                                                  "same-as": {"below": {"ppem": 40, "cv": "baseline"}}}
            except Exception:
                pass
            try:
                cvt["num-flat-top"] =            {"val": self.extreme_points("five")[0],
                                                  "type": "pos",
                                                  "axis": "y",
                                                  "cat": "Nd"}
            except Exception:
                pass
        self.cvt         = ygcvt(self,  self.source)
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

        # dict of {glyph_name: unicode}.
        self.cmap = self.ft_font['cmap'].buildReversed()

        # This dict is for using a glyph name to look up a glyph's index.
        # Composites are left out, since this program doesn't deal with them
        # (may decide, though, to display previews of them)
        self.name_to_index = {}
        raw_order_list = self.ft_font.getGlyphOrder()
        for order_index, gn in enumerate(raw_order_list):
            self.name_to_index[gn] = order_index
            #g = self.ft_font['glyf'][gn]
            #if not g.isComposite():
            #    self.name_to_index[gn] = order_index

        # Get a list of tuples containing unicodes and glyph names (still
        # omitting composites). Sort first by unicode, then by name. This
        # is our order for the font.
        for gn in glyph_names:
            g = self.ft_font['glyf'][gn]
            if not g.isComposite():
                cc = g.getCoordinates(self.ft_font['glyf'])
                if len(cc) > 0:
                    # u = self.get_unicode(gn)
                    self.glyph_list.append((self.get_unicode(gn), gn))
        self.glyph_list.sort(key = lambda x : x[1])
        self.glyph_list.sort(key = lambda x : x[0])

        self.unicode_to_name = {}
        for g in self.glyph_list:
            self.unicode_to_name[g[0]] = g[1]

        # Like name_to_index, but this one looks up the index in a slimmed-down,
        # non-composite-only list. This is for navigating in this program.
        self.glyph_index = {}
        for glyph_counter, g in enumerate(self.glyph_list):
            self.glyph_index[g[1]] = glyph_counter

    def default_instance(self):
        if not self.is_variable_font:
            return None
        default_coordinates = {}
        for a in self.axes:
            default_coordinates[a.axisTag] = a.defaultValue
        def_inst = None
        kk = self.instances.keys()
        for k in kk:
            if self.instances[k] == default_coordinates:
                def_inst = k
                break
        return def_inst

    def get_unicode(self, glyph_name, extended=False):
        u = 65535
        try:
            u = self.cmap[glyph_name]
        except Exception:
            if extended and ("." in glyph_name):
                gn = glyph_name.split(".")[0]
                try:
                    u = self.cmap[gn]
                except Exception:
                    pass
        if type(u) is set:
            u = next(iter(u))
        return u

    def get_unicode_category(self, glyph_name):
        u = self.get_unicode(glyph_name, extended=True)
        c = "C"
        if u != 65535:
            try:
                c = unicodedata.category(chr(u))
            except Exception:
                pass
        return c

    def extreme_points(self, glyph_name):
        """ Helper for setting up an initial cvt.

        """
        g = ygGlyph(ygPreferences(), self, glyph_name)
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
        self.main_window.set_window_title()

    def set_clean(self):
        self._clean = True
        self.main_window.set_window_title()

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

    def del_glyph(self, gname):
        try:
            self.glyphs.del_glyph(gname)
        except Exception:
            pass

    def get_glyph(self, gname):
        """ Get the source for a glyph's hints. If the glyph has no hints yet,
            return an empty hint program.

        """
        if not gname in self.glyphs:
            self.glyphs[gname] = {"y": {"points": []}, "x": {"points": []}}
        return(self.glyphs[gname])
        #try:
        #    return self.glyphs[gname]
        #except KeyError:
        #    return {"y": {"points": []}}

    def get_glyph_index(self, gname, short_index=False):
        if short_index:
            return self.glyph_index[gname]
        else:
            return self.name_to_index[gname]

    def get_glyph_name(self, char):
        try:
            return self.unicode_to_name[ord(char)]
        except Exception:
            return ".notdef"

    def string_to_name_list(self, s):
        """ Get the names of the glyphs needed to make string s
            from the current font.
        """
        result = []
        for c in s:
            gn = self.get_glyph_name(c)
            if not gn in result:
                result.append(gn)
        return result


    def save_glyph_source(self, source, axis, gname):
        """ Save a y or x block to the in-memory source.
        """
        if not gname in self.glyphs:
            self.glyphs[gname] = {}
        self.glyphs[gname][axis] = source



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

    def get_cvs(self, glyph, filters):
        """ Get a list of control values filtered to match a particular
            environment.

            Parameters:
            glyph (ygGlyph): the target glyph

            filters: a dict with any of these key/value pairs: type, axis,
            cat, suffix (others would be ignored)

            Returns:
            a list of ygcvt objects.

        """
        result = {}
        # Get the complete list of control values
        keys = self.data.keys()
        for key in keys:
            entry = self.data[key]
            include_this = True
            if glyph != None and type(entry) is dict:
                if "type" in entry:
                    if entry["type"] != filters["type"]:
                        include_this = False
                if include_this and ("axis" in entry):
                    if entry["axis"] != filters["axis"]:
                        include_this = False
                if include_this and ("cat" in entry):
                    if not glyph.match_category(entry["cat"], filters["cat"]):
                        include_this = False
                if include_this and ("suffix" in entry):
                    if not entry["suffix"] in filters["suffix"]:
                        include_this = False
            if include_this:
                result[key] = entry["val"]
        return result

    def get_list(self, glyph, **filters):
        """ Run get_cvs, then format for presentation in a menu
        """
        result = []
        cvt_matches = self.get_cvs(glyph, filters)
        for key in cvt_matches:
            result.append(key)
        return result

    def _closest(self, lst, v):
        """ Helper for get_closest_cv_action
        """
        return lst[min(range(len(lst)), key = lambda i: abs(lst[i] - v))]

    def _get_val_from_hint(self, hint, axis):
        """ Helper for get_closest_cv_action
        """
        tgt = hint.yg_glyph.resolve_point_identifier(hint.target())
        ref = hint.ref()
        if ref != None:
            ref = hint.yg_glyph.resolve_point_identifier(ref)
            if type(ref) is not ygPoint:
                return None
        if type(tgt) is not ygPoint:
            return None
        if ref == None:
            if axis == "y":
                return tgt.font_y
            else:
                return tgt.font_x
        else:
            if axis == "y":
                return abs(tgt.font_y - ref.font_y)
            else:
                return abs(tgt.font_x - ref.font_x)

    def get_closest_cv_name(self, cvlist, hint):
        """ cvlist is a list of cv names. hint is a ygModel.ygHint object.
        """
        axis = hint.yg_glyph.current_axis()
        val = self._get_val_from_hint(hint, axis)
        vlist = []
        for c in cvlist:
            vv = self.get_cv(c)
            if type(vv) is dict:
                vlist.append(vv["val"])
            else:
                vlist.append(vv)
        cc = self._closest(vlist, val)
        return cvlist[vlist.index(cc)]

    def get_closest_cv_action(self, alst, hint):
        """ Return the QAction from alst with value closest
            to the one in the hint.

            alst is a list of QActions; hint is the hint we're operating on.
            The hint must be type 0 (anchor) or 3 (single-point target, can take cv).
            Hint type should have been checked before we got here.
        """
        alst.pop(0)
        alst.pop(0)
        axis = hint.yg_glyph.current_axis()
        val = self._get_val_from_hint(hint, axis)
        vlist = []
        for a in alst:
            vv = self.get_cv(a.text())
            if type(vv) is dict:
                vlist.append(vv["val"])
            else:
                vlist.append(vv)
        c = self._closest(vlist, val)
        return alst[vlist.index(c)]

    def get_cv(self, name):
        """ Retrieve a control value by name. This will usually be a dict
            rather than just a number.

        """
        if name in self.data:
            return self.data[name]
        return None

    def add_cv(self, name, props):
        self.data[name] = props



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
            if k != "code" and k != "stack-safe" and k != "primitive" and  not ("type" in self.data[k] and self.data[k]['type'] == "point"):
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
        self.preferred_name = None

    def preferred_label(self, normalized=False, name_allowed=True):
        if name_allowed:
            if self.preferred_name != None and len(self.preferred_name) > 0:
                return self.preferred_name
        if self.label_pref == "coord":
            if normalized:
                t = self.coord.replace("{","")
                t = t.replace("}","")
                t = t.replace(";", ",")
                return t
            else:
                return self.coord
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

    def __contains__(self, v):
        vv = self.point_dict.values()
        if type(v) is not ygPoint:
            return False
        for val in vv:
            if type(val) is ygPoint and val.id == v.id:
                return True
            if type(val) is ygSet and v in val:
                return True
            if type(val) is list and v in ygSet(val):
                return True
        return False



class ygSet:
    """ Xgridfit has a structure called a 'set'--just a simple list of points.
        This can be the target for a shift, align or interpolate instruction,
        and a two-member set can be reference for interpolate.

        Parameters:
        point_list (list): a list of ygPoint objects

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

    def __contains__(self, v):
        if type(v) is ygPoint:
            for p in self._point_list:
                if type(p) is ygPoint:
                    if p.id == v.id:
                        return True
        return False

    def overlaps(self, tester):
        result = []
        if type(tester) is not ygSet:
            return result
        pts = tester.point_list()
        for pt in pts:
            if pt in self:
                result.append(pt)
        return result


class ygGlyphProperties(ygSourceable):
    def __init__(self, glyph):
        super().__init__(glyph.yg_font, None)
        self.yg_glyph = glyph

    def add_property(self, k, v):
        self.yg_glyph.undo_stack.push(glyphAddPropertyCommand(self.yg_glyph, k, v))
        self.set_clean(False)

    def get_property(self, k):
        try:
            return self.yg_glyph.gsource["props"][k]
        except KeyError:
            return None

    def set_clean(self, c):
        if not c:
            self.yg_glyph.set_dirty()

    def source(self):
        if "props" in self.yg_glyph.gsource:
            return self.yg_glyph.gsource["props"]
        return {}

    def del_property(self, k):
        try:
            self.yg_glyph.undo_stack.push(glyphDeletePropertyCommand(self.yg_glyph, k))
            self.set_clean(False)
        #except KeyError as k:
        except Exception as e:
            # print(e)
            pass

    def save(self, c):
        self.yg_glyph.undo_stack.push(replaceGlyphPropsCommand(self.yg_glyph, c))
        self.set_clean(False)



class ygGlyphNames(ygSourceable):
    def __init__(self, glyph):
        self.yg_glyph = glyph
        super().__init__(glyph.yg_font, None)

    def add(self, pt, name):
        self.yg_glyph.undo_stack.push(addPointSetNameCommand(self.yg_glyph, pt, name))
        self.set_clean(False)

    def set_clean(self, b):
        if not b:
            self.yg_glyph.set_dirty()

    def has_name(self, n):
        if "names" in self.yg_glyph.gsource:
            return n in self.yg_glyph.gsource["names"]
        return False

    def source(self):
        if "names" in self.yg_glyph.gsource:
            return self.yg_glyph.gsource["names"]
        return {}

    def get(self, n):
        if self.has_name(n):
            return self.yg_glyph.gsource["names"][n]

    def save(self, c):
        self.yg_glyph.undo_stack.push(replacePointNamesCommand(self.yg_glyph, c))
        self.set_clean(False)

#
# Undo / Redo
#
# One helper class(glyphSaver) and several subclasses of QUndoCommand. Each glyph has its
# own QUndoStack, and these are coordinated at the app level by one QUndoGroup.
#
# The regular sequence is: (1) The constructor takes a snapshot of the current state
# of the glyph program (via glyphSaver); (2) An editing action is performed (in .redo(),
# which Qt calls after the constructor is run--so the command's actual work is done there)
# and another snapshot is taken of the result; (3) on undo, the snapshot taken in (1)
# is swapped in for the current state of the glyph program; (4) on redo, the snapshot
# taken in (2) is swapped in.
#
# As a typical glyph program takes up 200-400 bytes in memory, this isn't as wasteful of
# memory as it sounds; and it definitely keeps things simple. There are some variations on
# the sequence.
#
# To do (some may be grouped):
#
# Indices to Coords
# Coords to Indices
#
# At font rather than glyph level (do these after glyph-level undos):
#
# Edit cvt
# Edit prep
# Edit fpgm
# Edit cvar
# Edit macros
# 
#

class glyphSaver:
    def __init__(self, g):
        self.yg_glyph = g
        self.gsource = copy.deepcopy(self.yg_glyph.gsource)

    def restore(self):
        # This looks awkward, but we need to make self.yg_glyph.gsource equal to
        # self.gsource without changing the id of the first. Is there a better way?
        self.yg_glyph.gsource.clear()
        for k in self.gsource.keys():
            self.yg_glyph.gsource[k] = self.gsource[k]



class glyphEditCommand(QUndoCommand):
    """ The superclass for most glyph editing commands.

        params:
        glyph (ygGlyph): The glyph being edited. Note that redo *must* be
        reimplemented, but undo ordinarily doesn't have to be.
    
    """
    def __init__(self, glyph):
        super().__init__()
        self.yg_glyph = glyph
        self.undo_state = glyphSaver(self.yg_glyph)
        self.redo_state = None

    def send_signal(self):
        self.yg_glyph.sig_hints_changed.emit(self.yg_glyph.hints())
        self.yg_glyph.send_yaml_to_editor()

    def redo(self):
        pass

    def undo(self):
        self.undo_state.restore()
        self.send_signal()



class changePointNumbersCommand(glyphEditCommand):
    def __init__(self, glyph, to_coords):
        super().__init__(glyph)
        self.to_coords = to_coords
        if self.to_coords:
            self.setText("Indices to Coords")
        else:
            self.setText("Coords to Indices")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph.sub_coords(self.yg_glyph.current_block(), to_coords=self.to_coords)
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class updateSourceCommand(glyphEditCommand):
    def __init__(self, glyph, s):
        super().__init__(glyph)
        self.s = s
        self.valid = True
        self.setText("Compile Glyph Program")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                self.yg_glyph.gsource[self.yg_glyph.current_axis()]["points"].clear()
                for ss in self.s:
                    self.yg_glyph.gsource[self.yg_glyph.current_axis()]["points"].append(ss)
                self.yg_glyph._yaml_add_parents(self.yg_glyph.current_block())
                self.yg_glyph._yaml_supply_refs(self.yg_glyph.current_block())
            except Exception as e:
                print(e)
                self.undo_state.restore()
                self.valid = False
        self.redo_state = glyphSaver(self.yg_glyph)
        if self.valid:
            self.send_signal()



class replacePointNamesCommand(glyphEditCommand):
    def __init__(self, glyph, name_dict):
        super().__init__(glyph)
        self.name_dict = name_dict
        self.setText("Edit Point Names")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if self.name_dict != None and len(self.name_dict) > 0:
                if not "names" in self.yg_glyph.gsource:
                    self.yg_glyph.gsource["names"] = {}
                else:
                    self.yg_glyph.gsource["names"].clear()
                for k in self.name_dict.keys():
                    self.yg_glyph.gsource["names"][k] = self.name_dict[k]
            else:
                if "names" in self.yg_glyph.gsource:
                    del self.yg_glyph.gsource["names"]
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class replaceGlyphPropsCommand(glyphEditCommand):
    def __init__(self, glyph, prop_dict):
        super().__init__(glyph)
        self.prop_dict = prop_dict
        self.setText("Edit Glyph Properties")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if self.prop_dict != None and len(self.prop_dict) > 0:
                if not "props" in self.yg_glyph.gsource:
                    self.yg_glyph.gsource["props"] = {}
                else:
                    self.yg_glyph.gsource["props"].clear()
                for k in self.prop_dict.keys():
                    self.yg_glyph.gsource["props"][k] = self.prop_dict[k]
            else:
                if "props" in self.yg_glyph.gsource:
                    del self.yg_glyph.gsource["props"]
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class addPointSetNameCommand(glyphEditCommand):
    def __init__(self, glyph, pt, name):
        super().__init__(glyph)
        self.pt = pt
        self.name = name
        self.setText("Name Point(s)")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if not "names" in self.yg_glyph.gsource:
                self.yg_glyph.gsource["names"] = {}
            if type(self.pt) is not list:
                self.yg_glyph.gsource["names"][self.name] = self.yg_glyph.resolve_point_identifier(self.pt).preferred_label(name_allowed=False)
            else:
                if len(self.pt) == 1:
                    self.yg_glyph.gsource["names"][self.name] = self.pt[0].preferred_label(name_allowed=False)
                elif len(self.pt) > 1:
                    pt_list = []
                    for p in self.pt:
                        pt_list.append(p.preferred_label(name_allowed=False))
                    self.yg_glyph.gsource["names"][self.name] = pt_list
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class setMacFuncOtherArgsCommand(glyphEditCommand):
    def __init__(self, glyph, hint, new_params):
        super().__init__(glyph)
        self.hint = hint
        self.new_params = new_params
        self.setText("Edit parameters")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._source[self.hint.hint_type()] = self.new_params
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class swapMacFuncPointsCommand(glyphEditCommand):
    def __init__(self, glyph, hint, new_name, old_name):
        super().__init__(glyph)
        self.hint = hint
        self.new_name = new_name
        self.old_name = old_name
        self.setText("Swap Mac/Func points")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if type(self.hint._source["ptid"]) is dict:
                try:
                    self.hint._source["ptid"][self.new_name], self.hint._source["ptid"][self.old_name] = \
                    self.hint._source["ptid"][self.old_name], self.hint._source["ptid"][self.new_name]
                except Exception as e:
                    self.hint._source["ptid"][self.new_name] = self.hint._source["ptid"][self.old_name]
                    del self.hint._source["ptid"][self.old_name]
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()
                



class cleanupGlyphCommand(glyphEditCommand):
    def __init__(self, glyph):
        super().__init__(glyph)

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph._rebuild_current_block()
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class changeDistanceTypeCommand(glyphEditCommand):
    def __init__(self, glyph, hint, new_color):
        super().__init__(glyph)
        self.hint = hint
        self.new_color = new_color

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._source["rel"] = self.new_color
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class toggleMinDistCommand(glyphEditCommand):
    def __init__(self, glyph, hint):
        super().__init__(glyph)
        self.hint = hint
        self.setText("Toggle Minimum Distance")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            current_min_dist = not self.hint.min_dist()
            if current_min_dist == self.hint.min_dist_is_default():
                if "min" in self.hint._source:
                    del self.hint._source["min"]
            else:
                self.hint._source["min"] = current_min_dist
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class changeCVCommand(glyphEditCommand):
    def __init__(self, glyph, hint, new_cv):
        super().__init__(glyph)
        self.hint = hint
        self.new_cv = new_cv
        self.setText("Set Control Value")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            cvtype = self.hint.required_cv_type()
            if cvtype:
                if self.new_cv == "None":
                    if cvtype in self.hint._source:
                        del self.hint._source[cvtype]
                else:
                    self.hint._source[cvtype] = self.new_cv
                self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class toggleRoundingCommand(glyphEditCommand):
    def __init__(self, glyph, hint):
        super().__init__(glyph)
        self.hint = hint
        self.setText("Toggle Rounding")

    def redo(self):
        current_round = not self.hint.rounded()
        if self.redo_state:
            self.redo_state.restore()
        else:
            if current_round == self.hint.round_is_default():
                if "round" in self.hint._source:
                    del self.hint._source["round"]
            else:
                self.hint._source["round"] = current_round
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class makeSetCommand(glyphEditCommand):
    def __init__(self, glyph, hint, pt_list, touched_point, callback):
        super().__init__(glyph)
        self.hint = hint
        self.pt_list = pt_list
        self.touched_point = touched_point
        self.callback = callback
        self.setText("Make Set")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            sorter = ygPointSorter(self.yg_glyph.current_axis())
            sorter.sort(self.pt_list)
            set = ygSet(self.pt_list)
            set._main_point = self.touched_point
            self.hint.set_target(set.id_list())
            self.callback()
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class addHintCommand(glyphEditCommand):
    def __init__(self, glyph, hint, conditional=False):
        super().__init__(glyph)
        self.hint = hint
        self.conditional = conditional
        self.setText("Add Hint")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph._add_hint(self.hint, self.yg_glyph.current_block())
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class deleteHintsCommand(glyphEditCommand):
    def __init__(self, glyph, l):
        super().__init__(glyph)
        self.hint_list = l
        self.setText("Delete Hints")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            for h in self.hint_list:
                s = h._source
                if "parent" in s:
                    try:
                        s["parent"]["points"].remove(s)
                    except Exception as e:
                        # print("error 1")
                        pass
                else:
                    try:
                        self.yg_glyph.current_block().remove(s)
                    except Exception as e:
                        # print("error 2")
                        pass
                if "points" in s:
                    for hh in s["points"]:
                        try:
                            if not "rel" in hh or hint_type_nums[hh["rel"]] == 4:
                                self.add_hint(ygHint(self, hh))
                        except Exception as e:
                            # print("error 3")
                            pass
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class reverseHintCommand(glyphEditCommand):
    def __init__(self, glyph, hint):
        super().__init__(glyph)
        self.hint = hint
        self.setText("Reverse Hint")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._source["ptid"], self.hint._source["ref"] = self.hint._source["ref"], self.hint._source["ptid"]
            self.yg_glyph._rebuild_current_block()
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()



class switchAxisCommand(QUndoCommand):
    def __init__(self, g, prefs, new_axis):
        super().__init__()
        self.yg_glyph = g
        self.original_axis = self.yg_glyph.current_axis()
        self.new_axis = new_axis
        self.top_window = prefs.top_window()
        self.setText("Change Axis")

    def redo(self):
        if self.yg_glyph.current_axis() == self.new_axis:
            return
        self.top_window.current_axis = self.yg_glyph._current_axis = self.new_axis
        self.yg_glyph._hints_changed(self.yg_glyph.hints(), dirty=False)
        self.yg_glyph.send_yaml_to_editor()
        self.top_window.set_window_title()
        self.top_window.check_axis_button()

    def undo(self):
        self.top_window.current_axis = self.yg_glyph._current_axis = self.original_axis
        self.yg_glyph.sig_hints_changed.emit(self.yg_glyph.hints())
        self.yg_glyph.send_yaml_to_editor()
        self.top_window.set_window_title()
        self.top_window.check_axis_button()



class glyphAddPropertyCommand(QUndoCommand):
    """ redo() has got to be the action itself. It will get excecuted when the
        constructor is called. So use the construction of this class to
        execute the command initially.

        undo() can be simpler: it can simply restore a saved state of the whole
        block.

        Constructor needs to save everything needed to execute the command,
        keeping its own separate copy of anything mutable (e.g. a list of
        selected objects).
    """

    def __init__(self, yg_glyph, prop_name, prop_value):
        super().__init__()
        self.yg_glyph = yg_glyph
        self.props = None
        if "props" in self.yg_glyph.gsource:
            self.props = copy.deepcopy(self.yg_glyph.gsource["props"])
        self.prop_name = prop_name
        self.prop_value = prop_value
        self.setText("Add Glyph Property")

    @pyqtSlot()
    def undo(self):
        if "props" in self.yg_glyph.gsource:
            if self.props:
                self.yg_glyph.gsource["props"] = self.props
            else:
                del self.yg_glyph.gsource["props"]
        self.yg_glyph._hints_changed(self.yg_glyph.hints())

    @pyqtSlot()
    def redo(self):
        if not "props" in self.yg_glyph.gsource:
            self.yg_glyph.gsource["props"] = {}
        self.yg_glyph.gsource["props"][self.prop_name] = self.prop_value
        self.yg_glyph._hints_changed(self.yg_glyph.hints())



class glyphDeletePropertyCommand(QUndoCommand):
    def __init__(self, yg_glyph, prop_name):
        super().__init__()
        self.yg_glyph = yg_glyph
        # Make a backup copy of the "props" block. It should never be
        # empty or absent, but we check just to make sure.
        self.props = None
        if "props" in self.yg_glyph.gsource:
            self.props = copy.deepcopy(self.yg_glyph.gsource["props"])
        self.prop_name = prop_name
        self.setText("Delete Glyph Property")

    @pyqtSlot()
    def undo(self):
        # Undo action is just to replace the current props block
        # with the former one.
        if self.props != None:
            if "props" in self.yg_glyph.gsource:
                self.yg_glyph.gsource["props"] = self.props
        else:
            if "props" in self.yg_glyph.gsource:
                del self.yg_glyph.gsource["props"]
        self.yg_glyph._hints_changed(self.yg_glyph.hints())

    @pyqtSlot()
    def redo(self):
        try:
            del self.yg_glyph.gsource["props"][self.prop_name]
            if len(self.yg_glyph.gsource["props"]) == 0:
                del self.yg_glyph.gsource["props"]
            self.yg_glyph._hints_changed(self.yg_glyph.hints())
        except Exception:
            pass



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
        top_window = self.preferences.top_window()
        if top_window != None:
            self.undo_stack = QUndoStack()
            self.preferences.top_window().add_undo_stack(self.undo_stack)
            self.undo_stack.setActive(True)
        self.yaml_editor = None
        self.yg_font = yg_font
        self.gsource = yg_font.get_glyph(gname)
        self.gname = gname
        self.names = ygGlyphNames(self)
        self.props = ygGlyphProperties(self)

        # Initialize:

        if not "y" in self.gsource:
            self.gsource["y"] = {"points": []}
        if not "x" in self.gsource:
            self.gsource["x"] = {"points": []}

        self.set_clean()

        # Work with the glyph from the fontTools representation of the font.

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

        # Decide the initial axis.
        if self.preferences and self.preferences.top_window() != None:
            self._current_axis = self.preferences.top_window().current_axis
        else:
            self._current_axis = "y"

        # Fix up the source to make it more usable.
        self._yaml_add_parents(self.current_block())
        self._yaml_supply_refs(self.current_block())

        # This is the QGraphicsScene wrapper for this glyph object. But
        # do we need a reference here in the __init__? It's only used once,
        # in setting up a signal, and there are other ways to do that.
        self.glyph_viewer = None

        self.sig_hints_changed.connect(self.hints_changed)
        if self.preferences.top_window() != None:
            self.set_auto_preview_connection()

    #
    # Ordering and structuring YAML source
    #

    def restore_gsource(self):
        """ Run when returning to a glyph.
        """
        if not "y" in self.gsource:
            self.gsource["y"] = {"points": []}
        if not "x" in self.gsource:
            self.gsource["x"] = {"points": []}
        self._yaml_add_parents(self.current_block())
        self._yaml_supply_refs(self.current_block())

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
        """ Helper for rebuild_current_block
        """
        block = []
        total_to_place = len(hl)
        placed = {}
        for h in hl:
            h["uuid"] = uuid.uuid1()
        while True:
            last_placed_len = len(placed)
            for h in hl:
                if not h["uuid"] in placed:
                    r = self._add_hint(h, block, conditional=True)
                    if r:
                        placed[h["uuid"]] = h
            if len(placed) >= total_to_place or last_placed_len == len(placed):
                break
        # If there are still unplaced hints after the while loop, append them
        # to the top level of the tree.
        if len(placed) < total_to_place:
            for h in hl:
                if not h["uuid"] in placed:
                    placed[h["uuid"]] = h
                    block.append(h)
        for h in hl:
            del h["uuid"]
        return block

    def _rebuild_current_block(self):
        """ Tears down the current source block and rebuilds it with proper
            regard for dependency and order. When this is reliable enough, it
            will be called every time the source is updated.

        """
        flattened_tree = self._flatten_yaml_tree(copy.deepcopy(self.current_block()))
        for f in flattened_tree:
            if "points" in f:
                del f["points"]
        new_tree = ygHintSorter(self.place_all(flattened_tree)).sort()
        self.gsource[self.current_axis()]["points"] = new_tree
        #if self.current_axis() == "y":
        #    self.y_block = new_tree
        #else:
        #    self.x_block = new_tree
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    def rebuild_current_block(self):
        self.undo_stack.push(cleanupGlyphCommand(self))

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
        #if self._current_axis == "y":
        #    self.y_block = node
        #else:
        #    self.x_block = node

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
            #if self._current_axis == "y":
            #    self.y_block = node
            #else:
            #    self.x_block = node

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

    def get_category(self, long_name=False):
        cat = self.props.get_property("category")
        if cat == None:
            cat = self.yg_font.get_unicode_category(self.gname)
        if long_name:
            return unicode_cat_names[cat]
        return cat

    def current_axis(self):
        return self._current_axis

    def current_block(self):
        if self._current_axis == "y":
            # return self.y_block
            return self.gsource["y"]["points"]
        else:
            # return self.x_block
            return self.gsource["x"]["points"]

    def hints(self):
        """ Get a list of hints for the current axis, wrapped in ygHint
            objects.

        """
        return self._yaml_mk_hint_list(self.current_block())

    def points(self):
        return self.point_list

    def indices_to_coords(self):
        """ Change coordinates in current block to point indices.

        """
        self.undo_stack.push(changePointNumbersCommand(self, True))
        #self.sub_coords(self.current_block())
        #self._hints_changed(self.hints(), dirty=True)
        #self.send_yaml_to_editor()

    def coords_to_indices(self):
        """ Change point indices in current block to coordinates.

        """
        self.undo_stack.push(changePointNumbersCommand(self, False))
        #self.sub_coords(self.current_block(), to_coords=False)
        #self._hints_changed(self.hints(), dirty=True)
        #self.send_yaml_to_editor()

    def sub_coords(self, block, to_coords=True):
        """ Helper for indices_to_coords and coords_to_indices
        """
        for ppt in block:
            ppt["ptid"] = self._sub_coords(ppt["ptid"], to_coords)
            if "ref" in ppt:
                ppt["ref"] = self._sub_coords(ppt["ref"], to_coords)
            if "points" in ppt:
                self.sub_coords(ppt["points"], to_coords=to_coords)

    def _sub_coords(self, block, to_coords):
        """ Helper for indices_to_coords and coords_to_indices
        """
        if type(block) is dict:
            new_dict = {}
            for kk, v in block.items():
                if type(v) is list:
                    new_dict[kk] = self._sub_coords(v, to_coords)
                else:
                    if to_coords:
                        new_dict[kk] = self.resolve_point_identifier(v).coord
                    else:
                        new_dict[kk] = self.resolve_point_identifier(v).index
            return new_dict
        elif type(block) is list:
            new_list = []
            for pp in block:
                if to_coords:
                    new_list.append(self.resolve_point_identifier(pp).coord)
                else:
                    new_list.append(self.resolve_point_identifier(pp).index)
            return new_list
        else:
            if to_coords:
                return self.resolve_point_identifier(block).coord
            else:
                return self.resolve_point_identifier(block).index

    def match_category(self, cat1, cat2):
        cat_a = cat1
        if cat2 == None:
            cat_b = self.get_category()
        else:
            cat_b = cat2
        if len(cat_a) == 1:
            cat_b = cat_b[:1]
        elif len(cat_b) == 1:
            cat_a = cat_a[:1]
        return cat_a == cat_b

    def get_suffixes(self):
        """ Will return an empty list if no suffixes
        """
        s = self.gname.split(".")
        return s[1:]

    def search_source(self, block, pt, ptype):
        """ Search the yaml source for a point.

            Parameters:
            block (list): At the top level, should be self.current_block().

            pt (ygPoint, ygSet, ygParams, int, or str): The point(s) we're
            searching for. If more than one point (ygSet, ygParams), any
            match at all is a positive result.

            ptype (str): "ptid" to search for target points, "ref" to search
            for ref points.

            Returns:
            A list of matching hint/point blocks from the source. These can
            be wrapped in ygHint objects for easy manipulation.

        """

        # Convert everything to a ygSet and test for overlap between two
        # ygSets.

        def _to_ygSet(o):
            """ 
            """
            if type(o) is ygSet:
                return o
            if type(o) is ygPoint:
                return ygSet([o])
            if type(o) is list:
                return ygSet([self.resolve_point_identifier(i) for i in o])
            if type(o) is ygParams:
                tmp_list = o.point_dict.values()
                new_list = []
                for t in tmp_list:
                    if type(t) is list:
                        new_list.extend(t)
                    else:
                        new_list.append(t)
                return ygSet([self.resolve_point_identifier(i) for i in new_list])
            t = self.resolve_point_identifier(o)
            return ygSet([t])

        result = []
        # pt is either the point we're searching for or a ygSet, for which we
        # count the search as positive if we get a match for just one element.
        # If we're starting with a ygPoint, wrap it in a ygSet.
        search_set = _to_ygSet(pt)
        for ppt in block:
            # ppt is what we want to return if we've made a find.
            tester = None
            if ptype in ppt:
                tester = _to_ygSet(ppt[ptype])
                if tester:
                    if len(tester.overlaps(search_set)) > 0:
                        result.append(ppt)
            if "points" in ppt and len(ppt["points"]) > 0:
                result.extend(self.search_source(ppt["points"], search_set, ptype))
        return result

    def glyph_name(self):
        return self.gname

    def xoffset(self):
        xo = self.props.get_property("xoffset")
        if xo != None:
            return xo
        return 0

    def yoffset(self):
        yo = self.props.get_property("yoffset")
        if yo != None:
            return yo
        return 0

    def _yaml_hint_type(self, n):
        """ Helper for _yaml_supply_refs
        """
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
        lpref = "index"
        top_window = self.preferences.top_window()
        if top_window != None and top_window.points_as_coords:
            lpref = "coord"
        for point_index, p in enumerate(zip(gl[0], gl[2])):
            is_on_curve = p[1] & 0x01 == 0x01
            pt = ygPoint(None,
                         point_index,
                         p[0][0],
                         p[0][1],
                         self.xoffset(),
                         self.yoffset(),
                         is_on_curve,
                         label_pref=lpref)
            pt_list.append(pt)
        return(pt_list)

    #
    # Navigation
    #

    def switch_to_axis(self, new_axis):
        if self.current_axis() == "y":
            new_axis = "x"
        else:
            new_axis = "y"
        self.undo_stack.push(switchAxisCommand(self, self.preferences, new_axis))

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
        new_cmd = updateSourceCommand(self, s)
        self.undo_stack.push(new_cmd)
        if not new_cmd.valid:
            new_cmd.setObsolete(True)
            self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])

    def cleanup_glyph(self):
        """ Call before saving YAML file.
        """
        have_y = True
        have_x = True
        if len(self.gsource["y"]["points"]) == 0:
            have_y = False
        if len(self.gsource["x"]["points"]) == 0:
            have_x = False
        if have_y:
            self.yaml_strip_extraneous_nodes(self.gsource["y"]["points"])
        else:
            del self.gsource["y"]
        if have_x:
            self.yaml_strip_extraneous_nodes(self.gsource["x"]["points"])
        else:
            del self.gsource["x"]
        if not have_y and not have_x:
            self.yg_font.del_glyph(self.gname)

    #
    # Editing
    #

    def set_category(self, c):
        rev_cat = {v: k for k, v in unicode_cat_names.items()}
        # Called function will use QUndoCommand.
        self.props.add_property("category", rev_cat[c])

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
                    if not h in block:
                        block.append(h)
        return True

    def add_hint(self, h):
        self.undo_stack.push(addHintCommand(self, h))

    def delete_hints(self, l):
        """ l: a list of ygHint objects
        """
        self.undo_stack.push(deleteHintsCommand(self, l))

    def set_dirty(self):
        self._clean = False
        self.yg_font.set_dirty()

    def make_set(self, hint, pt_list, touched_point, callback):
        self.undo_stack.push(makeSetCommand(self, hint, pt_list, touched_point, callback))

    def set_clean(self):
        self._clean = True

    def clean(self):
        return self._clean

    def make_named_points(self, pts, name):
        self.names.add(pts, name)


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
        elif self.names.has_name(ptid):
            result = self.names.get(ptid)
            if self._is_pt_obj(result):
                return result
        if result == None or depth > 20:
            m =  "Failed to resolve point identifier "
            m += str(ptid)
            m += " in glyph "
            m += self.gname
            m += ". Substituting zero."
            self.preferences.top_window().show_error_message(["Error", "Error", m])
            return 0
        result = self.resolve_point_identifier(result, depth=depth+1)
        if self._is_pt_obj(result):
            return result

    #
    # Signals and slots
    #

    def set_auto_preview_connection(self):
        if self.preferences.top_window().auto_preview_update:
            self.sig_hints_changed.connect(self.preferences.top_window().preview_current_glyph)
        else:
            try:
                self.sig_hints_changed.disconnect(self.preferences.top_window().preview_current_glyph)
            except Exception as e:
                # print(e)
                pass

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
        """ Called by signal from ygHint. Sends a list of hints in response.

        """
        self.set_dirty()
        self.sig_hints_changed.emit(self.hints())
        self.send_yaml_to_editor()

    @pyqtSlot(object)
    def hints_changed(self, hint_list):
        self._hints_changed(hint_list)

    def _hints_changed(self, hint_list, dirty=True):
        # print("running _hints_changed")
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

    def glyph_list(self):
        return list(self.data.keys())

    def del_glyph(self, gname):
        if gname in self.data:
            del self.data[gname]



class Comparable(object):
    """ For ordering hints such that a reference point never points to an
        untouched point.
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
    """ Before sorting a list of hints, wrap the source (._source) for each
        one in this. Class ygHintSorter does the actual sorting.
    """
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
        self.placed = False

        if self.yg_glyph != None:
            self.hint_changed_signal.connect(self.yg_glyph.hint_changed)

    def source(self):
        return(self._source)

    def parent(self):
        if "parent" in self.source:
            return self._source["parent"]

    def children(self):
        if "points" in self._source:
            return self._source["points"]

    def target(self):
        """ May return a point identifier (index, name, coordinate-pair), a list,
            or a dict.

        """
        return self._source["ptid"]

    def target_list(self, index_only=False):
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
            if index_only:
                for i, r in enumerate(result):
                    result[i] = self.yg_glyph.resolve_point_identifier(r).index
            return result
        else:
            return [self.yg_glyph.resolve_point_identifier(t).index]

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
            self.yg_glyph.undo_stack.push(reverseHintCommand(self.yg_glyph, self))

    def swap_macfunc_points(self, new_name, old_name):
        self.yg_glyph.undo_stack.push(swapMacFuncPointsCommand(self.yg_glyph, self, new_name, old_name))

    def change_hint_color(self, new_color):
        self.yg_glyph.undo_stack.push(changeDistanceTypeCommand(self.yg_glyph, self, new_color))
        #self._source["rel"] = new_color
        #self.hint_changed_signal.emit(self)

    def rounded(self):
        if "round" in self._source:
            if self._source["round"] == False:
                return False
            return True
        else:
            return self.round_is_default()

    # def has_min_dist(self):
    #     return "min-dist" in self._source

    def min_dist(self):
        try:
            m = self._source["min"]
            return m
            # return self._source["min"]
        except Exception:
            return self.min_dist_is_default()

    def min_dist_is_default(self):
        return hint_type_nums[self.hint_type()] == 3

    def toggle_min_dist(self):
        self.yg_glyph.undo_stack.push(toggleMinDistCommand(self.yg_glyph, self))

    def toggle_rounding(self):
        """ Ignores rounding types.
        """
        self.yg_glyph.undo_stack.push(toggleRoundingCommand(self.yg_glyph, self))

    def round_is_default(self):
        return hint_type_nums[self.hint_type()] in [0, 3]

    def set_round(self, b, update=False):
        if b != self.round_is_default():
            self._source["round"] = b
        else:
            if "round" in self._source:
                del self._source["round"]
        if update:
            self.hint_changed_signal.emit(self)

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
        self.yg_glyph.undo_stack.push(changeCVCommand(self.yg_glyph, self, new_cv))

    def cut_in(self):
        return True

    def hint_has_changed(self, h):
        self.hint_changed_signal.emit(h)

    def add_hint(self, hint):
        """ Add a hint. This simply calls add_hint in the glyph

        """
        self.yg_glyph.add_hint(hint)
        # ygGlyph.add_hint will emit the hint changed signal.

    def delete_hints(self, hint_list):
        """ Delete a hint from the hint tree. Just calls a function in ygGlyph.

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

    def set_macfunc_other_args(self, d):
        """ d is a dictionary of params for this hint.
        """
        if len(d) > 1:
            self.yg_glyph.undo_stack.push(setMacFuncOtherArgsCommand(self.yg_glyph, self, d))

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
        touched points.

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
        depending on the current axis.

    """
    def __init__(self, axis):
        self.axis = axis

    def _ptcoords(self, p):
        if self.axis == "y":
            return p.font_x
        else:
            return p.font_y

    def sort(self, pt_list):
        pt_list.sort(key=self._ptcoords)
