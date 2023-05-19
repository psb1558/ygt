# import traceback
from typing import Any, TypeVar, Union, Optional, List, Callable, overload, Iterable
from PyQt6.QtCore import (
    Qt,
    QObject,
    QModelIndex,
    pyqtSignal,
    pyqtSlot,
    QAbstractTableModel,
)
from PyQt6.QtGui import QUndoCommand, QUndoStack, QAction
from fontTools import ttLib, ufoLib # type: ignore
import yaml
from yaml import Dumper
import os
import pathlib
import uuid
import random
import copy
import unicodedata
import abc
from tempfile import SpooledTemporaryFile
from .ygPreferences import ygPreferences
from .cvGuesser import instanceChecker
from .freetypeFont import freetypeFont
from .harfbuzzFont import harfbuzzFont

# from .ygSchema import error_message, set_error_message, is_cv_delta_valid
import defcon # type: ignore
from ufo2ft import compileTTF # type: ignore

hint_type_nums = {
    "anchor": 0,
    "align": 1,
    "shift": 1,
    "interpolate": 2,
    "stem": 3,
    "whitedist": 3,
    "blackdist": 3,
    "graydist": 3,
    "move": 3,
    "macro": 4,
    "function": 4,
}

unicode_categories = [
    "Lu",
    "Ll",
    "Lt",
    "LC",
    "Lm",
    "Lo",
    "L",
    "Mn",
    "Mc",
    "Me",
    "M",
    "Nd",
    "Nl",
    "No",
    "N",
    "Pc",
    "Pd",
    "Ps",
    "Pe",
    "Pi",
    "Pf",
    "Po",
    "P",
    "Sm",
    "Sc",
    "Sk",
    "So",
    "S",
    "Zs",
    "Zl",
    "Zp",
    "Z",
    "Cc",
    "Cf",
    "Cs",
    "Co",
    "Cn",
    "C",
]

unicode_cat_names = {
    "Lu": "Letter, uppercase",
    "Ll": "Letter, lowercase",
    "Lt": "Letter, titlecase",
    "LC": "Letter, cased",
    "Lm": "Letter, modifier",
    "Lo": "Letter, other",
    "L":  "Letter",
    "Mn": "Mark, nonspacing",
    "Mc": "Mark, spacing",
    "Me": "Mark, enclosing",
    "M":  "Mark",
    "Nd": "Number, decimal",
    "Nl": "Number, letter",
    "No": "Number, other",
    "N":  "Number",
    "Pc": "Punctuation, connector",
    "Pd": "Punctuation, dash",
    "Ps": "Punctuation, open",
    "Pe": "Punctuation, close",
    "Pi": "Punctuation, initial quote",
    "Pf": "Punctuation, final quote",
    "Po": "Punctuation, other",
    "P":  "Punctuation",
    "Sm": "Symbol, math",
    "Sc": "Symbol, currency",
    "Sk": "Symbol, modifier",
    "So": "Symbol, other",
    "S":  "Symbol",
    "Zs": "Separator, space",
    "Zl": "Separator, line",
    "Zp": "Separator, paragraph",
    "Z":  "Separator",
    "Cc": "Other, control",
    "Cf": "Other, format",
    "Cs": "Other, surrogate",
    "Co": "Other, private use",
    "Cn": "Other, not assigned",
    "C":  "Other",
}

INITIAL_CV_DELTA = {"size": 25, "distance": 0.0}

reverse_unicode_cat_names = {v: k for k, v in unicode_cat_names.items()}

# Error flags. These are set in the current ygGlyph when something has gone
# wrong in the processing of point data.

POINT_OUT_OF_RANGE = 1
POINT_UNIDENTIFIABLE = 2


def random_id(s):
    random.seed()
    i = str(random.randint(100000, 999999))
    return s + i


# Classes in this file:

#
# Font Objects:
#
# SourceFile: The yaml source read from and written to by this program.
# FontFiles: Input and output font files.
# ygFont(QObject): Keeps the fontTools representation of a font and
#                  provides an interface for the YAML code.
# ygCaller: superclass for ygFunction and ygMacro.
# ygFunction(ygCaller): A function call.
# ygMacro(ygCaller): A macro call.
# ygPoint: One point.
# ygParams: For functions and macros, holds their parameters.
# ygSet: A set of points, for SLOOP instructions like shift and interpolate.
#
#  Commands:
#
# glyphSaver: Utility for undo/redo system.
# fontInfoSaver: Utility for undo/redo system.
#
# fontInfoEditCommand(QUndoCommand): Superclass for editing font-level data.
# glyphEditCommand(QUndoCommand): superclass for most editing commands.
#
# saveEditBoxCommand(fontInfoEditCommand): Saves the contents of an editing dialog.
# setDefaultCommand(fontInfoEditCommand): Sets a default value.
# deleteDefaultCommand(fontInfoEditCommand): Delete a default key/value pair.
# roundingDefaultCommand(fontInfoEditCommand): Set all rounding defaults.
# editCVDeltaCommand(fontInfoEditCommand): change existing CV deltas.
# addCVDeltaCommand(fontInfoEditCommand): add a CV delta.
# deleteCVDeltaCommand(fontInfoEditCommand): Delete a CV delta key/value pair.
# addMasterCommand(fontInfoEditCommand): Add a master.
# deleteMasterCommand(fontInfoEditCommand): Delete a master.
# setMasterNameCommand(fontInfoEditCommand): Change a master's display name.
# setMasterAxisValueCommand(fontInfoEditCommand): Change value in master def.
# deleteMasterAxisCommand(fontInfoEditCommand): Delete a master axis.
# addCVCommand(fontInfoEditCommand): Add a control value.
# setCVPropertyCommand(fontInfoEditCommand): set a CV property.
# delCVPropertyCommand(fontInfoEditCommand): delete a CV property.
# deleteCVCommand(fontInfoEditCommand): Delete a CV.
# renameCVCommand(fontInfoEditCommand): Rename a CV.
# changePointNumbersCommand(glyphEditCommand): Glyph editing command.
# updateSourceCommand(glyphEditCommand): Glyph editing command.
# replacePointNamesCommand(glyphEditCommand): Glyph editing command.
# replaceGlyphPropsCommand(glyphEditCommand): Glyph editing command.
# addPointSetNameCommand(glyphEditCommand): Glyph editing command.
# setMacFuncOtherArgsCommand(glyphEditCommand): Glyph editing command.
# swapMacFuncPointsCommand(glyphEditCommand): Glyph editing command.
# cleanupGlyphCommand(glyphEditCommand): Glyph editing command.
# changeDistanceTypeCommand(glyphEditCommand): Glyph editing command.
# toggleMinDistCommand(glyphEditCommand): Glyph editing command.
# changeCVCommand(glyphEditCommand): Glyph editing command.
# toggleRoundingCommand(glyphEditCommand): Glyph editing command.
# addHintCommand(glyphEditCommand): Glyph editing command.
# deleteHintsCommand(glyphEditCommand): Glyph editing command.
# reverseHintCommand(glyphEditCommand): Glyph editing command.
# addPointsCommand(glyphEditCommand): Add point(s) to shift, align or interp. hint
# deletePointsCommand(glyphEditCommand): Delete point(s) from shift, align or interp. hint
# switchAxisCommand(QUndoCommand): Glyph editing command.
# glyphAddPropertyCommand(QUndoCommand): Glyph editing command.
# glyphDeletePropertyCommand(QUndoCommand): Glyph editing command.
#
#  Font objects (resumed):
#
# glyphSourceTester: Tests equality of object IDs.
# ygGlyph(QObject): Keeps data for a glyph.
# ygGlyphs: Collection of this font's glyphs.
# Comparable: superclass for ygHintSource: for ordering hints.
# ygHintSource(Comparable): Wrapper for hint source: use when sorting.
# ygHint(QObject): One hint (including a function or macro call).
# ygSourceable: Superclass for various chunks of ygt source code.
# ygMasters: Collection of this font's masters
# ygprep(ygSourceable): Holds the cvt program/pre-program.
# ygDefaults(ygSourceable): Keeps defaults for this font's hints.
# ygCVDeltas(QAbstractTableModel): Collection of deltas for a CV.
# ygcvt(ygSourceable): Keeps the control values for this font.
# ygFunctions(ygSourceable): Holds the functions for this font.
# ygcvar(ygSourceable): Keeps the cvar table (deprecated).
# ygMacros(ygSourceable): Holds the macros for this font.
# ygGlyphProperties: Keeps miscellaneous properties for a glyph.
# ygGlyphNames: Keeps named points and sets.
# ygHintSorter: Sorts hints into their proper order.
# ygPointSorter: Utility for sorting points on the x or y axis.


class SourceFile:
    """The yaml source read from and written to by this program.

    To do: Source file may be read from and written to the data
    directory of a UFO. As there can be only one instruction
    file for a font, the filename should always be the same so
    that you only need the pathname of the UFO to locate it.
    """

    def __init__(self, yaml_source: Union[dict, str], yaml_filename: str = "") -> None:
        """The constructor reads the yaml source into the internal structure
        y_doc. If yaml_source is a dict, it is the skeleton yaml source
        generated for a new program. Otherwise, yaml_source will be a
        filename.

        yaml_source can be either a dict (containing newly initialized ygt code) or
        the name of either a .yaml file or a ufo.
        """
        # Determine the filename
        if type(yaml_source) is str:
            self.filename = yaml_source
        elif len(yaml_filename) > 0:
            self.filename = yaml_filename
        else:
            self.filename = "NewFile.yaml"

        # Determine the type of file: yaml or ufo (with yaml inside)
        suff = pathlib.Path(self.filename).suffix
        if suff == ".yaml":
            self.source_type = "yaml"
        elif suff == ".ufo":
            self.source_type = "ufo"
        else:
            # This shouldn't happen.
            raise Exception("Bad filename " + str(self.filename))

        # Read the yaml source. Either the skeleton created earlier (but shouldn't
        # it be here?), a yaml file, or a yaml file in a ufo.
        if type(yaml_source) is dict:
            self.y_doc = copy.deepcopy(yaml_source)
        else:
            if self.source_type == "yaml":
                y_stream = open(self.filename, "r")
                self.y_doc = yaml.safe_load(y_stream)
                y_stream.close()
            else:
                ufo = ufoLib.UFOReader(self.filename)
                if ufo.formatVersionTuple[0] == 3:
                    doc = ufo.readData("org.ygthinting/source.yaml")
                    self.y_doc = yaml.safe_load(doc)

    @property
    def source(self) -> dict:
        return self.y_doc

    def save_source(self, top_window: Any = None) -> None:
        yy = yaml.dump(self.y_doc, sort_keys=False, width=float("inf"), Dumper=Dumper)
        if self.source_type == "yaml":
            f = open(self.filename, "w")
            f.write(yy)
            f.close()
        else:
            if os.path.exists(self.filename):
                f = ufoLib.UFOWriter(self.filename)
                f.writeData("org.ygthinter/source.yaml", yy.encode()) # type: ignore
                f.close()
            else:
                if top_window:
                    msg = "To save to a UFO, you must select an existing UFO."
                    top_window.show_error_message(["Error", "Error", msg])


class FontFiles:
    """Keeps references to the font to be read (ufo or ttf) and the one to be
    written.
    """

    def __init__(self, source: dict) -> None:
        """Source is an internal representation of a yaml file, from which
        the names of the input and output font files can be retrieved.
        """
        self.data = source["font"]

    @property
    def in_font(self) -> Optional[str]:
        try:
            return self.data["in"]
        except KeyError:
            return None

    @property
    def out_font(self) -> Optional[str]:
        try:
            return self.data["out"]
        except KeyError:
            return None


class ygFont(QObject):
    """Keeps all the font's data, including a fontTools representation of the
    font, the "source" structure built from the yaml file, and a structure
    for each section of the yaml file. All of the font data can be accessed
    through this class.

    Call this directly to open a font for the first time. After that,
    you only have to open the yaml file.
    """

    sig_cvt_changed = pyqtSignal()
    sig_error = pyqtSignal(object)

    def __init__(
        self, main_window: Any, source_file: Union[str, dict], ygt_filename: str = ""
    ) -> None:
        super().__init__()
        self.main_window = main_window

        #
        # Set up an undo stack
        #
        self.undo_stack = QUndoStack()
        self.main_window.add_undo_stack(self.undo_stack)

        #
        # Open the font
        #
        self.source_file = SourceFile(source_file, yaml_filename=ygt_filename)

        # Fix directory (change to directory where source file is located)
        d = None
        if isinstance(source_file, str) and source_file:
            d = os.path.dirname(source_file)
        elif ygt_filename:
            d = os.path.dirname(ygt_filename)
        if d and os.path.isdir(d) and d != os.getcwd():
            os.chdir(d)

        self.source = self.source_file.source
        self.font_files = FontFiles(self.source)
        fontfile = self.font_files.in_font
        if not fontfile:
            raise Exception("Need the name of an existing font")
            # Need to let user try again.
        split_fn = os.path.splitext(str(fontfile))
        extension = split_fn[1]
        ft_open_error = False
        # self.freetype_font = None
        # Here we get *two* copies of the font in memory: one in FontTools format,
        # the other FreeType.
        if extension == ".ttf":
            try:
                self.ft_font = ttLib.TTFont(fontfile)
                self.freetype_font = freetypeFont(fontfile)
                self.harfbuzz_font = harfbuzzFont(fontfile, self.freetype_font)
            except FileNotFoundError as ferr:
                ft_open_error = True
        elif extension == ".ufo":
            try:
                ufo = defcon.Font(fontfile)
                self.ft_font = compileTTF(ufo, useProductionNames=False, reverseDirection=False)
                tf = SpooledTemporaryFile(max_size=3000000, mode='b')
                self.ft_font.save(tf, 1)
                self.freetype_font = freetypeFont(tf, keep_open = True)
                self.harfbuzz_font = harfbuzzFont(tf, self.freetype_font)
                # tf.close()
            except Exception as e:
                print(e)
                ft_open_error = True
        if ft_open_error:
            raise Exception("Can't find font file " + str(fontfile))
            # Fix this! Need a dialog box and a chance to try again for a valid font.
            #
            # Do this: open a file dialog for locating the font file, and place this
            # in the SourceFile object. If user doesn't choose a font, then close
            # this window (send signal to top_window?). The application can continue
            # if other windows are open.

        # Making a deepcopy so we can always have a clean copy of the font to work with.
        self.preview_font = copy.deepcopy(self.ft_font)

        #
        # If it's a variable font, get instances and axes
        #
        try:
            self.instances = {}
            for inst in self.ft_font["fvar"].instances:
                nm = (
                    self.ft_font["name"]
                    .getName(inst.subfamilyNameID, 3, 1, 0x409)
                    .toUnicode()
                )
                self.instances[nm] = inst.coordinates
            self.axes = self.ft_font["fvar"].axes
            self.is_variable_font = True
        except Exception as e:
            self.is_variable_font = False
        if self.is_variable_font:
            self.masters = ygMasters(self, self.source)
        #
        # Set up access to YAML font data (if there is no cvt table yet, get some
        # values from the font).
        #
        self.glyphs = ygGlyphs(self.source).data
        self.defaults = ygDefaults(self, self.source)
        self.defaults._set_default({"init-graphics": False, "cleartype": True})
        if not "cvt" in self.source:
            self.source["cvt"] = {}
        if len(self.source["cvt"]) == 0:
            cvt = self.source["cvt"]
            cvt["baseline"] = {"val": 0, "type": "pos", "axis": "y"}
            try:
                p = self.extreme_points("H")[0]
                cvt["cap-height"] = {
                    "val": p[1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Lu",
                    "origin": {"glyph": "H", "ptnum": [p[0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("x")[0]
                cvt["xheight"] = {
                    "val": p[1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Ll",
                    "origin": {"glyph": "x", "ptnum": [p[0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("O")
                cvt["cap-height-overshoot"] = {
                    "val": p[0][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Lu",
                    "same-as": {"below": {"ppem": 40, "cv": "cap-height"}},
                    "origin": {"glyph": "O", "ptnum": [p[0][0]]},
                }
                cvt["cap-baseline-undershoot"] = {
                    "val": p[1][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Lu",
                    "same-as": {"below": {"ppem": 40, "cv": "baseline"}},
                    "origin": {"glyph": "O", "ptnum": [p[1][0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("o")
                cvt["xheight-overshoot"] = {
                    "val": p[0][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Ll",
                    "same-as": {"below": {"ppem": 40, "cv": "xheight"}},
                    "origin": {"glyph": "o", "ptnum": [p[0][0]]},
                }
                cvt["lc-baseline-undershoot"] = {
                    "val": p[1][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Ll",
                    "same-as": {"below": {"ppem": 40, "cv": "baseline"}},
                    "origin": {"glyph": "o", "ptnum": [p[1][0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("b")[0]
                cvt["lc-ascender"] = {
                    "val": p[1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Ll",
                    "origin": {"glyph": "b", "ptnum": [p[0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("p")[1]
                cvt["lc-descender"] = {
                    "val": p[1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Ll",
                    "origin": {"glyph": "p", "ptnum": [p[0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("eight")
                cvt["num-round-top"] = {
                    "val": p[0][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Nd",
                    "same-as": {"below": {"ppem": 40, "cv": "num-flat-top"}},
                    "origin": {"glyph": "eight", "ptnum": [p[0][0]]},
                }
                cvt["num-baseline-undershoot"] = {
                    "val": p[1][1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Nd",
                    "same-as": {"below": {"ppem": 40, "cv": "baseline"}},
                    "origin": {"glyph": "eight", "ptnum": [p[1][0]]},
                }
            except Exception:
                pass
            try:
                p = self.extreme_points("five")[0]
                cvt["num-flat-top"] = {
                    "val": p[1],
                    "type": "pos",
                    "axis": "y",
                    "cat": "Nd",
                    "origin": {"glyph": "five", "ptnum": [p[0]]},
                }
            except Exception:
                pass
        self.cvt = ygcvt(self.main_window, self, self.source)
        if self.is_variable_font and not self.defaults.get_default("cv_vars_generated"):
            instanceChecker(self.ft_font, self.cvt, self.masters).refresh()
            self.defaults._set_default({"cv_vars_generated": True})
        self.cvar = ygcvar(self, self.source)
        self.prep = ygprep(self, self.source)
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
        self.glyph_list = []
        self._clean = True
        glyph_names = self.ft_font.getGlyphNames()

        # dict of {glyph_name: unicode}.
        self.cmap = self.ft_font["cmap"].buildReversed()

        # This dict is for using a glyph name to look up a glyph's index.
        self.name_to_index = {}
        raw_order_list = self.ft_font.getGlyphOrder()
        for order_index, gn in enumerate(raw_order_list):
            self.name_to_index[gn] = order_index

        # Get a list of tuples containing unicodes and glyph names (still
        # omitting composites). Sort first by unicode, then by name. This
        # is our order for the font.
        for gn in glyph_names:
            g = self.ft_font["glyf"][gn]
            # Remove this test if we're going to display composites.
            # if not g.isComposite():
            if True:
                cc = g.getCoordinates(self.ft_font["glyf"])
                if len(cc) > 0:
                    self.glyph_list.append((self.get_unicode(gn), gn))
        self.glyph_list.sort(key=lambda x: x[1])
        self.glyph_list.sort(key=lambda x: x[0])

        self.unicode_to_name = {}
        for g in self.glyph_list:
            self.unicode_to_name[g[0]] = g[1]

        # Like name_to_index, but this one looks up the index in a slimmed-down,
        # non-composite-only list. This is for navigating in this program.
        self.glyph_index = {}
        for glyph_counter, g in enumerate(self.glyph_list):
            self.glyph_index[g[1]] = glyph_counter

        # Track whether signal is connected
        self.signal_connected = False

    def setup_error_signal(self, f):
        self.sig_error.connect(f)

    def send_error_message(self, d: dict):
        self.sig_error.emit(d)

    @pyqtSlot()
    def refresh_variant_cvs(self):
        if self.is_variable_font:
            instanceChecker(self.preview_font, self.cvt, self.masters).refresh()

    @property
    def default_instance(self) -> Optional[str]:
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

    @property
    def axis_tags(self) -> list:
        result = []
        for a in self.axes:
            result.append(a.axisTag)
        return result

    def get_unicode(self, glyph_name: str, extended: bool = False) -> int:
        u: Optional[Union[set, int]] = None
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
            return int(list(u)[0])
        elif type(u) is int:
            return u
        else:
            return 65535

    def get_unicode_category(self, glyph_name: str) -> str:
        u = self.get_unicode(glyph_name, extended=True)
        c = "C"
        if u != 65535:
            try:
                c = unicodedata.category(chr(u))
            except Exception:
                pass
        return c

    def extreme_points(self, glyph_name: str) -> tuple[tuple, tuple]:
        """Helper for setting up an initial cvt."""
        return ygGlyph(ygPreferences(), self, glyph_name).extreme_points_y()

    @property
    def family_name(self) -> str:
        return str(self.ft_font["name"].getName(1, 3, 1, 0x409))

    @property
    def style_name(self) -> str:
        return str(self.ft_font["name"].getName(2, 3, 1, 0x409))

    @property
    def full_name(self) -> str:
        return self.family_name + "-" + self.style_name

    def set_dirty(self) -> None:
        self._clean = False
        self.main_window.set_window_title()

    def set_clean(self) -> None:
        self._clean = True
        self.main_window.set_window_title()

    def clean(self) -> bool:
        return self._clean

    def cleanup_font(self, current_glyph_name):
        try:
            no_hints = []
            glist = self.source["glyphs"]
            k = glist.keys()
            for kk in k:
                if kk != current_glyph_name and not self.has_hints(kk):
                    no_hints.append(kk)
            for g in no_hints:
                del self.source["glyphs"][g]
        except Exception as e:
            self.send_error_message(
                {"msg": "Error in cleanup_font: " + str(e), "mode": "console"}
            )

    def is_composite(self, gname: str) -> bool:
        if not gname in self.name_to_index:
            return False
        return self.ft_font['glyf'][gname].isComposite()

    def has_hints(self, gname: str) -> bool:
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

    def del_glyph(self, gname: str) -> None:
        try:
            self.glyphs.del_glyph(gname)
        except Exception:
            pass

    def get_glyph(self, gname: str) -> "dict":
        """Get the source for a glyph's hints. If the glyph has no hints yet,
        return an empty hint program.

        """
        if not gname in self.glyphs:
            self.glyphs[gname] = {"y": {"points": []}, "x": {"points": []}}
        return self.glyphs[gname]

    def get_glyph_index(self, gname: str, short_index: bool = False) -> int:
        if short_index:
            return self.glyph_index[gname]
        else:
            return self.name_to_index[gname]

    def get_glyph_name(self, char: str) -> str:
        try:
            return self.unicode_to_name[ord(char)]
        except Exception:
            return ".notdef"
        
    def additional_component_names(self, glyph_list):
        """Get list of components for all the glyphs in glyph_list.
           Recurse if necessary. Don't worry about redundancies in list.
        """
        result = []
        for gn in glyph_list:
            cn = self.ft_font['glyf'][gn].getComponentNames(self.ft_font['glyf'])
            if len(cn):
                for ccn in cn:
                    result.append(ccn)
                    result.extend(self.additional_component_names([ccn]))
        return result

    def string_to_name_list(self, s: str) -> list:
        """Get the names of the glyphs needed to make string s
        from the current font.
        """
        result = []
        for c in s:
            gn = self.get_glyph_name(c)
            if not gn in result:
                result.append(gn)
        result.extend(self.additional_component_names(result))
        return list(set(result))

    def save_glyph_source(self, source: dict, axis: str, gname: str) -> None:
        """Save a y or x block to the in-memory source."""
        if not gname in self.glyphs:
            self.glyphs[gname] = {}
        self.glyphs[gname][axis] = source

    def setup_signal(self, func) -> None:
        self.sig_cvt_changed.connect(func)
        self.signal_connected = True


class ygCaller:
    """Superclass for function and macro calls."""

    def __init__(self, callable_type: str, name: str, font: ygFont) -> None:
        if callable_type == "function":
            callables = font.functions
        else:
            callables = font.macros
        self.data = callables[name]

    # Analyze the type of a param and improve this return type
    def get_param(self, name: str) -> Any:
        try:
            return self.data[name]
        except Exception:
            return None

    def number_of_point_params(self) -> int:
        keys = self.data.keys()
        param_count = 0
        for k in keys:
            if type(self.data[k]) is dict and "type" in self.data[k]:
                if self.data[k]["type"] == "point":
                    param_count += 1
        return param_count

    def point_params_range(self) -> range:
        """The max in this range is the total number of point params. The
        min is the number of required point params (those without val
        attributes)
        """
        max_count = self.number_of_point_params()
        min_count = 0
        keys = self.data.keys()
        for k in keys:
            if (
                type(self.data[k]) is dict
                and "type" in self.data[k]
                and not "val" in self.data[k]
            ):
                if self.data[k]["type"] == "point":
                    min_count += 1
        return range(min_count, max_count + 1)

    @property
    def point_list(self) -> list:
        """Get a list of points (identifiers, not objects) from the dict of
        this callable's parameters.

        """
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k]:
                    if self.data[k]["type"] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def required_point_list(self) -> list:
        """Get a list of points in this glyph's required parameters."""
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k] and not "val" in self.data[k]:
                    if self.data[k]["type"] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def optional_point_list(self) -> list:
        """Get a list of points in this glyph's optional parameters."""
        plist = []
        keys = self.data.keys()
        for k in keys:
            try:
                if "type" in self.data[k] and "val" in self.data[k]:
                    if self.data[k]["type"] == "point":
                        plist.append(k)
            except Exception:
                pass
        return plist

    def non_point_params(self) -> dict:
        """Get a list of params that do not refer to points. For this to work
        properly, the params in the function definition have got to be
        defined carefully, with correct "type" attributes. This will return
        an empty dict if there are no eligible params.

        """
        pdict = {}
        # These keys are for the list of params. Step through this and
        # select the non-point params.
        keys = self.data.keys()
        for k in keys:
            if (
                k != "code"
                and k != "stack-safe"
                and k != "primitive"
                and not ("type" in self.data[k] and self.data[k]["type"] == "point")
            ):
                pdict[k] = self.data[k]
        return pdict


class ygFunction(ygCaller):
    def __init__(self, name: str, font: ygFont) -> None:
        super().__init__("function", name, font)


class ygMacro(ygCaller):
    def __init__(self, name: str, font: ygFont) -> None:
        super().__init__("macro", name, font)


class ygPoint:
    def __init__(
        self,
        name: Union[str, None],
        index: int,
        x: int,
        y: int,
        _xoffset: int,
        _yoffset: int,
        on_curve: bool,
        label_pref: str = "index",
    ) -> None:
        self.id = uuid.uuid1()
        self.name = name
        self.index = index
        self.font_x = x
        self.font_y = y
        self.coord = (
            "{" + str(self.font_x - _xoffset) + ";" + str(self.font_y - _yoffset) + "}"
        )
        self.on_curve = on_curve
        self.end_of_contour = False
        self.label_pref = label_pref
        self.preferred_name = ""

    def preferred_label(
        self, normalized: bool = False, name_allowed: bool = True
    ) -> str | int:
        if name_allowed:
            if len(self.preferred_name) > 0:
                return self.preferred_name
        # Coordinate IDs only allowed for on-curve points.
        if self.label_pref == "coord" and self.on_curve:
            if normalized:
                t = self.coord.replace("{", "")
                t = t.replace("}", "")
                t = t.replace(";", ",")
                return t
            else:
                return self.coord
        try:
            return int(self.index)
        except TypeError:
            print("TypeError: " + str(self.index))
            return str(self.index)

    def set_preferred_name(self, n: str) -> None:
        self.preferred_name = n

    def __eq__(self, other) -> bool:
        try:
            return self.id == other.id
        except AttributeError:
            return False
        
    def __str__(self):
        return str(self.index)


class ygParams:
    """Parameters to be sent to a macro or function. There are two sets of
    these: one consisting of points, the other anything else (e.g. cvt
    indexes).

    """

    def __init__(
        self,
        hint_type: Optional[str],
        name: Optional[str],
        point_dict: dict,
        other_params: Optional[dict],
    ) -> None:
        self.hint_type = hint_type
        self.name = name
        self.point_dict = point_dict
        self.other_params = other_params

    @property
    def point_list(self) -> list:
        result = []
        k = self.point_dict.keys()
        for kk in k:
            result.append(self.point_dict[kk])
        return result

    def __contains__(self, v) -> bool:
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
    """Xgridfit has a structure called a 'set'--just a simple list of points.
    This can be the target for a shift, align or interpolate instruction,
    and a two-member set can be reference for interpolate.

    Parameters:
    point_list (list): a list of ygPoint objects

    """

    def __init__(self, point_list: list) -> None:
        self._point_list = point_list
        self.id = uuid.uuid1()
        # The main point is the one the arrow is connected to. It shouldn't be
        # needed now, but the editor uses it against the possibility that a set
        # will contain another set. See if this can be safely removed.
        self._main_point: Optional[ygPoint] = None

    @property
    def point_list(self) -> list:
        return self._point_list

    #def id_list(self) -> list:
    #    l = []
    #    for p in self._point_list:
    #        l.append(p.preferred_label())
    #    return l

    def main_point(self) -> ygPoint:
        """Our use of an on-screen box may have made this useless. See if we
        can get rid of it.

        """
        if self._main_point:
            return self._main_point
        else:
            return self._point_list[0]

    def point_at_index(self, index: int) -> ygPoint:
        """Instead of failing when index is out of range, return the last
        item in the list.
        """
        try:
            return self._point_list[index]
        except Exception:
            return self._point_list[-1]

    def __contains__(self, v) -> bool:
        if type(v) is ygPoint:
            for p in self._point_list:
                if type(p) is ygPoint:
                    if p.id == v.id:
                        return True
        return False

    def overlaps(self, tester: "ygSet") -> list:
        result: list = []
        if type(tester) is not ygSet:
            return result
        pts = tester.point_list
        for pt in pts:
            if pt in self:
                result.append(pt)
        return result
    
    def __str__(self):
        result = "["
        for count, p in enumerate(self._point_list):
            if count > 0:
                result += ", "
            result += str(p.index)
        result += "]"
        return result

#
# Undo / Redo
#
# Two helper classes (glyphSaver and fontInfoSaver) and several subclasses of QUndoCommand.
# Each glyph has its own QUndoStack, and these are coordinated at the app level by one
# QUndoGroup.
#
# The regular sequence is: (1) The constructor takes a snapshot of the current state
# of the code (via glyphSaver or fontInfoSaver); (2) An editing action is performed (in
# .redo, which Qt calls when a command is added to the stack--so the command's actual work
# is done there) and another snapshot is taken of the result; (3) on undo, the snapshot
# taken in (1) is swapped in for the current state of the glyph program; (4) on redo,
# the snapshot taken in (2) is swapped in.
#
# As a typical glyph program takes up 200-400 bytes in memory, this isn't as wasteful of
# memory as it sounds; and it definitely keeps things simple. There are some variations on
# the sequence.
#


class glyphSaver:
    """Helper for many glyph commands."""

    def __init__(self, g: "ygGlyph") -> None:
        self.yg_glyph = g
        self.gsource = copy.deepcopy(self.yg_glyph.gsource)

    def restore(self) -> None:
        # This looks awkward, but we need to make self.yg_glyph.gsource equal to
        # self.gsource without changing the id of the first. Is there a better way?
        self.yg_glyph.gsource.clear()
        for k in self.gsource.keys():
            self.yg_glyph.gsource[k] = self.gsource[k]


class fontInfoSaver:
    """Helper for all undos concerning font-level info."""

    def __init__(self, yg_font: ygFont) -> None:
        self.yg_font = yg_font
        self.msource = None
        if self.yg_font.is_variable_font:
            self.msource = copy.deepcopy(self.yg_font.source["masters"])
        self.csource = None
        if "cvt" in self.yg_font.source:
            self.csource = copy.deepcopy(self.yg_font.source["cvt"])
        self.dsource = None
        if "defaults" in self.yg_font.source:
            self.dsource = copy.deepcopy(self.yg_font.source["defaults"])
        self.psource = None
        if "prep" in self.yg_font.source:
            self.psource = copy.deepcopy(self.yg_font.source["prep"])
        self.mcsource = None
        if "macros" in self.yg_font.source:
            self.mcsource = copy.deepcopy(self.yg_font.source["macros"])
        self.fsource = None
        if "functions" in self.yg_font.source:
            self.fsource = copy.deepcopy(self.yg_font.source["functions"])

    def _install_dict(self, k, d):
        if d:
            if k in self.yg_font.source:
                self.yg_font.source[k].clear()
            else:
                self.yg_font.source[k] = {}
            if len(d) > 0:
                for kk in d.keys():
                    self.yg_font.source[k][kk] = d[kk]
        else:
            try:
                del self.yg_font.source[k]
            except KeyError:
                pass

    def restore(self) -> None:
        if self.yg_font.is_variable_font and self.msource:
            self.yg_font.source["masters"].clear()
            for k in self.msource.keys():
                self.yg_font.source["masters"][k] = self.msource[k]
        else:
            try:
                del self.yg_font.source["masters"]
            except KeyError:
                pass
        self._install_dict("cvt", self.csource)
        self._install_dict("defaults", self.dsource)
        self._install_dict("prep", self.psource)
        self._install_dict("macros", self.mcsource)
        self._install_dict("functions", self.fsource)


class fontInfoEditCommand(QUndoCommand):
    """Superclass for editing font-level data."""

    def __init__(self, yg_font: ygFont) -> None:
        super().__init__()
        self.yg_font = yg_font
        self.yg_glyph = self.yg_font.main_window.current_glyph()
        self.undo_state = fontInfoSaver(self.yg_font)
        self.redo_state: Union[fontInfoSaver, None] = None

    def send_signal(self) -> None:
        if self.yg_font.signal_connected:
            self.yg_font.sig_cvt_changed.emit()
            self.yg_glyph.sig_hints_changed.emit(self.yg_glyph.hints)

    def redo(self) -> None:
        pass

    def undo(self) -> None:
        self.undo_state.restore()
        self.send_signal()


class glyphEditCommand(QUndoCommand):
    """The superclass for most glyph editing commands.

    params:
    glyph (ygGlyph): The glyph being edited. Note that redo *must* be
    reimplemented, but undo ordinarily doesn't have to be.

    """

    def __init__(self, glyph: "ygGlyph") -> None:
        super().__init__()
        self.yg_glyph = glyph
        self.undo_state = glyphSaver(self.yg_glyph)
        self.redo_state: Union[glyphSaver, None] = None

    def send_signal(self) -> None:
        self.yg_glyph.sig_hints_changed.emit(self.yg_glyph.hints)
        self.yg_glyph.send_yaml_to_editor()

    def redo(self) -> None:
        pass

    def undo(self) -> None:
        self.undo_state.restore()
        self.send_signal()


class saveEditBoxCommand(fontInfoEditCommand):
    def __init__(
        self, yg_font: ygFont, sourceable: "ygSourceable", c: dict, text: str
    ) -> None:
        self.sourceable = sourceable
        self.c = c
        # self.text = text
        super().__init__(yg_font)
        self.setText(text)

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
            self.cv_delta.dataChanged.emit(self.index, self.index)
        else:
            self.sourceable._save(self.c)
        self.send_signal()


class setDefaultCommand(fontInfoEditCommand):
    def __init__(self, yg_font, yg_defaults, d: dict) -> None:
        self.yg_defaults = yg_defaults
        self.d = d
        super().__init__(yg_font)
        self.setText("Set defaults")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
            self.cv_delta.dataChanged.emit(self.index, self.index)
        else:
            self.yg_defaults._set_default(self.d)
            # for key, value in self.d.items():
            #    self.yg_defaults.data[key] = value
        self.send_signal()


class deleteDefaultCommand(fontInfoEditCommand):
    def __init__(self, yg_font, yg_defaults, k):
        self.yg_defaults = yg_defaults
        self.k = k
        super().__init__(yg_font)
        self.setText("Delete Default")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
            self.cv_delta.dataChanged.emit(self.index, self.index)
        else:
            try:
                del self.yg_defaults.data[self.k]
            except Exception:
                pass
        self.send_signal()


class roundingDefaultCommand(fontInfoEditCommand):
    def __init__(self, yg_font, yg_defaults, r: dict) -> None:
        self.yg_defaults = yg_defaults
        self.r = r
        super().__init__(yg_font)
        self.setText("Set rounding default")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
            self.cv_delta.dataChanged.emit(self.index, self.index)
        else:
            self.yg_defaults.clear_rounding()
            k = self.r.keys()
            for kk in k:
                val = self.r[kk]
                if val != self.yg_defaults.rounding_default(kk):
                    self.yg_defaults.set_rounding(kk, val)
        self.send_signal()


class editCVDeltaCommand(fontInfoEditCommand):
    def __init__(self, yg_font, cv_delta, index, val):
        self.yg_font = yg_font
        self.cv_delta = cv_delta
        self.index = index
        self.val = val
        super().__init__(yg_font)
        self.setText("Edit Control Value Deltas")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
            self.cv_delta.dataChanged.emit(self.index, self.index)
        else:
            if self.index.row() < len(self.cv_delta._data):
                self.cv_delta._store_val(self.index, self.val)
                self.cv_delta.dataChanged.emit(self.index, self.index)
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()

    def undo(self):
        self.undo_state.restore()
        self.cv_delta.dataChanged.emit(self.index, self.index)
        self.send_signal()


class addCVDeltaCommand(fontInfoEditCommand):
    def __init__(self, yg_font, cv_delta):
        self.yg_font = yg_font
        self.cv_delta = cv_delta
        self.index = self.cv_delta.rowCount(None)
        super().__init__(yg_font)
        self.setText("Add Control Value Delta")

    def redo(self):
        if self.redo_state:
            self.cv_delta.beginInsertRows(QModelIndex(), self.index, self.index)
            self.redo_state.restore()
            self.cv_delta.endInsertRows()
        else:
            c = self.cv_delta.cvt.get_cv(self.cv_delta.name)
            self.cv_delta.beginInsertRows(QModelIndex(), self.index, self.index)
            if not "deltas" in c:
                c["deltas"] = []
            c["deltas"].append(copy.deepcopy(INITIAL_CV_DELTA))
            self.cv_delta.endInsertRows()
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()

    def undo(self):
        self.cv_delta.beginRemoveRows(QModelIndex(), self.index, self.index)
        self.undo_state.restore()
        self.cv_delta.endRemoveRows()
        self.send_signal()


class deleteCVDeltaCommand(fontInfoEditCommand):
    def __init__(self, yg_font, cv_delta, c, row):
        self.yg_font = yg_font
        self.cv_delta = cv_delta
        self.c = c
        self.row = row
        super().__init__(yg_font)
        self.setText("Delete Control Value Delta")

    def redo(self):
        if self.redo_state:
            self.cv_delta.beginRemoveRows(QModelIndex(), self.row, self.row)
            self.redo_state.restore()
            self.cv_delta.endRemoveRows()
        else:
            self.cv_delta.beginRemoveRows(QModelIndex(), self.row, self.row)
            del self.c["deltas"][self.row]
            if len(self.c["deltas"]) == 0:
                try:
                    del self.c["deltas"]
                except Exception:
                    pass
            self.cv_delta.endRemoveRows()
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()

    def undo(self):
        self.cv_delta.beginInsertRows(QModelIndex(), self.row, self.row)
        self.undo_state.restore()
        self.cv_delta.endInsertRows()
        self.send_signal()


class addMasterCommand(fontInfoEditCommand):
    def __init__(self, yg_font, id, data):
        self.id = id
        self.data = data
        super().__init__(yg_font)
        self.setText("Add Master")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_font.source["masters"][self.id] = self.data
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class deleteMasterCommand(fontInfoEditCommand):
    def __init__(self, yg_font, id):
        self.id = id
        super().__init__(yg_font)
        self.setText("Delete Master")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                del self.yg_font.source["masters"][id]
            except Exception:
                pass
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class setMasterNameCommand(fontInfoEditCommand):
    def __init__(self, yg_font, m_id, name):
        self.m_id = m_id
        self.name = name
        super().__init__(yg_font)
        self.setText("Set Master Name")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if not self.m_id in self.yg_font.source["masters"]:
                self.yg_font.source["masters"][self.m_id] = {}
            self.yg_font.source["masters"][self.m_id]["name"] = self.name
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class setMasterAxisValueCommand(fontInfoEditCommand):
    def __init__(self, yg_font, m_id, axis, val):
        self.m_id = m_id
        self.axis = axis
        self.val = val
        super().__init__(yg_font)
        self.setText("Set Master Axis Value")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            if not "vals" in self.yg_font.source["masters"][self.m_id]:
                self.yg_font.source["masters"][self.m_id]["vals"] = {}
            self.yg_font.source["masters"][self.m_id]["vals"][self.axis] = self.val
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class deleteMasterAxisCommand(fontInfoEditCommand):
    def __init__(self, yg_font, m_id, axis):
        self.m_id = m_id
        self.axis = axis
        super().__init__(yg_font)
        self.setText("Delete Master Axis")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                del self.yg_font.source["masters"][self.m_id]["vals"][self.axis]
                if len(self.yg_font.source["masters"][self.m_id]["vals"]) == 0:
                    del self.yg_font.source["masters"][self.m_id]["vals"]
            except KeyError:
                pass
        self.send_signal()


class addCVCommand(fontInfoEditCommand):
    def __init__(self, yg_font: ygFont, name: str, props: Union[int, dict]) -> None:
        super().__init__(yg_font)
        self.name = name
        self.props = props
        self.setText("Add Control Value")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_font.source["cvt"][self.name] = self.props
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class setCVPropertyCommand(fontInfoEditCommand):
    def __init__(self, yg_font: ygFont, cv_name: str, prop_name: str, val: Any) -> None:
        super().__init__(yg_font)
        self.name = cv_name
        self.val = val
        self.prop = prop_name
        self.setText("Set Control Value Property")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_font.source["cvt"][self.name][self.prop] = self.val
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class delCVPropertyCommand(fontInfoEditCommand):
    def __init__(self, yg_font: ygFont, name: str, prop: str):
        self.name = name
        self.prop = prop
        super().__init__(yg_font)
        self.setText("Delete Control Value Property")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                del self.yg_font.source["cvt"][self.name][self.prop]
            except Exception:
                pass
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class deleteCVCommand(fontInfoEditCommand):
    def __init__(self, yg_font: ygFont, name: str) -> None:
        super().__init__(yg_font)
        self.name = name
        self.setText("Delete Control Value")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                del self.yg_font.source["cvt"][self.name]
            except KeyError:
                pass
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class renameCVCommand(fontInfoEditCommand):
    def __init__(self, yg_font: ygFont, old_name: str, new_name: str) -> None:
        self.old_name = old_name
        self.new_name = new_name
        super().__init__(yg_font)
        self.setText("Rename Control Value")

    def redo(self):
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_font.source["cvt"][self.new_name] = self.yg_font.source["cvt"].pop(
                self.old_name
            )
            self.redo_state = fontInfoSaver(self.yg_font)
        self.send_signal()


class changePointNumbersCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", to_coords: bool) -> None:
        super().__init__(glyph)
        self.to_coords = to_coords
        if self.to_coords:
            self.setText("Indices to Coords")
        else:
            self.setText("Coords to Indices")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph.sub_coords(
                self.yg_glyph.current_block, to_coords=self.to_coords
            )
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "changePointNumbersCommand").test()
        self.send_signal()


class updateSourceCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", s: list) -> None:
        super().__init__(glyph)
        self.s = s
        self.valid = True
        self.setText("Compile Glyph Program")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            try:
                self.yg_glyph.gsource[self.yg_glyph.axis]["points"].clear()
                for ss in self.s:
                    self.yg_glyph.gsource[self.yg_glyph.axis][
                        "points"
                    ].append(ss)
                self.yg_glyph._yaml_add_parents(self.yg_glyph.current_block)
                self.yg_glyph._yaml_supply_refs(self.yg_glyph.current_block)
            except Exception as e:
                print(e)
                self.undo_state.restore()
                self.valid = False
        self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "updateSourceCommand").test()
        if self.valid:
            self.send_signal()


class replacePointNamesCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", name_dict: dict) -> None:
        super().__init__(glyph)
        self.name_dict = name_dict
        self.setText("Edit Point Names")

    def redo(self) -> None:
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
        glyphSourceTester(self.yg_glyph, "replacePointNamesCommand").test()
        self.send_signal()


class replaceGlyphPropsCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", prop_dict: dict) -> None:
        super().__init__(glyph)
        self.prop_dict = prop_dict
        self.setText("Edit Glyph Properties")

    def redo(self) -> None:
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
        glyphSourceTester(self.yg_glyph, "replaceGlyphPropsCommand").test()
        self.send_signal()


class addPointSetNameCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", pt: list, name: str) -> None:
        super().__init__(glyph)
        self.pt = pt
        self.name = name
        self.setText("Name Point(s)")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
            self.yg_glyph.names.update_point_names()
        else:
            if not "names" in self.yg_glyph.gsource:
                self.yg_glyph.gsource["names"] = {}
            if type(self.pt) is not list:
                self.yg_glyph.gsource["names"][
                    self.name
                ] = self.yg_glyph.resolve_point_identifier(self.pt).preferred_label(
                    name_allowed=False
                )
                self.yg_glyph.names.update_point_names()
            else:
                if len(self.pt) == 1:
                    self.yg_glyph.gsource["names"][self.name] = self.pt[
                        0
                    ].preferred_label(name_allowed=False)
                    self.yg_glyph.names.update_point_names()
                elif len(self.pt) > 1:
                    pt_list = []
                    for p in self.pt:
                        pt_list.append(p.preferred_label(name_allowed=False))
                    self.yg_glyph.gsource["names"][self.name] = pt_list
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "addPointSetNameCommand").test()
        self.send_signal()

    def undo(self) -> None:
        self.undo_state.restore()
        self.yg_glyph.names.update_point_names()
        self.send_signal()


class setMacFuncOtherArgsCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint", new_params: dict) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.new_params = new_params
        self.setText("Edit parameters")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint.source[self.hint.hint_type] = self.new_params
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "setMacFuncOtherArgsCommand").test()
        self.send_signal()


class swapMacFuncPointsCommand(glyphEditCommand):
    def __init__(
        self, glyph: "ygGlyph", hint: "ygHint", new_name: str, old_name: str
    ) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.new_name = new_name
        self.old_name = old_name
        self.setText("Swap Mac/Func points")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            if type(self.hint.source["ptid"]) is dict:
                try:
                    (
                        self.hint.source["ptid"][self.new_name],
                        self.hint.source["ptid"][self.old_name],
                    ) = (
                        self.hint.source["ptid"][self.old_name],
                        self.hint.source["ptid"][self.new_name],
                    )
                except Exception as e:
                    self.hint.source["ptid"][self.new_name] = self.hint._source[
                        "ptid"
                    ][self.old_name]
                    del self.hint.source["ptid"][self.old_name]
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "swapMacFuncPointsCommand").test()
        self.send_signal()


class cleanupGlyphCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph") -> None:
        super().__init__(glyph)
        self.setText("Clean up code")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph._rebuild_current_block()
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "cleanupGlyphCommand").test()
        self.send_signal()


class changeDistanceTypeCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint", new_color: str) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.new_color = new_color
        self.setText("Change distance type")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint.source["rel"] = self.new_color
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "changeDistanceTypeCommand").test()
        self.send_signal()


class toggleMinDistCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint") -> None:
        super().__init__(glyph)
        self.hint = hint
        self.setText("Toggle Minimum Distance")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            current_min_dist = not self.hint.min_dist
            if current_min_dist == self.hint.min_dist_is_default():
                if "min" in self.hint.source:
                    del self.hint.source["min"]
            else:
                self.hint.source["min"] = current_min_dist
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "toggleMinDistCommand").test()
        self.send_signal()


class changeCVCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint", new_cv: str) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.new_cv = new_cv
        self.setText("Set Control Value")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._set_cv(self.new_cv)
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "changeCVCommand").test()
        self.send_signal()


class toggleRoundingCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint") -> None:
        super().__init__(glyph)
        self.hint = hint
        self.setText("Toggle Rounding")

    def redo(self) -> None:
        current_round = not self.hint.rounded
        if self.redo_state:
            self.redo_state.restore()
        else:
            if current_round == self.hint.round_is_default():
                if "round" in self.hint.source:
                    del self.hint.source["round"]
            else:
                self.hint.source["round"] = current_round
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "toggleRoundingCommand").test()
        self.send_signal()


class addHintCommand(glyphEditCommand):
    def __init__(
        self, glyph: "ygGlyph", hint: "ygHint", conditional: bool = False
    ) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.conditional = conditional
        self.setText("Add Hint")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.yg_glyph._add_hint(self.hint, self.yg_glyph.current_block)
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "addHintCommand").test()
        self.send_signal()


class deleteHintsCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", l: list) -> None:
        super().__init__(glyph)
        self.hint_list = l
        self.setText("Delete Hints")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            for h in self.hint_list:
                s = h.source
                if "parent" in s:
                    try:
                        s["parent"]["points"].remove(s)
                    except Exception as e:
                        pass
                else:
                    try:
                        self.yg_glyph.current_block.remove(s)
                    except Exception as e:
                        pass
                if "points" in s:
                    for hh in s["points"]:
                        try:
                            if not "rel" in hh or hint_type_nums[hh["rel"]] == 4:
                                self.yg_glyph.add_hint(ygHint(self.yg_glyph, hh))
                        except Exception as e:
                            pass
            glyphSourceTester(self.yg_glyph, "deleteHintsCommand").test()
            self.redo_state = glyphSaver(self.yg_glyph)
        self.send_signal()


class reverseHintCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint") -> None:
        super().__init__(glyph)
        self.hint = hint
        self.setText("Reverse Hint")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint.source["ptid"], self.hint.source["ref"] = (
                self.hint.source["ref"],
                self.hint.source["ptid"],
            )
            self.yg_glyph._rebuild_current_block()
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "reverseHintCommand").test()
        self.send_signal()


class addPointsCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint", p_list: list) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.p_list = p_list
        self.setText("Adds points to hint")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._add_points(self.p_list)
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "addPointsCommand").test()
        self.send_signal()


class deletePointsCommand(glyphEditCommand):
    def __init__(self, glyph: "ygGlyph", hint: "ygHint", p_list: list) -> None:
        super().__init__(glyph)
        self.hint = hint
        self.p_list = p_list
        self.setText("Delete points from hint")

    def redo(self) -> None:
        if self.redo_state:
            self.redo_state.restore()
        else:
            self.hint._delete_points(self.p_list)
            self.redo_state = glyphSaver(self.yg_glyph)
        glyphSourceTester(self.yg_glyph, "deletePointsCommand").test()
        #self.yg_glyph._hints_changed(self.yg_glyph.hints)
        self.send_signal()


class switchAxisCommand(QUndoCommand):
    def __init__(self, g: "ygGlyph", prefs: ygPreferences, new_axis: str) -> None:
        super().__init__()
        self.yg_glyph = g
        self.original_axis = self.yg_glyph.axis
        self.new_axis = new_axis
        self.top_window = prefs.top_window()
        self.setText("Change Axis")

    def redo(self) -> None:
        if self.yg_glyph.axis == self.new_axis:
            return
        self.top_window.current_axis = self.yg_glyph.axis = self.new_axis
        self.yg_glyph._hints_changed(self.yg_glyph.hints, dirty=False)
        self.yg_glyph.send_yaml_to_editor()
        self.top_window.set_window_title()
        self.top_window.check_axis_button()

    def undo(self) -> None:
        self.top_window.current_axis = self.yg_glyph.axis = self.original_axis
        self.yg_glyph.sig_hints_changed.emit(self.yg_glyph.hints)
        self.yg_glyph.send_yaml_to_editor()
        self.top_window.set_window_title()
        self.top_window.check_axis_button()


class glyphAddPropertyCommand(QUndoCommand):
    """redo() has got to be the action itself. It will get excecuted when the
    constructor is called. So use the construction of this class to
    execute the command initially.

    undo() can be simpler: it can simply restore a saved state of the whole
    block.

    Constructor needs to save everything needed to execute the command,
    keeping its own separate copy of anything mutable (e.g. a list of
    selected objects).
    """

    def __init__(self, yg_glyph: "ygGlyph", prop_name: str, prop_value: Any) -> None:
        super().__init__()
        self.yg_glyph = yg_glyph
        self.props = None
        if "props" in self.yg_glyph.gsource:
            self.props = copy.deepcopy(self.yg_glyph.gsource["props"])
        self.prop_name = prop_name
        self.prop_value = prop_value
        self.setText("Add Glyph Property")

    @pyqtSlot()
    def undo(self) -> None:
        if "props" in self.yg_glyph.gsource:
            if self.props:
                self.yg_glyph.gsource["props"] = self.props
            else:
                del self.yg_glyph.gsource["props"]
        self.yg_glyph._hints_changed(self.yg_glyph.hints)

    @pyqtSlot()
    def redo(self) -> None:
        if not "props" in self.yg_glyph.gsource:
            self.yg_glyph.gsource["props"] = {}
        self.yg_glyph.gsource["props"][self.prop_name] = self.prop_value
        glyphSourceTester(self.yg_glyph, "glyphAddPropertyCommand").test()
        self.yg_glyph._hints_changed(self.yg_glyph.hints)


class glyphDeletePropertyCommand(QUndoCommand):
    def __init__(self, yg_glyph: "ygGlyph", prop_name: str) -> None:
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
    def undo(self) -> None:
        # Undo action is just to replace the current props block
        # with the former one.
        if self.props != None:
            if "props" in self.yg_glyph.gsource:
                self.yg_glyph.gsource["props"] = self.props
        else:
            if "props" in self.yg_glyph.gsource:
                del self.yg_glyph.gsource["props"]
        self.yg_glyph._hints_changed(self.yg_glyph.hints)

    @pyqtSlot()
    def redo(self) -> None:
        try:
            del self.yg_glyph.gsource["props"][self.prop_name]
            if len(self.yg_glyph.gsource["props"]) == 0:
                del self.yg_glyph.gsource["props"]
            self.yg_glyph._hints_changed(self.yg_glyph.hints)
        except Exception:
            pass
        glyphSourceTester(self.yg_glyph, "glyphDeletePropertyCommand").test()


class glyphSourceTester:
    def __init__(self, yg_glyph: "ygGlyph", caller: str):
        self.yg_glyph = yg_glyph
        self.caller = caller

    def test(self) -> None:
        try:
            if (
                self.yg_glyph.gsource
                != self.yg_glyph.yg_font.source["glyphs"][self.yg_glyph.gname]
            ):
                print("Not equal in " + self.caller)
            if (
                self.yg_glyph.gsource
                is not self.yg_glyph.yg_font.source["glyphs"][self.yg_glyph.gname]
            ):
                print("Not same in " + self.caller)
        except Exception as e:
            print("Error in glyphSourceTester.test: " + str(e))


class ygGlyph(QObject):
    """Keeps all the data for one glyph and provides an interface for
    changing it.

    Parameters:

    preferences (ygPreferences.ygPreferences): Preferences for the app.

    yg_font (ygFont): The font object, providing access to the fontTools
    representation and the whole of the hinting source.

    gname (str): The name of this glyph.

    """

    sig_hints_changed = pyqtSignal(object)
    sig_glyph_source_ready = pyqtSignal(object)

    def __init__(self, preferences: ygPreferences, yg_font: ygFont, gname: str) -> None:
        """Requires a ygFont object and the name of the glyph. Also access to preferences
        as a convenience.
        """
        super().__init__()
        self.preferences = preferences
        self.top_window = self.preferences.top_window()
        if self.top_window != None:
            self.undo_stack = QUndoStack()
            self.top_window.add_undo_stack(self.undo_stack)
            self.undo_stack.setActive(True)
        self.yaml_editor = None
        self._yg_font = yg_font
        # The next few lines have to come *after* loading the ft_font (below)
        self._gname = gname

        # Work with the glyph from the fontTools representation of the font.

        try:
            self.ft_glyph = yg_font.ft_font["glyf"][self.gname]
        except KeyError:
            l = list(yg_font.ft_font.getGlyphSet())
            if "A" in l:
                self.gname = "A"
            elif len(l) >= 2:
                self.gname = l[1]
            else:
                raise Exception("Tried to load nonexistent glyph " + self.gname)
            self.ft_glyph = yg_font.ft_font["glyf"][self.gname]
        self.is_composite = self.ft_glyph.isComposite()

        # Initialize the source for this glyph.

        self._gsource = yg_font.get_glyph(self.gname)
        self.props = ygGlyphProperties(self)
        self.error = 0

        if not "y" in self.gsource:
            self.gsource["y"] = {"points": []}
        if not "x" in self.gsource:
            self.gsource["x"] = {"points": []}

        self.set_clean()

        # Going to run several indexes for this glyph's points. This is because
        # Xgridfit is permissive about naming, so we need several ways to look
        # up points. (Check later to make sure all these are being used.)

        # Extract points from the fontTools Glyph object and store them in a list.
        self.point_list = self._make_point_list()

        # Get the named glyphs (we need self.point_list to do this)
        self.names = ygGlyphNames(self)

        # Dict for looking up points with uuid-generated id.
        self.point_id_dict = {}
        for p in self.point_list:
            self.point_id_dict[p.id] = p

        # Dict for looking up points by coordinates
        self.point_coord_dict = {}
        for p in self.point_list:
            self.point_coord_dict[p.coord] = p

        # Decide the initial axis.
        if self.preferences and self.top_window != None:
            self._current_axis = self.top_window.current_axis
        else:
            self._current_axis = "y"

        # A little fix

        backup_axis = self.axis
        self.axis = "y"
        self.fix_hint_types(self.current_block)
        self.axis = "x"
        self.fix_hint_types(self.current_block)
        self.axis = backup_axis

        # Fix up the source to make it more usable.
        self._yaml_add_parents(self.current_block)
        self._yaml_supply_refs(self.current_block)

        # This is the QGraphicsScene wrapper for this glyph object. But
        # do we need a reference here in the __init__? It's only used once,
        # in setting up a signal, and there are other ways to do that.
        self.yg_glyph_scene = None

        self.sig_hints_changed.connect(self.hints_changed)
        if self.top_window != None:
            self.set_auto_preview_connection()

    #def report_vars(self) -> None:
    #    print("Glyph name: " + self.gname)
    #    print("Size of undo stack: " + str(self.undo_stack.count()))
    #    print("Code for glyph:")
    #    print(self.gsource)
    #    print("Current block:")
    #    print(self.current_block)

    def send_error_message(self, d: dict):
        if self.yg_font:
            self.yg_font.send_error_message(d)

    #
    # Ordering and structuring YAML source
    #

    def restore_gsource(self) -> None:
        """Run when returning to a glyph."""
        if not "y" in self.gsource:
            self.gsource["y"] = {"points": []}
        if not "x" in self.gsource:
            self.gsource["x"] = {"points": []}
        self._yaml_add_parents(self.gsource["y"]["points"])
        self._yaml_supply_refs(self.gsource["y"]["points"])
        self._yaml_add_parents(self.gsource["x"]["points"])
        self._yaml_supply_refs(self.gsource["x"]["points"])

    def _flatten_yaml_tree(self, tree: list) -> list:
        """Helper for rebuild_current_block"""
        flat = []
        for t in tree:
            if "parent" in t:
                del t["parent"]
            flat.append(t)
            if "points" in t:
                flat.extend(self._flatten_yaml_tree(t["points"]))
        return flat

    def place_all(self, hl: list) -> list:
        """Helper for rebuild_current_block"""
        block: list = []
        total_to_place = len(hl)
        placed: dict = {}
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

    def _rebuild_current_block(self) -> None:
        """Tears down the current source block and rebuilds it with proper
        regard for dependency and order. When this is reliable enough, it
        will be called every time the source is updated.

        """
        flattened_tree = self._flatten_yaml_tree(copy.deepcopy(self.current_block))
        for f in flattened_tree:
            if "points" in f:
                del f["points"]
        new_tree = ygHintSorter(self.place_all(flattened_tree)).sort()
        self.gsource[self.axis]["points"].clear()
        for t in new_tree:
            self.gsource[self.axis]["points"].append(t)
        self.sig_hints_changed.emit(self.hints)
        self.send_yaml_to_editor()

    def rebuild_current_block(self) -> None:
        self.undo_stack.push(cleanupGlyphCommand(self))

    def _yaml_mk_hint_list(self, source: list, validate: bool = False) -> list:
        """'source' is a yaml "points" block."""
        flist = []
        for pt in source:
            flist.append(ygHint(self, pt))
            if ("points" in pt) and pt["points"]:
                flist.extend(self._yaml_mk_hint_list(pt["points"]))
        return flist

    def _yaml_add_parents(self, node: list) -> None:
        """Walk through the yaml source for one 'points' block, adding 'parent'
        items to each point dict so that we can easily climb the tree if we
        have to.

        We do this (and also supply refs) when we copy a "y" or "x" block
        from the main source file so we don't have to do it elsewhere.

        """
        for pt in node:
            if "points" in pt:
                for ppt in pt["points"]:
                    ppt["parent"] = pt
                self._yaml_add_parents(pt["points"])

    def _yaml_supply_refs(self, node: list) -> None:
        """After "parent" properties have been added, walk the tree supplying
        implicit references. If we can't find a reference, let it go (it
        doesn't seem to actually happen).

        """
        if type(node) is list:
            for n in node:
                type_num = hint_type_nums[self._yaml_hint_type(n)]
                if type_num in [1, 3]:
                    if "parent" in n and not "ref" in n:
                        n["ref"] = self._yaml_get_single_target(n["parent"])
                    else:
                        pass
                if type_num == 2:
                    reflist = []
                    if "parent" in n:
                        reflist.append(self._yaml_get_single_target(n["parent"]))
                        if "parent" in n["parent"]:
                            reflist.append(
                                self._yaml_get_single_target(n["parent"]["parent"])
                            )
                    if len(reflist) == 2 and not "ref" in n:
                        n["ref"] = reflist
                if "points" in n:
                    self._yaml_supply_refs(n["points"])

    def yaml_strip_extraneous_nodes(self, node: list) -> None:
        """Walks the yaml tree, stripping out parent references and
        explicit statements of implicit refs.

        """
        for pt in node:
            if "parent" in pt:
                h = ygHint(self, pt["parent"])
                if (not h.hint_type in ["function", "macro"]) and len(
                    h.target_list()
                ) == 1:
                    del pt["ref"]
                del pt["parent"]
            if "points" in pt:
                self.yaml_strip_extraneous_nodes(pt["points"])

    def _yaml_get_single_target(self, node: dict) -> Any:
        """This is for building the yaml tree. We need a single point (not a
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
            random_point: Union[int, list] = 0
            for kk in k:
                random_point = node["ptid"][kk]
                if type(random_point) is not list:
                    break
            if type(random_point) is list:
                return random_point[0]
            else:
                return random_point
        return 0

    #
    # Accessing glyph data
    #

    def extreme_points_y(self):
        last_highest = highest = -100000
        last_lowest = lowest = 100000
        highest_point = -1
        lowest_point = -1
        for i, p in enumerate(self.point_list):
            highest = max(highest, p.font_y)
            if highest != last_highest:
                last_highest = highest
                highest_point = i
            lowest = min(lowest, p.font_y)
            if lowest != last_lowest:
                last_lowest = lowest
                lowest_point = i
        return (highest_point, highest), (lowest_point, lowest)

    def extreme_points_x(self):
        last_right = right = -100000
        last_left = left = 100000
        rightmost_point = -1
        leftmost_point = -1
        for i, p in enumerate(self.point_list):
            right = max(right, p.font_x)
            if right != last_right:
                last_right = right
                rightmost_point = i
            left = min(left, p.font_x)
            if left != last_left:
                last_left = left
                leftmost_point = i
        return (rightmost_point, right), (leftmost_point, left)

    def dimensions(self):
        if len(self.point_list) == 0:
            return 0, 0
        x_right, x_left = self.extreme_points_x()
        y_top, y_bottom = self.extreme_points_y()
        x_dim = x_right[1] - x_left[1]
        y_dim = y_top[1] - y_bottom[1]
        return x_dim, y_dim

    def get_category(self, long_name: bool = False) -> str:
        cat = self.props.get_property("category")
        if cat == None:
            cat = self.yg_font.get_unicode_category(self.gname)
        if long_name:
            return unicode_cat_names[cat]
        return cat

    @property
    def axis(self) -> str:
        return self._current_axis
    
    @axis.setter
    def axis(self, a: str) -> None:
        if a in ["y", "x"]:
            self._current_axis = a
        else:
            raise ValueError("Axis must be 'y' or 'x'.")

    @property
    def yg_font(self) -> ygFont:
        return self._yg_font
    
    @property
    def gname(self) -> str:
        return self._gname
    
    @property
    def gsource(self) -> dict:
        return self._gsource

    @property
    def current_block(self) -> list:
        if self.axis == "y":
            return self.gsource["y"]["points"]
        else:
            return self.gsource["x"]["points"]

    @property
    def hints(self) -> list:
        """Get a list of hints for the current axis, wrapped in ygHint
        objects.

        """
        return self._yaml_mk_hint_list(self.current_block, validate=True)

    @property
    def points(self) -> list:
        return self.point_list

    def indices_to_coords(self) -> None:
        """Change coordinates in current block to point indices."""
        self.undo_stack.push(changePointNumbersCommand(self, True))

    def coords_to_indices(self) -> None:
        """Change point indices in current block to coordinates."""
        self.undo_stack.push(changePointNumbersCommand(self, False))

    def fix_hint_types(self, block):
        for ppt in block:
            if "rel" in ppt and "space" in ppt["rel"]:
                ppt["rel"] = ppt["rel"].replace("space", "dist")
            if "points" in ppt:
                self.fix_hint_types(ppt["points"])

    def sub_coords(self, block: list, to_coords: bool = True) -> None:
        """Helper for indices_to_coords and coords_to_indices"""
        for ppt in block:
            ppt["ptid"] = self._sub_coords(ppt["ptid"], to_coords)
            if "ref" in ppt:
                ppt["ref"] = self._sub_coords(ppt["ref"], to_coords)
            if "points" in ppt:
                self.sub_coords(ppt["points"], to_coords=to_coords)

    @overload
    def _sub_coords(self, block: dict, to_coords: bool) -> dict:
        ...

    @overload
    def _sub_coords(self, block: list, to_coords: bool) -> list:
        ...

    @overload
    def _sub_coords(
        self, block: Union[str, int], to_coords: bool
    ) -> Union[str, int, None]:
        ...

    def _sub_coords(
        self, block: Union[list, dict, str, int], to_coords: bool
    ) -> Union[list, dict, str, int, None]:
        """Helper for indices_to_coords and coords_to_indices"""
        if type(block) is dict:
            new_dict = {}
            for kk, v in block.items():
                if type(v) is list:
                    new_dict[kk] = self._sub_coords(v, to_coords)
                else:
                    if to_coords:
                        try:
                            new_dict[kk] = self.resolve_point_identifier(v).coord
                        except Exception:
                            pass
                    else:
                        try:
                            new_dict[kk] = self.resolve_point_identifier(v).index
                        except Exception:
                            pass
            return new_dict
        elif type(block) is list:
            new_list = []
            for pp in block:
                if to_coords:
                    try:
                        new_list.append(self.resolve_point_identifier(pp).coord)
                    except Exception:
                        pass
                else:
                    try:
                        new_list.append(self.resolve_point_identifier(pp).index)
                    except Exception:
                        pass
            return new_list
        else:
            if to_coords:
                try:
                    return self.resolve_point_identifier(block).coord
                except Exception:
                    pass
            else:
                try:
                    return self.resolve_point_identifier(block).index
                except Exception:
                    pass
        return None

    def match_category(self, cat1: str, cat2: str) -> bool:
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

    def get_suffixes(self) -> list:
        """Will return an empty list if no suffixes"""
        s = self.gname.split(".")
        return s[1:]

    def search_source(
        self,
        block: list,
        pt: Union[ygPoint, ygSet, ygParams, int, str, None],
        ptype: str,
    ) -> list:
        """Search the yaml source for a point.

        Parameters:
        block (list): At the top level, should be self.current_block.

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

        def _to_ygSet(o) -> ygSet:
            """ """
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

    #def glyph_name(self) -> str:
    #    return self.gname

    @property
    def xoffset(self) -> int:
        xo = self.props.get_property("xoffset")
        if xo != None:
            return xo
        return 0

    @property
    def yoffset(self) -> int:
        yo = self.props.get_property("yoffset")
        if yo != None:
            return yo
        return 0

    def _yaml_hint_type(self, n) -> str:
        """Helper for _yaml_supply_refs"""
        if "function" in n:
            return "function"
        if "macro" in n:
            return "macro"
        if "rel" in n:
            return n["rel"]
        return "anchor"

    def _is_pt_obj(self, o: Any) -> bool:
        """Whether an object is a 'point object' (a point or a container for
        points), which can appear in a ptid or ref field.

        """
        return type(o) is ygPoint or type(o) is ygSet or type(o) is ygParams

    def _make_point_list(self) -> list:
        """Make a list of the points in a fontTools glyph structure.

        Returns:
        A list of ygPoint objects.

        """
        pt_list = []
        gl = self.ft_glyph.getCoordinates(self.yg_font.ft_font["glyf"])
        lpref = "index"
        if self.top_window != None and self.top_window.points_as_coords:
            lpref = "coord"
        for point_index, p in enumerate(zip(gl[0], gl[2])):
            is_on_curve = p[1] & 0x01 == 0x01
            pt = ygPoint(
                None,
                point_index,
                p[0][0],
                p[0][1],
                self.xoffset,
                self.yoffset,
                is_on_curve,
                label_pref=lpref,
            )
            if point_index in gl[1]:
                pt.end_of_contour = True
            pt_list.append(pt)
        return pt_list

    #
    # Navigation
    #

    def switch_to_axis(self, new_axis: str) -> None:
        if self.axis == "y":
            new_axis = "x"
        else:
            new_axis = "y"
        self.undo_stack.push(switchAxisCommand(self, self.preferences, new_axis))

    #
    # Saving
    #

    def save_editor_source(self, s: list) -> None:
        """When the user has typed Ctrl+R to compile the contents of the
        editor pane, this function gets called to do the rest. It
        massages the yaml source exactly as the __init__for this class
        does (calling the same functions) and installs new source
        in self.current_block. Finally it
        sends sig_hints_changed to notify that the hints are ready to
        render and sends reconstituted source back to the editor.
        """
        new_cmd = updateSourceCommand(self, s)
        self.undo_stack.push(new_cmd)
        if not new_cmd.valid:
            new_cmd.setObsolete(True)
            self.send_error_message({"msg": "Invalid source.", "mode": "console"})

    def cleanup_glyph(self, source: Union[dict, None] = None) -> None:
        """Call before saving YAML file."""
        if source:
            s = source
        else:
            s = self.gsource
        have_y = True
        have_x = True
        if "y" in s and len(s["y"]["points"]) == 0:
            have_y = False
        if "x" in s and len(s["x"]["points"]) == 0:
            have_x = False
        if have_y:
            self.yaml_strip_extraneous_nodes(s["y"]["points"])
        else:
            del s["y"]
        if have_x:
            self.yaml_strip_extraneous_nodes(s["x"]["points"])
        else:
            del s["x"]
        if not have_y and not have_x:
            self.yg_font.del_glyph(self.gname)

    #
    # Editing
    #

    def set_category(self, c: str) -> None:
        # Called function will use QUndoCommand.
        reverse_unicode_cat_names
        self.props.add_property("category", reverse_unicode_cat_names[c])

    def combine_point_blocks(self, block: dict) -> Union[list, None]:
        if len(block) > 0:
            new_block = []
            k = block.keys()
            for kk in k:
                new_block.extend(block[kk])
            return new_block
        return None

    def _add_hint(self, h: Any, block: list, conditional: bool = False) -> bool:
        """If conditional=False, function will always place a hint somewhere
        in the tree (in the top level when it can't find another place).
        When True, function will return False when it fails to place the
        hint in the tree.
        """
        ref = None
        if type(h) is ygHint:
            h = h.source
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

    def add_hint(self, h: "ygHint") -> None:
        self.undo_stack.push(addHintCommand(self, h))

    def delete_hints(self, l: list) -> None:
        """l: a list of ygHint objects"""
        self.undo_stack.push(deleteHintsCommand(self, l))

    def set_dirty(self) -> None:
        self._clean = False
        self.yg_font.set_dirty()

    def set_clean(self) -> None:
        self._clean = True

    def clean(self) -> bool:
        return self._clean

    @overload
    def points_to_labels(self, pts: Union[ygPoint, str]) -> str:
        ...

    @overload
    def points_to_labels(self, pts: int) -> int:
        ...

    @overload
    def points_to_labels(self, pts: Union[list, ygSet, ygParams]) -> list:
        ...

    def points_to_labels(
        self, pts: Union[str, int, list, ygSet, ygParams, ygPoint]
    ) -> Union[str, int, list]:
        """Accepts a ygPoint, ygSet or ygParams object and converts it to a
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
            return self.points_to_labels(pts.point_list)
        if type(pts) is ygParams:
            pp = pts.point_list
            result = []
            for p in pp:
                if type(p) is ygPoint:
                    result.append(p.preferred_label())
                elif type(p) is list:
                    result.extend(self.points_to_labels(p))
            return result
        if type(pts) is ygPoint:
            return pts.preferred_label()
        return 0

    def resolve_point_identifier(self, ptid: Any, depth: int = 0) -> Any:
        """Get the ygPoint object identified by ptid. ***Failures are very
        possible here, since there may be nonsense in a source file or in
        the editor. We handle obvious bad results (like None instead of an
        object) by returning the zero point and issuing an error message.

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
        if depth == 0:
            self.error = 0
        if type(ptid) is str:
            try:
                ptid = int(ptid)
            except Exception:
                pass
        result = ptid
        if self._is_pt_obj(ptid):
            return result
        if type(ptid) is list:
            new_list = []
            for p in ptid:
                new_list.append(self.resolve_point_identifier(p, depth=depth + 1))
            return ygSet(new_list)
        elif type(ptid) is dict:
            new_dict = {}
            key_list = ptid.keys()
            for key in key_list:
                p = self.resolve_point_identifier(ptid[key], depth=depth + 1)
                new_dict[key] = p
            return ygParams(None, None, new_dict, None)
        elif type(ptid) is int:
            try:
                result = self.point_list[ptid]
                if self._is_pt_obj(result):
                    return result
            except IndexError:
                if self.error == 0:
                    self.error |= POINT_OUT_OF_RANGE
                    m = "Point index "
                    m += str(ptid)
                    m += " is out of range. This glyph may have been "
                    m += "edited since its hints were written, and if so, they "
                    m += "will have to be redone."
                    self.send_error_message({"msg": m, "mode": "console"})
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
            if self.error == 0:
                self.error |= POINT_UNIDENTIFIABLE
                m = "Failed to resolve point identifier "
                m += str(ptid)
                m += " in glyph "
                m += self.gname
                m += ". Substituting zero."
                self.send_error_message({"msg": m, "mode": "console"})
            return self.point_list[0]
        result = self.resolve_point_identifier(result, depth=depth + 1)
        if self._is_pt_obj(result):
            return result

    #
    # Signals and slots
    #

    def set_auto_preview_connection(self) -> None:
        if self.top_window.auto_preview_update:
            self.sig_hints_changed.connect(
                self.top_window.preview_current_glyph
            )
        else:
            try:
                self.sig_hints_changed.disconnect(
                    self.top_window.preview_current_glyph
                )
            except Exception as e:
                # print(e)
                pass

    def set_yaml_editor(self, ed: Any) -> None:
        """Registers a slot in a ygYAMLEditor object, for installing source."""
        self.sig_glyph_source_ready.connect(ed.install_source)
        self.send_yaml_to_editor()

    def send_yaml_to_editor(self) -> None:
        """Sends yaml source for the current x or y block to the editor pane."""
        new_yaml = copy.deepcopy(self.current_block)
        self.yaml_strip_extraneous_nodes(new_yaml)
        self.sig_glyph_source_ready.emit(
            [yaml.dump(new_yaml, sort_keys=False, Dumper=Dumper), self.is_composite]
        )

    def hint_changed(self, h: Union["ygHint", None]):
        """Called by signal from ygHint. Sends a list of hints in response."""
        self.set_dirty()
        self.sig_hints_changed.emit(self.hints)
        self.send_yaml_to_editor()

    @pyqtSlot(object)
    def hints_changed(self, hint_list: list) -> None:
        self._hints_changed(hint_list)

    def _hints_changed(
            self,
            hint_list: list,
            dirty: bool = True
        ) -> None:
        if dirty:
            self.set_dirty()
        from .ygHintEditor import ygGlyphScene

        if self.yg_glyph_scene:
            self.yg_glyph_scene.install_hints(hint_list)

        if self.top_window != None:
            if self.top_window.font_viewer:
                self.top_window.font_viewer.update_cell(self.gname)


class ygGlyphs:
    """The "glyphs" section of a yaml file."""

    def __init__(self, source: dict) -> None:
        try:
            self.data = source["glyphs"]
        except KeyError:
            self.data = {}

    def get_glyph(self, gname: str) -> dict:
        if gname in self.data:
            return self.data[gname]
        else:
            return {}

    #def glyph_list(self) -> list:
    #    return list(self.data.keys())

    def del_glyph(self, gname: str) -> None:
        if gname in self.data:
            del self.data[gname]


class Comparable(object):
    """For ordering hints such that a reference point never points to an
    untouched point.
    """

    def _compare(self, other: "Comparable", method: Callable) -> Any:
        try:
            return method(self._cmpkey(), other._cmpkey())
        except (AttributeError, TypeError):
            return NotImplemented

    @abc.abstractmethod
    def _cmpkey(self) -> tuple:
        ...

    def _mk_point_list(self, obj: dict, key: str) -> list:
        """Helper for comparison functions. For target points, this will
        recurse into dependent hints to build a complete list.

        """
        hint = ygHint(None, obj) # type: ignore
        if key == "ptid":
            p = hint.target
        else:
            p = hint.ref
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
        return result

    def _comparer(self, obj1: dict, obj2: dict) -> int:
        """Helper for comparison functions. A return value of zero doesn't
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

    def __eq__(self, other: object) -> bool:
        return self == other

    def __ne__(self, other: object) -> bool:
        return self != other

    @abc.abstractmethod
    def __lt__(self, other: object) -> bool:
        ...

    @abc.abstractmethod
    def __gt__(self, other: object) -> bool:
        ...

    @abc.abstractmethod
    def __ge__(self, other: object) -> bool:
        ...

    @abc.abstractmethod
    def __le__(self, other: object) -> bool:
        ...


class ygHintSource(Comparable):
    """Before sorting a list of hints, wrap the source (._source) for each
    one in this. Class ygHintSorter does the actual sorting.
    """

    def __init__(self, s):
        self._source = s

    def _cmpkey(self) -> tuple:
        return (self._source,)

    def __hash__(self) -> int:
        return hash(self._cmpkey())

    def __lt__(self, other):
        return self._comparer(self._source, other._source) < 0

    def __gt__(self, other):
        return self._comparer(self._source, other._source) > 0

    def __ge__(self, other):
        return (
            self._comparer(self._source, other._source) > 0
            or self._source == other._source
        )

    def __le__(self, other):
        return (
            self._comparer(self._source, other._source) < 0
            or self._source == other._source
        )


class ygHint(QObject):
    """A hint. This wraps a point from the yaml source tree and provides
    a number of functions for accessing and altering it.

    Parameters:

    glyph (ygGlyph): The glyph for which this is a hint. It is okay to
    pass None here, though mypy complains (use --no-strict-optional to
    suppress the error).

    point: The point, list or dict that is the target of this hint.

    """

    hint_changed_signal = pyqtSignal(object)

    def __init__(self, glyph: ygGlyph, point: dict) -> None:
        super().__init__()
        self._id = uuid.uuid1()
        self._source = point
        self.yg_glyph = glyph
        self.placed = False

        if self.yg_glyph != None:
            self.hint_changed_signal.connect(self.yg_glyph.hint_changed)

    @property
    def source(self) -> dict:
        return self._source

    # The next two are not used right now. Note that parent() conflicts
    # with the superclass, so if we decide to use it, we have to
    # rename it.

    # def parent(self):
    #    if "parent" in self.source:
    #        return self.source["parent"]

    # def children(self):
    #    if "points" in self.source:
    #        return self.source["points"]

    @property
    def id(self):
        return self._id

    @property
    def target(self) -> Any:
        """May return a point identifier (index, name, coordinate-pair), a list,
        or a dict.

        """
        return self._source["ptid"]

    # This is not used right now
    # @target.setter
    # def target(self, tgt: Any) -> None:
    #     """tgt can be a point identifier or a set of them. no ygPoint objects."""
    #     self.source["ptid"] = tgt

    def target_list(self, index_only: bool = False) -> list:
        """Always returns a list. Does not recurse."""
        if self.yg_glyph == None:
            return []
        t = self.target
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
        
    def _ptid_to_objects(self):
        _target_list = self.target_list()
        pt_list = []
        for t in _target_list:
            pt_list.append(self.yg_glyph.resolve_point_identifier(t))
        return pt_list
        
    def contains_points(self, p: Any) -> bool:
        """Returns True if point p or all points in list p are targets of this hint."""
        if len(p) == 0:
            return False
        pt_list = self._ptid_to_objects()
        sought_list = []
        if type(p) is list:
            for pp in p:
                sought_list.append(self.yg_glyph.resolve_point_identifier(pp))
        else:
            sought_list = [self.yg_glyph.resolve_point_identifier(p)]
        for p in sought_list:
            if not p in pt_list:
                return False
        return True
    
    def _add_points(self, p: list) -> None:
        """We should already have checked to make sure all points in p are
        untouched and that this hint is shift, align, or interpolate.
        Points in p must be type ygPoint."""
        current_points = self._ptid_to_objects()
        current_points.extend(p)
        labels = []
        for p in current_points:
            labels.append(p.preferred_label())
        if len(labels) > 1:
            self.source["ptid"] = labels

    def add_points(self, p: list) -> None:
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(
                addPointsCommand(self.yg_glyph, self, p)
            )

    def _delete_points(self, p: list) -> None:
        if not len(p):
            return
        pt_list = self._ptid_to_objects()
        original_len = len(pt_list)
        # There's got to be at least one point left for the hint after this operation.
        if len(p) >= len(pt_list):
            return
        for pp in p:
            ppp = self.yg_glyph.resolve_point_identifier(pp)
            try:
                pt_list.remove(ppp)
            except Exception:
                pass
        if len(pt_list) >= original_len:
            return
        labels = []
        for p in pt_list:
            labels.append(p.preferred_label())
        if len(labels) == 1:
            self.source["ptid"] = labels[0]
        elif len(labels) > 1:
            self.source["ptid"] = labels

    def delete_points(self, p: list) -> None:
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(
                deletePointsCommand(self.yg_glyph, self, p)
            )

    @property
    def ref(self) -> Any:
        if "ref" in self.source:
            return self.source["ref"]
        return None

    @property
    def hint_type(self) -> str:
        if "macro" in self.source:
            return "macro"
        if "function" in self.source:
            return "function"
        if "rel" in self.source:
            return self.source["rel"]
        return "anchor"

    @property
    def reversible(self) -> bool:
        no_func = not "function" in self.source
        no_macro = not "macro" in self.source
        has_eligible_ref = "ref" in self.source and (
            type(self.source["ref"]) is not list
        )
        has_eligible_target = "ptid" in self.source and (
            type(self.source["ptid"]) is not list
        )
        return has_eligible_ref and has_eligible_target and no_func and no_macro

    def reverse_hint(self, h: Any) -> None:
        if self.reversible and self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(reverseHintCommand(self.yg_glyph, self))

    def swap_macfunc_points(self, new_name: str, old_name: str) -> None:
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(
                swapMacFuncPointsCommand(self.yg_glyph, self, new_name, old_name)
            )

    def change_hint_color(self, new_color: str) -> None:
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(
                changeDistanceTypeCommand(self.yg_glyph, self, new_color)
            )

    @property
    def rounded(self) -> bool:
        if "round" in self.source:
            if self.source["round"] == False:
                return False
            return True
        else:
            return self.round_is_default()

    # Should make "min" handle a value.
    @property
    def min_dist(self) -> bool:
        try:
            m = self.source["min"]
            return m
        except Exception:
            return self.min_dist_is_default()

    def min_dist_is_default(self) -> bool:
        return hint_type_nums[self.hint_type] == 3

    def toggle_min_dist(self) -> None:
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(toggleMinDistCommand(self.yg_glyph, self))

    def toggle_rounding(self) -> None:
        """Ignores rounding types."""
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(toggleRoundingCommand(self.yg_glyph, self))

    def round_is_default(self) -> bool:
        return hint_type_nums[self.hint_type] in [0, 3]

    def set_round(self, b: bool, update: bool = False) -> None:
        if b != self.round_is_default():
            self.source["round"] = b
        else:
            if "round" in self.source:
                del self.source["round"]
        if update:
            self.hint_changed_signal.emit(self)

    @property
    def cv(self) -> Optional[str]:
        if "pos" in self.source:
            return self.source["pos"]
        if "dist" in self.source:
            return self.source["dist"]
        if "cv" in self.source:
            return self.source["cv"]
        return None

    def required_cv_type(self) -> Optional[str]:
        hnum = hint_type_nums[self.hint_type]
        if hnum == 0:
            return "pos"
        if hnum == 3:
            return "dist"
        return None

    def set_cv(self, new_cv: str) -> None:
        """Does not work for functions and macros. Those must be changed
        through the GUI.

        """
        if self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(changeCVCommand(self.yg_glyph, self, new_cv))

    def _set_cv(self, new_cv: str) -> None:
        """Performs the operation on the hint source without emitting any signal or pushing
        a command onto the undo stack. This is called from changeCVCommand, which does
        those things, and also from ygHintEditor.guess_cv_for_hint, which guesses at a cv
        as part of constructing a hint.
        """
        cvtype = self.required_cv_type()
        if cvtype:
            if new_cv == "None":
                if cvtype in self.source:
                    del self.source[cvtype]
            else:
                self.source[cvtype] = new_cv

    # Placeholder. Need to provide an interface to control this.
    @property
    def cut_in(self) -> bool:
        return True

    def hint_has_changed(self, h: "ygHint") -> None:
        self.hint_changed_signal.emit(h)

    def add_hint(self, hint: "ygHint") -> None:
        """Add a hint. This simply calls add_hint in the glyph"""
        if self.yg_glyph != None:
            self.yg_glyph.add_hint(hint)

    def delete_hints(self, hint_list: list) -> None:
        """Delete a hint from the hint tree. Just calls a function in ygGlyph."""
        if self.yg_glyph != None:
            self.yg_glyph.delete_hints(hint_list)

    def _hint_string(self) -> str:
        result = "Hint target: "
        result += str(self.source["ptid"])
        if "ref" in self.source:
            result += "; ref: "
            result += str(self.source["ref"])
        if "parent" in self.source:
            result += "; parent: "
            result += str(self.source["parent"]["ptid"])
        return result

    def _get_macfunc(self) -> Optional[Union[str, dict]]:
        if "function" in self.source:
            return self.source["function"]
        elif "macro" in self.source:
            return self.source["macro"]
        return None

    @property
    def macfunc_name(self) -> Optional[str]:
        macfunc = self._get_macfunc()
        if type(macfunc) is dict:
            return macfunc["nm"]
        if type(macfunc) is str:
            return macfunc
        return None

    @property
    def macfunc_other_args(self) -> Optional[dict]:
        macfunc = self._get_macfunc()
        other_params = {}
        if type(macfunc) is dict:
            other_params = {
                key: val for key, val in macfunc.items() if not key in ["nm", "code"]
            }
        if len(other_params) > 0:
            return other_params
        return None

    @macfunc_other_args.setter
    def macfunc_other_args(self, d: dict) -> None:
        """d is a dictionary of params for this hint."""
        if len(d) > 1 and self.yg_glyph != None:
            self.yg_glyph.undo_stack.push(
                setMacFuncOtherArgsCommand(self.yg_glyph, self, d)
            )

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


class ygSourceable:
    """Superclass for a number of ygt classes that represent chunks
    of source code.
    """

    def __init__(self, font: ygFont, source: dict) -> None:
        self.data = source
        self.font = font
        self._clean = True

    def clean(self) -> bool:
        return self._clean

    def set_clean(self, c: bool) -> None:
        self._clean = c
        if not self._clean:
            self.font.set_dirty()

    def source(self) -> dict:
        return self.data

    def _save(self, c: dict) -> None:
        pass

    def save(self, c: dict) -> None:
        k = c.keys()
        for kk in k:
            self.data[kk] = c[kk]
        self.set_clean(True)


class ygMasters:
    def __init__(self, yg_font, source):
        self.yg_font = yg_font
        self.source = source
        if not "masters" in self.source:
            self.source["masters"] = {}
        if len(self.source["masters"]) == 0:
            self.build_master_list()

    def create_master(self):
        master_id = random_id("master")
        d = {"name": master_id, "vars": {}}
        at = self.yg_font.axis_tags
        for a in at:
            d["vars"][a] = 0.0
        return master_id, d

    @property
    def keys(self):
        return self.source["masters"].keys()

    @property
    def names(self):
        n_list = []
        k = self.keys
        for kk in k:
            n_list.append(self.source["masters"][kk]["name"])
        return n_list

    def master_by_name(self, n):
        k = self.keys
        for kk in k:
            if self.source["masters"][kk]["name"] == n:
                return kk, self.source["masters"][kk]
        return None

    def master(self, m_id):
        try:
            return m_id, self.source["masters"][m_id]
        except KeyError:
            return self.create_master()

    def add_master(self, id, data):
        self.yg_font.undo_stack.push(addMasterCommand(self.yg_font, id, data))

    def del_by_name(self, name):
        m = self.master_by_name(name)
        if m != None:
            self.del_by_id(m[0])

    def del_by_id(self, id):
        self.yg_font.undo_stack.push(deleteMasterCommand(self.yg_font, id))

    def set_master_name(self, m_id, name):
        """Assumes that a master already exists"""
        self.yg_font.undo_stack.push(setMasterNameCommand(self.yg_font, m_id, name))

    def get_master_name(self, m_id):
        try:
            return self.source["masters"][m_id]["name"]
        except KeyError:
            return m_id

    def get_master_coords(self, master_id):
        axis_vals = self.master(master_id)[1]["vals"]
        axes = self.yg_font.axes
        result = {}
        for a in axes:
            if a.axisTag in axis_vals:
                if axis_vals[a.axisTag] == 0:
                    result[a.axisTag] = a.defaultValue
                elif axis_vals[a.axisTag] > 0:
                    result[a.axisTag] = a.defaultValue + (
                        axis_vals[a.axisTag] * (a.maxValue - a.defaultValue)
                    )
                else:
                    result[a.axisTag] = a.defaultValue - (
                        abs(axis_vals[a.axisTag]) * (a.defaultValue - a.minValue)
                    )
            else:
                result[a.axisTag] = a.defaultValue
        return result

    def get_axis_value(self, m_id, axis):
        try:
            return self.source["masters"][m_id]["vals"][axis]
        except KeyError as e:
            return 0.0

    def set_axis_value(self, m_id, axis, val):
        self.yg_font.undo_stack.push(
            setMasterAxisValueCommand(self.yg_font, m_id, axis, val)
        )

    def del_axis(self, m_id, axis):
        self.yg_font.undo_stack.push(deleteMasterAxisCommand(self.yg_font, m_id, axis))

    def build_master_list(self):
        # Build initial list of masters; install in source
        if not "masters" in self.yg_font.source:
            self.yg_font.source["masters"] = {}
        for a in self.yg_font.axes:
            if a.minValue != a.defaultValue:
                t = str(a.axisTag) + "-min"
                d = {"name": t, "vals": {a.axisTag: -1.0}}
                self.yg_font.source["masters"][t] = d
            if a.maxValue != a.defaultValue:
                t = str(a.axisTag) + "-max"
                d = {"name": t, "vals": {a.axisTag: 1.0}}
                self.yg_font.source["masters"][t] = d

    def __len__(self):
        return len(self.source["masters"])


class ygprep(ygSourceable):
    def __init__(self, font: ygFont, source: dict) -> None:
        self.yg_font = font
        if "prep" in source:
            data = source["prep"]
        else:
            data = {}
        super().__init__(font, data)

    def _save(self, c: dict):
        self.font.source["prep"]["code"] = c["code"]

    def save(self, c: dict) -> None:
        self.yg_font.undo_stack.push(
            saveEditBoxCommand(self.yg_font, self, c, "Save CVT Program Edits")
        )
        # self.data["code"] = c["code"]
        # self._save(c)
        self.set_clean(True)


class ygDefaults(ygSourceable):
    def __init__(self, font: ygFont, source: dict) -> None:
        if "defaults" in source:
            data = source["defaults"]
        else:
            data = {}
        super().__init__(font, data)

    def get_default(self, *args) -> Any:
        if args[0] in self.data:
            return self.data[args[0]]
        return None

    def _set_default(self, dflts: dict) -> None:
        for key, value in dflts.items():
            self.data[key] = value

    def set_default(self, dflts: dict) -> None:
        self.font.undo_stack.push(setDefaultCommand(self.font, self, dflts))

    def del_default(self, k):
        self.font.undo_stack.push(deleteDefaultCommand(self.font, self, k))

    def _save(self, c: dict):
        k = c.keys()
        for kk in k:
            self.font.source["defaults"][kk] = c[kk]

    def save(self, c: dict) -> None:
        self.font.undo_stack.push(
            saveEditBoxCommand(self.font, self, c, "Edit Font Defaults")
        )
        # k = c.keys()
        # for kk in k:
        #    self.data[kk] = c[kk]
        # self._save(c)
        self.set_clean(True)

    def clear_rounding(self):
        try:
            del self.data["round"]
        except KeyError:
            pass
        try:
            del self.data["no-round"]
        except KeyError:
            pass

    def set_rounding_defaults(self, r: dict):
        self.font.undo_stack.push(roundingDefaultCommand(self.font, self, r))

    def set_rounding(self, hint_type: str, b: bool) -> None:
        if b:
            if not "round" in self.data:
                self.data["round"] = []
            self.data["round"].append(hint_type)
        else:
            if not "no-round" in self.data:
                self.data["no-round"] = []
            self.data["no-round"].append(hint_type)

    def rounding_default(self, hint_type):
        return hint_type_nums[hint_type] in [0, 3]

    def rounding_state(self, hint_type):
        if "round" in self.data and hint_type in self.data["round"]:
            return True
        if "no-round" in self.data and hint_type in self.data["no-round"]:
            return False
        return self.rounding_default(hint_type)


class ygCVDeltas(QAbstractTableModel):
    """Provides a view of the 'deltas' section of a CV and
    implements a model to work with the QTableView for CVs
    in the CV editing pane.

    """

    def __init__(self, cvt: "ygcvt", name: str):
        super(ygCVDeltas, self).__init__()
        self.cvt = cvt
        self.name = name
        self._data = None
        self.header_data = ["Size", "Distance"]
        self.dataChanged.connect(self.data_changed)

    def data_changed(self, index_a, index_b):
        c = self.cvt.get_cv(self.name)
        row = index_a.row()
        try:
            from .ygSchema import is_cv_delta_valid

            if not is_cv_delta_valid(c["deltas"][row]):
                self.cvt.yg_font.send_error_message(
                    {
                        "msg": "Illegal value in Control Value Delta "
                        + str(c["deltas"][row]),
                        "mode": "console",
                    }
                )
        except Exception as e:
            print(e)

    def columnCount(self, index):
        return 2

    def rowCount(self, index):
        c = self.cvt.get_cv(self.name)
        try:
            return len(c["deltas"])
        except Exception:
            return 0

    def _mk_row(self, d: dict) -> list:
        return [d["size"], d["distance"]]

    def _store_val(self, index, val):
        c = self.cvt.get_cv(self.name)
        if not "deltas" in c:
            c["deltas"] = []
        if index.row() == len(c["deltas"]):
            # Is trying to append to the list. We'll create a place to put it.
            c["deltas"].append(copy.deepcopy(INITIAL_CV_DELTA))
        try:
            if index.column() == 0:
                c["deltas"][index.row()]["size"] = int(val)
            elif index.column() == 1:
                try:
                    c["deltas"][index.row()]["distance"] = float(val)
                except Exception:
                    c["deltas"][index.row()]["distance"] = str(val)
        except Exception as e:
            print(e)

    def data(self, index, role):
        c = self.cvt.get_cv(self.name)
        arr = []
        if role == Qt.ItemDataRole.DisplayRole:
            if "deltas" in c:
                for d in c["deltas"]:
                    arr.append(self._mk_row(d))
            if len(arr) > 0:
                self._data = arr
                return self._data[index.row()][index.column()]
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole:
            self.cvt.yg_font.undo_stack.push(
                editCVDeltaCommand(self.cvt.yg_font, self, index, value)
            )
            return True
        return False

    def insertRows(self, row, count, parent = QModelIndex()):
        """Actually just appends a new row to the existing structure. We never
        insert multiple rows, and we always append rather than insert.

        """
        self.cvt.yg_font.undo_stack.push(addCVDeltaCommand(self.cvt.yg_font, self))
        return True

    @pyqtSlot()
    def new_row(self):
        self.insertRows(0, 0)

    def deleteRows(self, row, count, parent = QModelIndex()) -> bool:
        c = self.cvt.get_cv(self.name)
        if "deltas" in c and row < len(c["deltas"]): # type: ignore
            self.cvt.yg_font.undo_stack.push(
                deleteCVDeltaCommand(self.cvt.yg_font, self, c, row)
            )
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.header_data[section]


class ygcvt(ygSourceable):
    def __init__(self, top_window: Any, font: ygFont, source: dict) -> None:
        self.yg_font = font
        self.font_source = source
        self.top_window = top_window
        if not "cvt" in self.font_source:
            self.font_source["cvt"] = {}
        self.data = self.font_source["cvt"]
        super().__init__(self.yg_font, source["cvt"])

    def source(self) -> dict:
        return self.font_source["cvt"]

    def _save(self, c: dict) -> None:
        self.font_source["cvt"].clear()
        k = c.keys()
        for kk in k:
            self.font_source["cvt"][kk] = c[kk]

    def save(self, c: dict) -> None:
        self.yg_font.undo_stack.push(
            saveEditBoxCommand(self.yg_font, self, c, "Edit Control Values")
        )
        self.set_clean(True)

    @property
    def keys(self) -> Iterable:
        return self.font_source["cvt"].keys()

    def get_cvs(self, glyph: ygGlyph, filters: dict) -> dict:
        """Get a list of control values filtered to match a particular
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
        keys = self.font_source["cvt"].keys()
        for key in keys:
            entry = self.font_source["cvt"][key]
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

    def get_list(self, glyph: ygGlyph, **filters) -> list:
        """Run get_cvs, then format for presentation in a menu"""
        result = []
        cvt_matches = self.get_cvs(glyph, filters)
        for key in cvt_matches:
            result.append(key)
        return result

    def _closest(self, lst: list, v: Optional[int]) -> int:
        """Helper for get_closest_cv_action"""
        if v == None:
            return 0
        return lst[min(range(len(lst)), key=lambda i: abs(lst[i] - v))]

    def _get_val_from_hint(self, hint: ygHint, axis: str) -> Optional[int]:
        """Helper for get_closest_cv_action and get_closest_cv_name."""
        tgt = hint.yg_glyph.resolve_point_identifier(hint.target)
        ref = hint.ref
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

    def get_closest_cv_name(self, cvlist: list, hint: ygHint) -> str:
        """cvlist is a list of cv names."""
        axis = hint.yg_glyph.axis
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

    def get_closest_cv_action(self, alst: list, hint: ygHint) -> QAction:
        """Return the QAction from alst with value closest
        to the one in the hint.

        alst is a list of QActions; hint is the hint we're operating on.
        The hint must be type 0 (anchor) or 3 (single-point target, can take cv).
        Hint type should have been checked before we got here.
        """
        alst.pop(0)
        alst.pop(0)
        axis = hint.yg_glyph.axis
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

    def get_cv(self, name: str) -> Optional[Union[int, dict]]:
        """Retrieve a control value by name. This will usually be a dict
        rather than just a number.

        """
        if name in self.font_source["cvt"]:
            return self.font_source["cvt"][name]
        return None

    def get_deltas(self, name: str) -> ygCVDeltas:
        return ygCVDeltas(self, name)

    def add_cv(self, name: str, props: Union[int, dict]) -> None:
        self.yg_font.undo_stack.push(addCVCommand(self.yg_font, name, props))

    def set_cv_property(self, cv_name: str, prop_name: str, val: Any) -> None:
        self.yg_font.undo_stack.push(
            setCVPropertyCommand(self.yg_font, cv_name, prop_name, val)
        )

    def del_cv_property(self, cv_name: str, prop_name: str) -> None:
        self.yg_font.undo_stack.push(
            delCVPropertyCommand(self.yg_font, cv_name, prop_name)
        )

    def del_cv(self, name: str) -> None:
        self.yg_font.undo_stack.push(deleteCVCommand(self.yg_font, name))

    def rename(self, old_name: str, new_name: str) -> None:
        self.yg_font.undo_stack.push(renameCVCommand(self.yg_font, old_name, new_name))

    def __len__(self):
        return len(self.font_source["cvt"])


class ygFunctions(ygSourceable):
    def __init__(self, font: ygFont, source: dict) -> None:
        super().__init__(font, source)

    def _save(self, c: dict) -> None:
        try:
            self.font.source["functions"].clear()
        except KeyError:
            pass
        if not "functions" in self.font.source:
            self.font.source["functions"] = {}
        k = c.keys()
        for kk in k:
            self.font.source["functions"][kk] = c[kk]

    def save(self, c: dict) -> None:
        self.font.undo_stack.push(
            saveEditBoxCommand(self.font, self, c, "Edit Functions")
        )
        # self._save(c)
        self.set_clean(True)


class ygMacros(ygSourceable):
    def __init__(self, font: ygFont, source: dict) -> None:
        super().__init__(font, source)

    def _save(self, c: dict) -> None:
        try:
            self.font.source["macros"].clear()
        except KeyError:
            pass
        if not "macros" in self.font.source:
            self.font.source["macros"] = {}
        k = c.keys()
        for kk in k:
            self.font.source["macros"][kk] = c[kk]

    def save(self, c: dict) -> None:
        self.font.undo_stack.push(
            saveEditBoxCommand(self.font, self, c, "Edit Macros")
        )
        # self._save(c)
        self.set_clean(True)


class ygcvar(ygSourceable):
    """This structure is now obsolete. If the more recent way of constructing
    the cvar (through CV properties and masters) is available, this
    structure, if present, will be ignored; if not, it will be used.
    """

    def __init__(self, font: ygFont, source: dict) -> None:
        try:
            data = source["cvar"]
        except Exception as e:
            data = []
        super().__init__(font, data)

    def save(self, c: Any) -> None:
        self.data = c
        self.font.source["cvar"] = c
        self.set_clean(True)


class ygGlyphProperties(ygSourceable):
    def __init__(self, glyph: ygGlyph) -> None:
        super().__init__(glyph.yg_font, glyph.gsource)
        self.yg_glyph = glyph

    def add_property(self, k: str, v: Any) -> None:
        self.yg_glyph.undo_stack.push(glyphAddPropertyCommand(self.yg_glyph, k, v))
        self.set_clean(False)

    def get_property(self, k: str) -> Any:
        try:
            return self.yg_glyph.gsource["props"][k]
        except KeyError:
            return None

    def set_clean(self, c: bool) -> None:
        if not c:
            self.yg_glyph.set_dirty()

    def source(self) -> dict:
        if "props" in self.yg_glyph.gsource:
            return self.yg_glyph.gsource["props"]
        return {}

    def del_property(self, k: str) -> None:
        try:
            self.yg_glyph.undo_stack.push(glyphDeletePropertyCommand(self.yg_glyph, k))
            self.set_clean(False)
        except Exception as e:
            pass

    def save(self, c: Any) -> None:
        self.yg_glyph.undo_stack.push(replaceGlyphPropsCommand(self.yg_glyph, c))
        self.set_clean(False)


class ygGlyphNames(ygSourceable):
    """The collection of glyph and set names."""

    def __init__(self, glyph: ygGlyph) -> None:
        self.yg_glyph = glyph
        super().__init__(glyph.yg_font, self.yg_glyph.gsource)
        self.inverse_dict: dict = {}
        self.update_point_names()

    def update_inverse_dict(self) -> dict:
        if "names" in self.yg_glyph.gsource:
            new_dict = {}
            original_dict = self.yg_glyph.gsource["names"]
            for key, value in original_dict.items():
                if (type(value) is str or type(value) is int) and not value in new_dict:
                    new_dict[value] = key
            return new_dict
        return {}

    def add(self, pt: list, name: str) -> None:
        self.yg_glyph.undo_stack.push(addPointSetNameCommand(self.yg_glyph, pt, name))
        self.set_clean(False)

    def set_clean(self, b: bool) -> None:
        if not b:
            self.yg_glyph.set_dirty()

    def get_point_name(self, yg_point: ygPoint) -> str:
        try:
            return self.inverse_dict[yg_point.index]
        except Exception:
            pass
        try:
            return self.inverse_dict[yg_point.coord]
        except Exception:
            return ""

    def update_point_names(self) -> None:
        self.inverse_dict = self.update_inverse_dict()
        for p in self.yg_glyph.point_list:
            p.preferred_name = self.get_point_name(p)

    def has_name(self, n: str) -> bool:
        if "names" in self.yg_glyph.gsource:
            return n in self.yg_glyph.gsource["names"]
        return False

    def source(self) -> dict:
        if "names" in self.yg_glyph.gsource:
            return self.yg_glyph.gsource["names"]
        return {}

    def get(self, n: str) -> Any:
        if self.has_name(n):
            return self.yg_glyph.gsource["names"][n]

    def save(self, c: Any) -> None:
        self.yg_glyph.undo_stack.push(replacePointNamesCommand(self.yg_glyph, c))
        self.set_clean(False)


class ygHintSorter:
    """Will sort a (flat) list of hints into an order where hints with touched
    points occur earlier in the list than hints with refs pointing to those
    touched points.

    """

    def __init__(self, list: list) -> None:
        self.list = list

    def sort(self) -> list:
        sortable = []
        for l in self.list:
            sortable.append(ygHintSource(l))
        ll = sorted(sortable)
        result = []
        for l in ll:
            result.append(l._source)
        return result


class ygPointSorter:
    """Will sort a list of points into left-to-right or up-to-down order,
    depending on the current axis.

    """

    def __init__(self, axis: str) -> None:
        self.axis = axis

    def _ptcoords(self, p: ygPoint) -> int:
        if self.axis == "y":
            return p.font_x
        else:
            return p.font_y

    def sort(self, pt_list: list) -> None:
        pt_list.sort(key=self._ptcoords)
