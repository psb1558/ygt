from typing import Any, TypeVar, Union, Optional, List, Dict, Callable, overload, Tuple
import sys
import numpy
import uuid
import copy
from .macfuncDialog import macfuncDialog
from .makeCVDialog import makeCVDialog
from .ygModel import (
    ygFont,
    ygSet,
    ygParams,
    ygPoint,
    ygPointSorter,
    ygHint,
    hint_type_nums,
    ygCaller,
    ygFunction,
    ygMacro,
    ygGlyph,
    unicode_cat_names,
)
from .ygStems import stemFinder
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QSizeF,
    QRectF,
    pyqtSignal,
    QLine,
    QLineF,
    pyqtSlot,
    QObject,
)
from PyQt6.QtGui import (
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QPolygonF,
    QAction,
    QPainter,
    QPalette,
    QImage,
    QPixmap,
    QBitmap,
)
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QMenu,
    QLabel,
    QDialog,
    QInputDialog,
    QLineEdit,
    QGraphicsProxyWidget,
    QStyleOptionGraphicsItem,
    QHBoxLayout,
)
from fontTools.pens.basePen import BasePen  # type: ignore
from fontTools.pens.freetypePen import FreeTypePen
from .ygPreferences import ygPreferences
# from .freetypeFont import freetypeFont


HINT_ARROW_WIDTH = 3
HINT_ANCHOR_WIDTH = 3
HINT_LINK_WIDTH = 1
HINT_ARROWHEAD_WIDTH = 2

HINT_ANCHOR_COLOR = QColor(255, 0, 255, 128)
HINT_ANCHOR_DARK = QColor(255, 0, 255, 192)
HINT_ANCHOR_SELECT_COLOR = QColor(175, 0, 175, 128)
HINT_ANCHOR_SELECT_DARK = QColor(192, 0, 192, 192)

HINT_STEM_COLOR = QColor(255, 0, 0, 128)
HINT_STEM_DARK = QColor(255, 128, 176, 192)
HINT_STEM_SELECT_COLOR = QColor(175, 0, 0, 128)
HINT_STEM_SELECT_DARK = QColor(191, 0, 74, 192)

HINT_SHIFT_COLOR = QColor(100, 100, 255, 128)
HINT_SHIFT_DARK = QColor(96, 159, 191, 192)
HINT_SHIFT_SELECT_COLOR = QColor(0, 0, 150, 128)
HINT_SHIFT_SELECT_DARK = QColor(51, 186, 255, 192)

HINT_ALIGN_COLOR = QColor(0, 255, 0, 128)
HINT_ALIGN_DARK = QColor(191, 255, 209, 192)
HINT_ALIGN_SELECT_COLOR = QColor(0, 205, 0, 128)
HINT_ALIGN_SELECT_DARK = QColor(96, 191, 122, 192)

HINT_FUNC_COLOR = QColor(0, 205, 0, 128)
HINT_FUNC_DARK = QColor(173, 204, 181, 192)
HINT_FUNC_SELECT_COLOR = QColor(0, 105, 0, 128)
HINT_FUNC_SELECT_DARK = QColor(38, 191, 74, 192)

HINT_INTERPOLATE_COLOR = QColor(255, 127, 0, 128)
HINT_INTERPOLATE_DARK = QColor(212, 187, 106, 192)
HINT_INTERPOLATE_SELECT_COLOR = QColor(215, 87, 0, 128)
HINT_INTERPOLATE_SELECT_DARK = QColor(255, 195, 0, 192)

PTFILL_COLOR = QColor("white")
PTFILL_DARK = QColor("black")
PTFILL_SELECT_COLOR = QColor(100, 105, 108, 192)
PTFILL_SELECT_DARK = QColor(137, 207, 240)
PTFILL_TOUCH_COLOR = QColor(255, 182, 193, 192)
PTFILL_TOUCH_DARK = QColor(170, 51, 106, 192)
PTFILL_TOUCH_SELECT_COLOR = QColor(138, 41, 86, 128)
PTFILL_TOUCH_SELECT_DARK = QColor(255, 233, 236, 128)

POINT_ONCURVE_OUTLINE = QColor("red")
POINT_OFFCURVE_OUTLINE = QColor(127, 127, 255, 255)

POINT_OFFCURVE_FILL = PTFILL_COLOR
POINT_ONCURVE_FILL = PTFILL_COLOR
#POINT_OFFCURVE_SELECTED = QColor(127, 127, 255, 255)
#POINT_ONCURVE_SELECTED = QColor(127, 127, 255, 255)
POINT_OFFCURVE_SELECTED = PTFILL_SELECT_COLOR
POINT_ONCURVE_SELECTED = PTFILL_SELECT_COLOR
POINT_TOUCHED = PTFILL_TOUCH_COLOR
POINT_TOUCHED_SELECTED = PTFILL_TOUCH_SELECT_COLOR

PREVIEW_BASE_COLOR = QColor(64, 33, 31, 255)
POINT_OUTLINE_WIDTH = 1
POINT_ANCHORED_OUTLINE_WIDTH = 3
CHAR_OUTLINE_WIDTH = 1
FUNC_BORDER_WIDTH = 2
GLYPH_WIDGET_MARGIN = 50
POINT_ONCURVE_DIA = 8
POINT_OFFCURVE_DIA = 6
HINT_BUTTON_DIA = 6

PTFILL_ANCHOR_TOUCH_COLOR = QColor(255, 233, 236, 128)
PTFILL_ANCHOR_TOUCH_DARK = QColor(170, 51, 106, 192)
PTFILL_ANCHOR_TOUCH_SELECT_COLOR = QColor(255, 233, 236, 128)
PTFILL_ANCHOR_TOUCH_SELECT_DARK = QColor(170, 51, 106, 192)

HINT_COLOR = {}

_HINT_COLOR = {
    "anchor": HINT_ANCHOR_COLOR,
    "align": HINT_ALIGN_COLOR,
    "shift": HINT_SHIFT_COLOR,
    "interpolate": HINT_INTERPOLATE_COLOR,
    "stem": HINT_STEM_COLOR,
    "whitedist": HINT_STEM_COLOR,
    "blackdist": HINT_STEM_COLOR,
    "graydist": HINT_STEM_COLOR,
    "move": HINT_STEM_COLOR,
    "macro": HINT_FUNC_COLOR,
    "function": HINT_FUNC_COLOR,
}

_HINT_DARK = {
    "anchor": HINT_ANCHOR_DARK,
    "align": HINT_ALIGN_DARK,
    "shift": HINT_SHIFT_DARK,
    "interpolate": HINT_INTERPOLATE_DARK,
    "stem": HINT_STEM_DARK,
    "whitedist": HINT_STEM_DARK,
    "blackdist": HINT_STEM_DARK,
    "graydist": HINT_STEM_DARK,
    "move": HINT_STEM_DARK,
    "macro": HINT_FUNC_DARK,
    "function": HINT_FUNC_DARK,
}

SELECTED_HINT_COLOR = {}

_SELECTED_HINT_COLOR = {
    "anchor": HINT_ANCHOR_SELECT_COLOR,
    "align": HINT_ALIGN_SELECT_COLOR,
    "shift": HINT_SHIFT_SELECT_COLOR,
    "interpolate": HINT_INTERPOLATE_SELECT_COLOR,
    "stem": HINT_STEM_SELECT_COLOR,
    "whitedist": HINT_STEM_SELECT_COLOR,
    "blackdist": HINT_STEM_SELECT_COLOR,
    "graydist": HINT_STEM_SELECT_COLOR,
    "move": HINT_STEM_SELECT_COLOR,
    "macro": HINT_FUNC_SELECT_COLOR,
    "function": HINT_FUNC_SELECT_COLOR,
}

_SELECTED_HINT_DARK = {
    "anchor": HINT_ANCHOR_SELECT_DARK,
    "align": HINT_ALIGN_SELECT_DARK,
    "shift": HINT_SHIFT_SELECT_DARK,
    "interpolate": HINT_INTERPOLATE_SELECT_DARK,
    "stem": HINT_STEM_SELECT_DARK,
    "whitedist": HINT_STEM_SELECT_DARK,
    "blackdist": HINT_STEM_SELECT_DARK,
    "graydist": HINT_STEM_SELECT_DARK,
    "move": HINT_STEM_SELECT_DARK,
    "macro": HINT_FUNC_SELECT_DARK,
    "function": HINT_FUNC_SELECT_DARK,
}

# Classes in this file:

# QtPen(BasePen): copied from fontTools so we could drop a reference to Qt5.
# ygSelectable: inherited by objects that can be selected.
# ygHintView(QGraphicsItem, ygSelectable): Interface with a hint (ygModel.ygHint)
# ygGraphicalHintComponent: Superclass for a visible piece of a hint.
# ygArrowHead(QGraphicsPolygonItem, ygGraphicalHintComponent):
#                    Arrowhead component of a visible hint.
# ygBorderLine(QGraphicsLineItem, ygGraphicalHintComponent):
#                    Borderline around certain hints.
# ygHintStem(QGraphicsPathItem, ygGraphicalHintComponent):
#                    Stem of a visible hint
# ygHintButton(QGraphicsEllipseItem, ygGraphicalHintComponent):
#                    A button to display in the middle of a hint stem. Makes it
#                    easier to select with mouse.
# ygPointMarker(QGraphicsEllipseItem, ygGraphicalHintComponent):
#                    Thickens and adds color to a point.
# ygPointable: superclass for objects that an arrow can point at.
# ygPointCollectionView(QGraphicsItem, ygGraphicalHintComponent, ygPointable):
#                    A collection of points appears in a box.
# ygSetView(ygPointCollectionView):
#                    Visible representation of a set (of points).
# ygSelection(QObject): Keeps track of selected objects.
# ygPointView(QGraphicsEllipseItem, ygSelectable, ygPointable):
#                    Visual representation of a point.
# SelectionRect(QGraphicsRectItem): For making marquee selections.
# ygGlyphScene(QGraphicsScene): Visual representation of a glyph (with points,
#                    ygHintView objects, etc.)
# ygGlyphView(QGraphicsView): Container for ygGlyphScene; receives (some) events


class QtPen(BasePen):
    """Copied from fontTools so we can get rid of the reference to Qt5
    (we're using Qt6). The fontTools library was issued under the MIT license:

    MIT License

    Copyright (c) 2017 Just van Rossum

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """

    def __init__(self, glyphSet, path=None):
        BasePen.__init__(self, glyphSet)
        if path is None:
            # An import dropped here: otherwise this class is the same as in fontTools.
            path = QPainterPath()
        self.path = path

    def _moveTo(self, p):
        self.path.moveTo(*p)

    def _lineTo(self, p):
        self.path.lineTo(*p)

    def _curveToOne(self, p1, p2, p3):
        self.path.cubicTo(*p1, *p2, *p3)

    def _qCurveToOne(self, p1, p2):
        self.path.quadTo(*p1, *p2)

    def _closePath(self):
        self.path.closeSubpath()


class ygSelectable:
    """Mixin superclass for graphical objects that can be selected."""

    def _prepare_graphics(self) -> None:
        pass

    def update(self) -> None:
        pass

    def selected(self) -> bool:
        pass

    def yg_select(self) -> None:
        pass

    def yg_unselect(self) -> None:
        pass


class ygHintView(QGraphicsItem, ygSelectable):
    """Wrapper for a ygModel.ygHint object."""

    def __init__(self, *args, **kwargs) -> None:
        """Constructor for ygHintView

        Parameters:
        args[0] (ygGlyphScene): The scene that owns this. We can't always
        call scene() because we sometimes need that reference before this
        is added to the scene.

        args[1] (ygModel.ygHint): a hint from the ygModel

        args[2]: either a component of the graphical hint or a list of them.

        """
        super().__init__()
        self._selected = False
        self.yg_glyph_scene = args[0]
        self.yg_hint = args[1]
        self.label: Optional[QLabel] = None
        self.label_proxy = None
        self.description = self._set_description()
        if len(args) >= 3:
            # graphical_hint may arrive as an irregularly nested list.
            # flatten it into a simple list
            self.graphical_hint = list(self._traverse(args[2]))
            for g in self.graphical_hint:
                g.setParentItem(self)

    def _set_description(self) -> str:
        result = self.yg_hint.hint_type
        if hasattr(self.yg_hint, "cvt"):
            result += " (" + str(self.yg_hint.cv) + ")"
        # Tooltip not yet. By default, the tooltip appears when the mouse is
        # anywhere in a widget's bounding rect. For hints that is not helpful.
        # *** There is a way to change this behavior: figure it out later.
        # self.setToolTip(result)
        return result

    def _set_name(self, name: str) -> None:
        self.yg_hint.name = name
        self.label = QLabel()
        self.label.setStyleSheet("QLabel {background-color: transparent; color: gray;}")
        self.label.setText(name)
        self.label_proxy = self.yg_glyph_scene.addWidget(self.label)
        rect = self.boundingRect()
        self.label.move(
            round(rect.topLeft().x()), round(rect.topLeft().y() - self.label.height())
        )

    def _remove_labels(self) -> None:
        if self.label_proxy:
            self.yg_glyph_scene.removeItem(self.label_proxy)
        for g in self.graphical_hint:
            if hasattr(g, "_remove_labels"):
                g._remove_labels()

    # Adapted from https://stackoverflow.com/questions/6340351/iterating-through-list-of-list-in-python
    # Presumed public domain.
    def _traverse(self, o) -> Any:
        if isinstance(o, list):
            for value in o:
                for subvalue in self._traverse(value):
                    yield subvalue
        else:
            yield o

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """Got to be here, but it doesn't have to do anything."""
        pass

    def boundingRect(self) -> QRectF:
        if len(self.graphical_hint) >= 1:
            resultRect = None
            for g in self.graphical_hint:
                if resultRect == None:
                    resultRect = g.boundingRect()
                else:
                    resultRect = g.boundingRect().united(resultRect)
            return resultRect
        else:
            return None  # This shouldn't happen. Behavior undefined if it does.

    def contains(self, pt: QPointF) -> bool:
        if len(self.graphical_hint) >= 1:
            for g in self.graphical_hint:
                if g.contains(pt):
                    return True
        return False
    
    def mouse_over_point(self, pt: QPointF) -> "ygPointMarker":
        """In ygHintView. Returns a ygPointMarker."""
        if len(self.graphical_hint) >= 1:
            for g in self.graphical_hint:
                if type(g) is ygPointMarker and g.contains(pt):
                    return g
        return None

    #def get_scene(self) -> "ygGlyphScene":
    #    return self.yg_glyph_scene

    def _target_list(self) -> list:
        """Returns a list of target points for this hint."""
        mpt = self.yg_glyph_scene.resolve_point_identifier(self.yg_hint.target)
        mypoints = []
        if type(mpt) is ygSet:
            for p in mpt.point_list:
                mypoints.append(p)
        elif type(mpt) is ygParams:
            mypoints.extend(self._get_macfunc_targets(mpt))
        elif type(mpt) is not list:
            mypoints.append(self.yg_glyph_scene.resolve_point_identifier(mpt))
        return mypoints

    def _update_touches(self) -> None:
        self._remove_touches()
        self._touch_all_points()

    def _get_macfunc_targets(self, p: ygParams) -> list:
        """p should be the point_dict from a ygParams object. Survey all the
        point params in a macro or function definition and touch any marked
        as "target."

        """
        macfunc_name = self.yg_hint.name
        plist = []
        if macfunc_name != None:
            try:
                if self.yg_hint.hint_type == "macro":
                    macfunc = self.yg_glyph_scene.yg_glyph.yg_font.macros[macfunc_name]
                elif self.yg_hint.hint_type == "function":
                    macfunc = self.yg_glyph_scene.yg_glyph.yg_font.functions[
                        macfunc_name
                    ]
                else:
                    return plist
                k = p.point_dict.keys()
                for kk in k:
                    if (
                        kk in macfunc
                        and "subtype" in macfunc[kk]
                        and macfunc[kk]["subtype"] == "target"
                    ):
                        plist.append(p.point_dict[kk])
            except Exception as e:
                print(e)
        return plist

    def _touch_untouch(self, point_list: list, touch: bool) -> None:
        """Touch or untouch the points in point_list. When touch=False,
        remove self from the owners list, and mark the point as untouched
        only if there are no other owners.

        """
        ptindex = self.yg_glyph_scene.yg_point_view_index
        for p in point_list:
            if type(p) is ygSet:
                self._touch_untouch(p.point_list, touch)
            elif type(p) is ygParams:
                self._touch_untouch(self._get_macfunc_targets(p), touch)
            else:
                pp = ptindex[p.id]
                if touch:
                    try:
                        ptindex[p.id].touched = True
                        if ptindex[p.id].changed:
                            ptindex[p.id]._prepare_graphics()
                        ptindex[p.id].owners.append(self)
                    except Exception:
                        pass
                else:
                    try:
                        ptindex[p.id].owners.remove(self)
                        if len(ptindex[p.id].owners) == 0:
                            ptindex[p.id].touched = False
                            if ptindex[p.id].changed:
                                ptindex[p.id]._prepare_graphics()
                    except Exception as e:
                        #print(str(e.args))
                        #print(str(e))
                        pass

    def _touch_all_points(self) -> None:
        """Mark each point affected by this hint as 'touched,' and record
        this hint as an owner in its 'owners" list. To orient new hints
        correctly, we need to be accurate about which points are touched.

        """
        self._touch_untouch(self._target_list(), True)

    def _remove_touches(self) -> None:
        """Remove reference to this hint from the "owners" list for each
        point, and if the owner's list is empty afterwards, mark the
        point as untouched.

        """
        self._touch_untouch(self._target_list(), False)

    def _process_click_on_hint(self, obj, with_shift: bool, is_left: bool) -> None:
        if is_left:
            if with_shift:
                self.yg_glyph_scene.yg_selection._toggle_object(self)
            else:
                self.yg_glyph_scene.yg_selection._add_object(self, False)

    def _prepare_graphics(self) -> None:
        # In ygHintView
        if len(self.graphical_hint) >= 1:
            for c in self.graphical_hint:
                if isinstance(c, ygGraphicalHintComponent):
                    c._prepare_graphics(
                        is_selected=self._selected,
                        hint_type=self.yg_hint.hint_type,
                    )

    def selected(self) -> bool:
        return self._selected

    def update(self, rect: QRectF = None) -> None:  # type: ignore
        if len(self.graphical_hint) >= 1:
            for c in self.graphical_hint:
                c.update()
        super().update(rect=self.boundingRect())

    def yg_select(self) -> None:
        self._selected = True
        self._prepare_graphics()
        self.update()

    def yg_unselect(self) -> None:
        self._selected = False
        self._prepare_graphics()
        self.update()


class ygGraphicalHintComponent:
    def _prepare_graphics(self, **kwargs) -> None:
        ...


class ygArrowHead(QGraphicsPolygonItem, ygGraphicalHintComponent):
    """Arrowhead to mount on the end of a line

    A reference should be kept only in ygHintView.

    This is separate from the line (ygHintStem) it goes with, chiefly so that
    it can be clickable.
    """

    def __init__(self, tip, direction: str, hint_type: str, id, parent=None) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.direction = direction
        self.hint_type = hint_type
        self.parent = parent
        self.id = id
        tp = QPointF(0, 0)
        self.tip = tip
        qpolygon = QPolygonF([tp, tp, tp, tp])
        if direction == "down":
            self.tip = QPointF(8, 8)
            pt1 = QPointF(self.tip.x() - 6, self.tip.y() - 8)
            pt2 = QPointF(self.tip.x() + 6, self.tip.y() - 8)
            qpolygon = QPolygonF([self.tip, pt1, pt2, self.tip])  # 8,8
        elif direction == "up":
            self.tip = QPointF(8, 0)
            pt1 = QPointF(self.tip.x() - 6, self.tip.y() + 8)
            pt2 = QPointF(self.tip.x() + 6, self.tip.y() + 8)
            qpolygon = QPolygonF([self.tip, pt1, pt2, self.tip])  # 8,0
        elif direction == "left":
            self.tip = QPointF(0, 8)
            pt1 = QPointF(self.tip.x() + 8, self.tip.y() + 6)
            pt2 = QPointF(self.tip.x() + 8, self.tip.y() - 6)
            qpolygon = QPolygonF([self.tip, pt1, pt2, self.tip])  # 0,8
        elif direction == "right":
            self.tip = QPointF(8, 8)
            pt1 = QPointF(self.tip.x() - 8, self.tip.y() - 6)
            pt2 = QPointF(self.tip.x() - 8, self.tip.y() + 6)
            qpolygon = QPolygonF([pt1, pt2, self.tip, pt1])  # 8,8
        self.setPolygon(qpolygon)
        self._prepare_graphics(is_selected=False, hint_type=self.hint_type)

    def _prepare_graphics(self, **kwargs):
        # For ygArrowHead
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        if is_selected:
            pen_color = SELECTED_HINT_COLOR[hint_type]
        else:
            pen_color = HINT_COLOR[hint_type]
        pen = QPen(pen_color)
        pen.setWidth(HINT_ARROWHEAD_WIDTH)
        self.setPen(pen)

    def setPos(self, qpf):
        # These little offsets were made by experimentation.  But see if they
        # can be abstracted somehow.
        if self.direction == "down":
            nqp = QPointF(qpf.x() - 8, qpf.y() - 6)
        elif self.direction == "up":
            nqp = QPointF(qpf.x() - 8, qpf.y() - 2)
        elif self.direction == "left":
            nqp = QPointF(qpf.x() - 4, qpf.y() - 8)
        else:
            nqp = QPointF(qpf.x() - 6, qpf.y() - 8)
        super().setPos(nqp)

    def mousePressEvent(self, event):
        # In ygArrowHead
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)


class ygBorderLine(QGraphicsLineItem, ygGraphicalHintComponent):
    def __init__(self, line, hint_type):
        super().__init__()
        self.hint_type = hint_type
        self.line = line
        self.setLine(self.line)

    def _prepare_graphics(self, **kwargs):
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        if is_selected:
            pen_color = SELECTED_HINT_COLOR[hint_type]
        else:
            pen_color = HINT_COLOR[hint_type]
        pen = QPen(pen_color)
        pen.setWidth(FUNC_BORDER_WIDTH)
        pen.setDashPattern([1, 2])
        brush = QBrush(pen_color)
        self.setPen(pen)

    def mousePressEvent(self, event):
        # in yBorderLine
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)


class ygHintStem(QGraphicsPathItem, ygGraphicalHintComponent):
    """Line for connecting related points

    The connecting line with arrow represents a hint. There are different kinds,
    which will be represented by different colors.

    params:

    p1 (ygPointable): point for one end of the stem.

    p2 (ygPointable): point for the other end of the stem.

    axis: Not sure if this is ever used.

    hint_type (str): The type of this hint.

    id: A unique id for this object.

    parent: The parent of this item.
    """

    def __init__(
        self,
        p1: "ygPointable",
        p2: "ygPointable",
        axis: str,
        hint_type: str,
        id: Any = None,
        parent=None,
    ) -> None:
        # "axis" param not used. Get rid of it.
        super().__init__()
        #
        # This class looks very messy. Clean it up!
        #
        # p1 and p2 must be ygPointable objects (ygPointView, ygPointCollectionView).
        #
        # p1 is the beginning of the line; p2 is the end (where we will put
        # the arrowhead). axis is 0 for y, 1 for x
        # start by figuring out the rectangle that will contain this line.
        #
        self.axis = axis
        # id setup not needed:
        if id:
            self.id = id
        else:
            self.id = uuid.uuid1()
        # parent setup not needed
        self.parent = parent
        self._center_point = QPointF(0, 0)
        self.setCursor(Qt.CursorShape.CrossCursor)
        begin_a = p1.attachment_point(p2.center_point)
        begin_x = begin_a.x()
        begin_y = begin_a.y()
        end_a = p2.attachment_point(begin_a)
        end_x = end_a.x()
        end_y = end_a.y()
        xdistance = abs(begin_x - end_x)
        ydistance = abs(begin_y - end_y)
        self.hint_type = hint_type
        # Shouldn't need a ref to the arrowhead here, but only in ygHintView.
        self.arrowhead = None
        try:
            box_ratio = xdistance / ydistance
        except ZeroDivisionError:
            box_ratio = 0
        # Generate a keyword to describe the shape of the box.
        if xdistance == 0 and ydistance == 0:
            self._shape = "invisible"
            self.arrow_axis = None
        elif xdistance < 10:
            self._shape = "y only"
            self.arrow_axis = "y"
        elif ydistance < 10:
            self._shape = "x only"
            self.arrow_axis = "x"
        elif box_ratio < 0.3333:
            self._shape = "tall"
            self.arrow_axis = "y"
        elif box_ratio > 3:
            self._shape = "flat"
            self.arrow_axis = "x"
        elif ydistance > xdistance:
            self._shape = "tallish"
            self.arrow_axis = "y"
        else:
            self._shape = "flattish"
            self.arrow_axis = "x"
        self.arrowhead_direction = None
        # Should these direction words be "positive" and "negative"?
        if self.arrow_axis == "x":
            if begin_x < end_x:
                self.arrowhead_direction = "right"
            if begin_x > end_x:
                self.arrowhead_direction = "left"
        if self.arrow_axis == "y":
            if begin_y < end_y:
                self.arrowhead_direction = "down"
            if begin_y > end_y:
                self.arrowhead_direction = "up"
        # These little adjustments are for getting the line aligned exactly
        # with the center of the points. See if they can be abstracted, and
        # change with the point diameter.
        self.leftadjust = [12, 4]
        self.rightadjust = [-4, 4]
        self.topadjust = [4, 12]
        self.bottomadjust = [4, -4]
        if self.arrow_axis == "x":
            if min(begin_x, end_x) == begin_x:
                self.lineBegin = self._adjustPoint(self.leftadjust, begin_x, begin_y)
                self.lineEnd = self._adjustPoint(self.rightadjust, end_x, end_y)
                leftPoint = self.lineBegin
                rightPoint = self.lineEnd
            else:
                self.lineEnd = self._adjustPoint(self.leftadjust, end_x, end_y)
                self.lineBegin = self._adjustPoint(self.rightadjust, begin_x, begin_y)
                rightPoint = self.lineBegin
                leftPoint = self.lineEnd
        else:
            if min(begin_y, end_y) == begin_y:
                self.lineBegin = self._adjustPoint(self.topadjust, begin_x, begin_y)
                self.lineEnd = self._adjustPoint(self.bottomadjust, end_x, end_y)
                topPoint = self.lineBegin
                bottomPoint = self.lineEnd
            else:
                self.lineEnd = self._adjustPoint(self.topadjust, end_x, end_y)
                self.lineBegin = self._adjustPoint(self.bottomadjust, begin_x, begin_y)
                bottomPoint = self.lineBegin
                topPoint = self.lineEnd
        # The "0.25" that governs the length of the handles for the cubic drawing
        # needs to be abstracted, so it can change with the _shape of the box.
        partial_y_distance = ydistance * 0.25
        partial_x_distance = xdistance * 0.25
        if self._shape == "invisible":
            path = QPainterPath()
        elif self._shape in ["tall", "tallish", "y only"]:
            top_point_x = topPoint.x()
            bottom_point_x = bottomPoint.x()
            if self._shape == "y only":
                flat_adjust = round(ydistance * 0.05)
                if flat_adjust > 15:
                    flat_adjust = 15
                top_point_x -= flat_adjust
                bottom_point_x -= flat_adjust
            handle1 = QPointF(top_point_x, topPoint.y() + partial_y_distance)
            handle2 = QPointF(bottom_point_x, bottomPoint.y() - partial_y_distance)
            self._center_point = self.find_mid_point(handle1, handle2)
            if self.arrowhead_direction == "up":
                path = QPainterPath(bottomPoint)
                path.quadTo(handle2, self._center_point)
                path.quadTo(handle1, topPoint)
            else:
                path = QPainterPath(topPoint)
                path.quadTo(handle1, self._center_point)
                path.quadTo(handle2, bottomPoint)
        elif self._shape in ["flat", "flattish", "x only"]:
            left_point_y = leftPoint.y()
            right_point_y = rightPoint.y()
            if self._shape == "x only":
                flat_adjust = round(xdistance * 0.05)
                if flat_adjust > 15:
                    flat_adjust = 15
                left_point_y += flat_adjust
                right_point_y += flat_adjust
            handle1 = QPointF(leftPoint.x() + partial_x_distance, left_point_y)
            handle2 = QPointF(rightPoint.x() - partial_x_distance, right_point_y)
            self._center_point = self.find_mid_point(handle1, handle2)
            if self.arrowhead_direction == "left":
                path = QPainterPath(rightPoint)
                path.quadTo(handle2, self._center_point)
                path.quadTo(handle1, leftPoint)
            else:
                path = QPainterPath(leftPoint)
                path.quadTo(handle1, self._center_point)
                path.quadTo(handle2, rightPoint)
        else:
            # This has never happened.
            print("What's going on?")
        self.setPath(path)
        self._prepare_graphics(is_selected=False, hint_type=self.hint_type)

    def _prepare_graphics(self, **kwargs) -> None:
        # For ygHintStem
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        pen = QPen()
        pen.setWidth(HINT_ARROW_WIDTH)
        if is_selected:
            pen.setColor(SELECTED_HINT_COLOR[hint_type])
        else:
            pen.setColor(HINT_COLOR[hint_type])
        if hint_type == "whitedist":
            pen.setDashPattern([2, 2])
        if hint_type == "graydist":
            pen.setDashPattern([4, 2])
        self.setPen(pen)

    def find_mid_point(self, pt1: QPointF, pt2: QPointF) -> QPointF:
        """For placing the point in the middle of a quadratic curve: get the
        mid-point on a line between two points.
        """
        l = QLineF(pt1, pt2)
        return l.center()

    def center_point(self):
        return self._center_point

    def _adjustPoint(self, adjustment: list, x: int, y: int) -> QPointF:
        return QPointF(x + adjustment[0], y + adjustment[1])

    def endPoint(self) -> QPointF:
        return self.lineEnd

    def mousePressEvent(self, event) -> None:
        # In ygHintStem
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)  # type: ignore


class ygHintButton(QGraphicsEllipseItem, ygGraphicalHintComponent):
    """A button to display mid-stem, to make an easy target for a mouse."""

    def __init__(self, yg_glyph_scene: "ygGlyphScene", location: QPoint, hint: ygHint) -> None:
        """yg_glyph_scene: a ygGlyphScene object
        location: QPoint
        hint: ygModel.ygHint
        """
        self.yg_glyph_scene = yg_glyph_scene
        self.diameter = HINT_BUTTON_DIA + 2
        loc_offset = self.diameter - (self.diameter / 2)
        self.location = QPointF(location.x() - loc_offset, location.y() - loc_offset)
        self.yg_hint = hint
        super().__init__(QRectF(self.location, QSizeF(self.diameter, self.diameter)))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._prepare_graphics(is_selected=False, hint_type=self.yg_hint.hint_type)

    def _prepare_graphics(self, **kwargs) -> None:
        # for ygHintButton
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        pen = QPen()
        brush = QBrush()
        pen.setWidth(HINT_ANCHOR_WIDTH)
        if is_selected:
            color = SELECTED_HINT_COLOR[hint_type]
        else:
            color = HINT_COLOR[hint_type]
        brush.setColor(color)
        pen.setColor(color)
        self.setPen(pen)
        self.setBrush(brush)

    def mousePressEvent(self, event) -> None:
        # In ygHintButton
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)  # type: ignore


class ygPointMarker(QGraphicsEllipseItem, ygGraphicalHintComponent):
    """pt has got to be a ygPointView."""

    def __init__(
        self,
        yg_glyph_scene: "ygGlyphScene",
        pt: "ygPointView",
        hint_type: str,
        name: str = None,
        id=None,
        parent=None,
    ):
        self.pt = pt
        self.name = name
        self.label: Optional[QLabel] = None
        # This is "placed" when user has associated it with a point.
        self._x = self.pt.glocation.x() - 1
        self._y = self.pt.glocation.y() - 1
        self.glocation = QPointF(self._x, self._y)
        if self.pt.yg_point.on_curve:
            self.diameter = POINT_ONCURVE_DIA + 2
        else:
            self.diameter = POINT_OFFCURVE_DIA + 2
        super().__init__(QRectF(self.glocation, QSizeF(self.diameter, self.diameter)))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._prepare_graphics(is_selected=False, hint_type=hint_type)
        self.label_proxy = None
        if self.name != None:
            self._prepare_label()
            self.label_proxy = yg_glyph_scene.addWidget(self.label)
        self.yg_glyph_scene = yg_glyph_scene

    def _prepare_label(self) -> None:
        self.label = QLabel()
        self.label.setStyleSheet("QLabel {background-color: transparent; color: gray;}")
        self.label.setText(str(self.name))
        self.label.move(round(self._x + self.diameter), round(self._y + self.diameter))

    #def _get_view_point(self):
    #    return self.pt

    def _remove_labels(self):
        if self.label_proxy:
            self.yg_glyph_scene.removeItem(self.label_proxy)

    def _prepare_graphics(self, **kwargs):
        # For ygPointMarker
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        pen = QPen()
        pen.setWidth(HINT_ANCHOR_WIDTH)
        if is_selected:
            pen.setColor(SELECTED_HINT_COLOR[hint_type])
            if self.label:
                self.label.show()
        else:
            pen.setColor(HINT_COLOR[hint_type])
            if self.label:
                self.label.hide()
        self.setPen(pen)

    #def get_scene(self) -> "ygGlyphScene":
    #    return self.yg_glyph_scene

    def mousePressEvent(self, event):
        # In ygPointMarker
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)


class ygPointable:
    """Mixin for getting the point that a hint line should attach to. For points,
    this is very simple. For sets, not so much.

    """

    def attachment_point(self, pt):
        pass

    def center_point(self):
        pass


class ygPointCollectionView(QGraphicsItem, ygGraphicalHintComponent, ygPointable):
    """A graphical representation of a collection of points. Select by clicking
    one of the points, or by clicking the border.

    Parameters:
    yg_glyph_scene (ygGlyphScene): The scene for this editing pane

    yg_params (ygModel.ygParams): The collection of params for a function
    or macro

    hint_type (str): The type of this hint (it must be "function" or
    "macro")

    """

    def __init__(self, yg_glyph_scene: "ygGlyphScene", *args) -> None:
        super().__init__()
        self.yg_glyph_scene = yg_glyph_scene
        self.point_dict = {}
        if type(args[0]) is ygParams:
            self.yg_params = args[0]
            kk = self.yg_params.point_dict.keys()
            for k in kk:
                self.point_dict[k] = yg_glyph_scene.resolve_point_identifier(
                    self.yg_params.point_dict[k]
                )
            self.hint_type = self.yg_params.hint_type
        else:
            point_list = args[0]
            self.hint_type = args[1]
            for p in point_list:
                pp = yg_glyph_scene.resolve_point_identifier(p)
                if type(pp) is ygPoint:
                    self.point_dict[pp.preferred_label()] = pp
                elif type(pp) is ygSet:
                    self.point_dict[pp.main_point().preferred_label()] = pp.main_point()
        self.point_markers = self._make_point_markers()
        lines, self.rect = self._boundingLines()
        self.borders = []
        for l in lines:
            self.borders.append(ygBorderLine(l, self.hint_type))
        self._prepare_graphics(is_selected=False, hint_type=self.hint_type)

    def _prepare_graphics(self, **kwargs):
        # For ygPointCollectionView
        is_selected = kwargs["is_selected"]
        hint_type = kwargs["hint_type"]
        if is_selected:
            pen_color = SELECTED_HINT_COLOR[hint_type]
        else:
            pen_color = HINT_COLOR[hint_type]
        pen = QPen(pen_color)
        pen.setWidth(FUNC_BORDER_WIDTH)
        pen.setDashPattern([1, 2])
        for b in self.borders:
            b.setPen(pen)
            b.update()
        ppen = QPen(pen_color)
        ppen.setWidth(HINT_ANCHOR_WIDTH)
        for m in self.point_markers:
            m.setPen(ppen)
            m.update()

    def visible_objects(self):
        return self.point_markers + self.borders

    def _make_point_markers(self):
        kk = self.point_dict.keys()
        marker_list = []
        for k in kk:
            p = self.yg_glyph_scene.resolve_point_identifier(self.point_dict[k])
            if type(p) is ygSet:
                p = p.main_point()
            ptv = self.yg_glyph_scene.yg_point_view_index[p.id]
            h = ygPointMarker(self.yg_glyph_scene, ptv, self.hint_type, name=k)
            marker_list.append(h)
        return marker_list

    def paint(self, painter, option, widget):
        """Got to be here, but it doesn't have to do anything."""
        pass

    def boundingRect(self) -> QRectF:
        return self.rect

    def height(self) -> int:
        return self.rect.height()

    def width(self) -> int:
        return self.rect.width()

    def _boundingLines(self) -> tuple:
        # Four visible lines for border, plus the bounding rect
        markers = self.point_markers
        min_x = max_x = min_y = max_y = None
        for m in markers:
            if not min_x:
                min_x = m._x
            else:
                min_x = min(min_x, m._x)
            if not min_y:
                min_y = m._y
            else:
                min_y = min(min_y, m._y)
            if not max_x:
                max_x = m._x
            else:
                max_x = max(max_x, m._x)
            if not max_y:
                max_y = m._y
            else:
                max_y = max(max_y, m._y)
        min_x -= 5
        min_y -= 5
        max_x += 15
        max_y += 15
        lines = []
        lines.append(QLineF(min_x, min_y, max_x, min_y))
        lines.append(QLineF(max_x, min_y, max_x, max_y))
        lines.append(QLineF(max_x, max_y, min_x, max_y))
        lines.append(QLineF(min_x, min_y, min_x, max_y))
        rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        return lines, rect

    def attachment_point(self, pt: "ygPointView") -> QPointF:
        if pt.x() < self.rect.x() - 1:
            x = self.rect.x() - 1
            if pt.y() < self.rect.y() - 1:
                return QPointF(x, self.rect.y() - 4)
            elif pt.y() > self.rect.y() + self.rect.height():
                return QPointF(x, self.rect.y() + self.rect.height() - 3)
            else:
                return QPointF(x, self.rect.y() + (self.rect.height() / 2) - 3)
        elif pt.x() > self.rect.x() + self.rect.width() + 1:
            x = self.rect.x() + self.rect.width() + 1
            if pt.y() < self.rect.y() - 1:
                return QPointF(x, self.rect.y() - 4)
            elif pt.y() > self.rect.y() + self.rect.height():
                return QPointF(x, self.rect.y() + self.rect.height() - 3)
            else:
                return QPointF(x, self.rect.y() + (self.rect.height() / 2) - 3)
        else:
            x = self.rect.x() + self.rect.width() / 2
            if pt.y() < self.rect.y() + (self.rect.height() / 2):
                return QPointF(x, self.rect.y() - 4)
            else:
                return QPointF(x, self.rect.y() + self.height() - 3)

    def center_point(self) -> QPointF:
        return QPointF(self.x() + (self.width() / 2), self.y() + (self.height() / 2))

    def contains(self, pt: QPointF) -> bool:
        for p in self.point_markers:
            if p.contains(pt):
                return True
        for b in self.borders:
            if b.contains(pt):
                return True
        return False

    def mousePressEvent(self, event) -> None:
        # In ygPointCollectionView
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        is_left = event.button() == Qt.MouseButton.LeftButton
        self.parentItem()._process_click_on_hint(self, with_shift, is_left)  # type: ignore


class ygSetView(ygPointCollectionView):
    """A graphical representation of a list of points."""

    def __init__(self, yg_glyph_scene: "ygGlyphScene", yg_set: ygSet, hint_type: str) -> None:
        super().__init__(yg_glyph_scene, yg_set.point_list, hint_type)
        self.yg_glyph_scene = yg_glyph_scene
        self.hint_type = hint_type


class ygSelection(QObject):
    """A list of selected objects (points, hints, or both).

    The class has functions for manipulating the list.
    """

    sig_selection_changed = pyqtSignal(object)

    def __init__(self, yg_glyph_scene: "ygGlyphScene") -> None:
        super().__init__()
        self.selected_objects: list = []
        self.yg_glyph_scene = yg_glyph_scene

    def setup_selection_signal(self, f: Optional[Callable]) -> None:
        self.sig_selection_changed.connect(f)

    #def get_scene(self) -> "ygGlyphScene":
    #    return self.yg_glyph_scene

    def send_signal(self) -> None:
        self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())

    def _cancel_selection(self, emit_signal: bool = True) -> None:
        for p in self.selected_objects:
            if p.selected:
                p.yg_unselect()
                p._prepare_graphics()
                p.update()
        self.selected_objects = []
        self.yg_glyph_scene.update()
        if emit_signal:
            self.send_signal()
            #self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())

    def _add_object(self, obj: ygSelectable, add_to_selection: bool) -> None:
        if not add_to_selection:
            self._cancel_selection(emit_signal=False)
        # Not sure what to do about next line. Study Protocol further?
        # isVisible is inherited from QGraphicsItem, and here we look
        # both at that and at things inherited from ygSelectable.
        if obj.isVisible():  # type: ignore
            obj.yg_select()
            self.selected_objects.append(obj)
            obj._prepare_graphics()
            obj.update()
        self.send_signal()
        # self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())

    def _toggle_object(self, obj: ygSelectable) -> None:
        # Problem as in _add_object above.
        if not obj.isVisible():  # type: ignore
            return
        if obj.selected():
            obj.yg_unselect()
            self.selected_objects.remove(obj)
        else:
            obj.yg_select()
            self.selected_objects.append(obj)
        obj._prepare_graphics()
        obj.update()
        self.send_signal()
        # self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())

    def _add_rect(self, rect: QRectF, add_to_selection: bool) -> None:
        """This method of selecting doesn't work on hints."""
        if not add_to_selection:
            self._cancel_selection()
        for ptv in self.yg_glyph_scene.yg_point_view_list:
            if ptv.isVisible() and rect.contains(ptv.glocation):
                ptv.yg_select()
                self.selected_objects.append(ptv)
                ptv._prepare_graphics()
                ptv.update()
        self.send_signal()
        #self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())

    def _toggle_rect(self, rect: QRectF) -> None:
        """This method of selecting doesn't work on hints."""
        for ptv in self.yg_glyph_scene.yg_point_view_list:
            if ptv.isVisible() and rect.contains(ptv.glocation):
                if ptv.selected():
                    ptv.yg_unselect()
                else:
                    ptv.yg_select()
                if ptv.selected():
                    self.selected_objects.append(ptv)
                else:
                    self.selected_objects.remove(ptv)
                ptv._prepare_graphics()
                ptv.update()
        self.send_signal()
        # self.sig_selection_changed.emit(self.yg_glyph_scene.selection_profile())


class ygPointView(QGraphicsEllipseItem, ygSelectable, ygPointable):
    """A visible point"""

    def __init__(self, yg_glyph_scene: "ygGlyphScene", yg_point: ygPoint):
        self._selected = False
        self.yg_point = yg_point
        if yg_point.on_curve:
            self.diameter = POINT_ONCURVE_DIA
        else:
            self.diameter = POINT_OFFCURVE_DIA
        # glocation is a QPointF. Initialize at 0,0: must be set later.
        self.glocation = QPointF(0, 0)
        super().__init__(QRectF(self.glocation, QSizeF(self.diameter, self.diameter)))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.border_width = 1
        self.index = -1
        self.yg_glyph_scene = yg_glyph_scene
        self.point_number_label: Optional[QLabel] = None
        self.point_number_label_proxy: Optional[QGraphicsProxyWidget] = None
        self._touched = False
        self._changed = False
        # These are the ygHintView objects that touch this point. When a hint
        # is removed from ygGlyphScene, remove the reference from this list.
        # If a hint being removed makes this list empty, remove the "touched"
        # flag from this ygPointView.
        self.owners: List[ygHintView] = []

    @property
    def touched(self) -> bool:
        return self._touched

    @touched.setter
    def touched(self, b: bool) -> None:
        if b != self._touched:
            self._touched = b
            self._changed = True
        else:
            self._changed = False

    @property
    def changed(self) -> bool:
        return self._changed

    def attachment_point(self, pt: Any) -> QPointF:
        return self.glocation

    def center_point(self) -> QPointF:
        return self.glocation

    def _prepare_graphics(self) -> None:
        # For ygPointView
        if self.selected():
            if self.touched:
                brushColor = POINT_TOUCHED_SELECTED
            else:
                brushColor = POINT_ONCURVE_SELECTED
        else:
            if self.touched:
                brushColor = POINT_TOUCHED
            else:
                brushColor = POINT_ONCURVE_FILL
        if self.yg_point.on_curve:
            penColor = POINT_ONCURVE_OUTLINE
        else:
            penColor = POINT_OFFCURVE_OUTLINE
        pen = QPen(penColor)
        pen.setWidth(self.border_width)
        brush = QBrush(brushColor)
        self.setBrush(brush)
        self.setPen(pen)
        self._changed = False

    #def get_scene(self) -> "ygGlyphScene":
    #    return self.yg_glyph_scene

    def has_label(self) -> bool:
        return self.point_number_label != None

    def add_label(self) -> None:
        """Adds a label for this point. The label is supplied by the model
        point, which will supply an index, a pair of coordinates, or a
        name, depending on current settings.
        """
        if self.point_number_label:
            self.del_label()
        self.point_number_label = QLabel()
        self.point_number_label.setStyleSheet(
            "QLabel {background-color: transparent; color: red; font-size: 90%}"
        )
        self.point_number_label.setText(
            str(self.yg_point.preferred_label(normalized=True))
        )
        self.point_number_label_proxy = self.yg_glyph_scene.addWidget(self.point_number_label)
        label_x = self.glocation.x() + self.diameter
        label_y = self.glocation.y() - self.point_number_label.height()
        self.point_number_label.move(round(label_x), round(label_y))

    def del_label(self) -> None:
        if self.point_number_label:
            self.yg_glyph_scene.removeItem(self.point_number_label_proxy)
            self.point_number_label = None
            self.point_number_label_proxy = None

    def update(self):
        pass

    def selected(self) -> bool:
        return self._selected

    def yg_select(self) -> None:
        self._selected = True
        self._prepare_graphics()
        self.update()

    def yg_unselect(self) -> None:
        self._selected = False
        self._prepare_graphics()
        self.update()

    def contains(self, p: QPointF) -> bool:
        return self.mapToScene(self.boundingRect()).boundingRect().contains(p)

    def mousePressEvent(self, event) -> None:
        # In ygPointView
        # Select when clicked, eiher adding to or replacing current selection.
        modifier = QApplication.keyboardModifiers()
        if (
            modifier & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier:
            if event.button() == Qt.MouseButton.LeftButton:
                self.yg_glyph_scene.yg_selection._toggle_object(self)
        else:
            if event.button() == Qt.MouseButton.LeftButton:
                self.yg_glyph_scene.yg_selection._add_object(self, False)


class SelectionRect(QGraphicsRectItem):
    """The rubber band that appears while dragging to select points."""

    def __init__(self, qr: QRectF) -> None:
        super(SelectionRect, self).__init__(qr)
        self.setRect(qr)


class ygGlyphScene(QGraphicsScene):
    """The workspace.

    Holds all the visible items belonging to hints.

    """

    sig_new_hint = pyqtSignal(object)
    sig_reverse_hint = pyqtSignal(object)
    sig_change_hint_color = pyqtSignal(object)
    sig_off_curve_visibility = pyqtSignal()
    sig_make_macfunc = pyqtSignal(object)
    sig_assign_macfunc_point = pyqtSignal(object)
    sig_edit_macfunc_params = pyqtSignal(object)
    sig_change_cv = pyqtSignal(object)
    sig_round_hint = pyqtSignal(object)
    sig_min_dist = pyqtSignal(object)
    sig_swap_macfunc_points = pyqtSignal(object)
    sig_toggle_point_numbers = pyqtSignal()
    sig_set_category = pyqtSignal(object)
    sig_name_points = pyqtSignal(object)

    def __init__(
            self, preferences: ygPreferences,
            yg_glyph: ygGlyph,
            owner: Optional["ygGlyphView"] = None) -> None:
        """yg_glyph is a ygGlyph object from ygModel."""
        global HINT_COLOR, SELECTED_HINT_COLOR, POINT_OFFCURVE_FILL, POINT_ONCURVE_FILL, POINT_OFFCURVE_SELECTED, POINT_ONCURVE_SELECTED, POINT_TOUCHED_SELECTED, POINT_TOUCHED

        self.preferences = preferences

        # Set up glyph info

        self.yg_glyph = yg_glyph
        self.owner = owner

        self.yg_point_view_index: dict = {}
        self.yg_point_view_list: list = []
        # No use for this one (right now)
        # self.yg_hint_view_index: dict = {}
        self.yg_hint_view_list: list = []
        super(ygGlyphScene, self).__init__()
        self.cv_error_msg = "Error while looking for a control value."

        # Current display preferences

        # Auto-detect if we have dark mode. We need to know so we can set
        # hint colors (not controlled by the system) to appropriate values.
        text_hsv_value = self.palette().color(QPalette.ColorRole.WindowText).value()
        bg_hsv_value = self.palette().color(QPalette.ColorRole.Base).value()
        self.dark_theme = text_hsv_value > bg_hsv_value
        if self.dark_theme:
            # These two are dicts
            HINT_COLOR = _HINT_DARK
            SELECTED_HINT_COLOR = _SELECTED_HINT_DARK
            # Fill colors. We don't have to distinguish between fill for on-
            # and off-curve points
            POINT_OFFCURVE_FILL = PTFILL_DARK
            POINT_ONCURVE_FILL = PTFILL_DARK
            POINT_OFFCURVE_SELECTED = PTFILL_SELECT_DARK
            POINT_ONCURVE_SELECTED = PTFILL_SELECT_DARK
            POINT_TOUCHED = PTFILL_TOUCH_DARK
            POINT_TOUCHED_SELECTED = PTFILL_TOUCH_SELECT_DARK
        else:
            HINT_COLOR = _HINT_COLOR
            SELECTED_HINT_COLOR = _SELECTED_HINT_COLOR
            POINT_OFFCURVE_FILL = PTFILL_COLOR
            POINT_ONCURVE_FILL = PTFILL_COLOR
            POINT_OFFCURVE_SELECTED = PTFILL_SELECT_COLOR
            POINT_ONCURVE_SELECTED = PTFILL_SELECT_COLOR
            POINT_TOUCHED = PTFILL_TOUCH_COLOR
            POINT_TOUCHED_SELECTED = PTFILL_TOUCH_SELECT_COLOR
        if self.preferences.top_window().show_off_curve_points != None:
            self.off_curve_points_showing = self.preferences.top_window().show_off_curve_points
        else:
            self.off_curve_points_showing = self.preferences.show_off_curve_points()
        self.point_numbers_showing = self.preferences.top_window().show_point_numbers
        self.zoom_factor = 1.0
        self.initial_zoom_factor = None
        self.canvas_size = self._calc_canvas_size()
        self.setSceneRect(QRectF(0, 0, self.canvas_size[0], self.canvas_size[1]))
        self.xTranslate = self.canvas_size[2]
        self.yTranslate = self.canvas_size[3]

        # Used when we draw an image instead of rendering the glyph.
        self.glyph_img = None

        # Try to get rid of ref to this scene in the model's ygGlyph class.
        # For now, we've got to ignore the type so as to avoid circular imports.
        self.yg_glyph.yg_glyph_scene = self  # type: ignore

        # Make graphical points

        for p in self.yg_glyph.points:
            yg_point_view = ygPointView(self, p)
            self.yg_point_view_index[p.id] = yg_point_view
            self.yg_point_view_list.append(yg_point_view)

        # Set up dimensions; scale the glyph.

        self.adv = 0
        self.lsb = 0
        self.xTranslate = 0
        self.yTranslate = 0
        self.original_coordinates: Any = None
        self.center_x = self.xTranslate + round(self.adv / 2)
        self.optimal_size = (0, 0)

        # Setup for selecting

        # selectionRect is the rubber band. None when no selection is underway.
        self.selectionRect: Optional[SelectionRect] = None
        # Set dragBeginPoint whenever left mouse button is pressed, in case of
        # rubber band selection.
        self.dragBeginPoint = QPointF(0, 0)
        self.yg_selection = ygSelection(self)
        self.yg_selection.setup_selection_signal(
            self.preferences.top_window().selection_changed
        )

        # Add the points and manage their visibility.

        if not self.yg_glyph.is_composite:
            for p in self.yg_point_view_list:
                p._prepare_graphics()
                if not p.yg_point.on_curve and not self.off_curve_points_showing:
                    p.hide()
                if p.isVisible() and self.point_numbers_showing:
                    p.add_label()
                self.addItem(p)

        # Set up connections.

        self.sig_new_hint.connect(self.add_hint)
        self.sig_change_cv.connect(self.change_cv)
        self.sig_reverse_hint.connect(self.reverse_hint)
        self.sig_swap_macfunc_points.connect(self.swap_macfunc_points)
        self.sig_change_hint_color.connect(self.change_hint_color)
        self.sig_edit_macfunc_params.connect(self.edit_macfunc_params)
        self.sig_off_curve_visibility.connect(self.toggle_off_curve_visibility)
        self.sig_make_macfunc.connect(self.make_macfunc)
        self.sig_toggle_point_numbers.connect(self.toggle_point_numbers)
        self.sig_set_category.connect(self.set_category)
        self.sig_round_hint.connect(self.toggle_hint_rounding)
        self.sig_min_dist.connect(self.toggle_min_dist)
        self.sig_name_points.connect(self.name_points)

        # Get and display the hints.

        self.install_hints(self.yg_glyph.hints)
        # review the list of points and mark the ones that are touched.
        if not self.yg_glyph.is_composite:
            for p in self.yg_point_view_list:
                if p.touched:
                    p._prepare_graphics()

    #
    # Sizing and zooming
    #

    def size_report(self) -> None:
        """For diagnostics."""
        print("Zoom factor: " + str(self.zoom_factor))
        print("xTranslate: " + str(self.xTranslate))
        print("yTranslate: " + str(self.yTranslate))
        ft_font = self.yg_glyph.yg_font.ft_font
        oc = ft_font["glyf"]._getCoordinatesAndControls(
            self.yg_glyph.gname, ft_font["hmtx"].metrics
        )[0]
        print("First point: " + str(oc[0]))
        qr = self.sceneRect()
        #print("Canvas rect: " + str(self.sceneRect()))
        print("Canvas rect: " + str(qr.x()) + " " + str(qr.y()) + " " + str(qr.width()) + " " + str(qr.height()))
        print("")

    def set_zoom_factor(self, new_zoom: float) -> None:
        self.zoom_factor = new_zoom
        # We are ignoring the zoom_factor setting in the preferences now, in favor
        # of setting an optimal zoom factor in the __init__ of ygGlyphScene. Survey
        # uses of the preferences object to make sure this is so.
        self.preferences.top_window().zoom_factor = self.zoom_factor
        self.scale_glyph()
        self.center_x = self.xTranslate + round(self.adv / 2)
        self.update()
        self.install_hints(self.yg_glyph.hints)
        # This will have the effect of moving point labels to the new positions
        # of the points. Affect only those already visible.
        if not self.yg_glyph.is_composite:
            for p in self.yg_point_view_list:
                if p.has_label():
                    p.add_label()

    def reset_scale(self) -> None:
        c = self.original_coordinates
        ft_font = self.yg_glyph.yg_font.ft_font
        ft_font["glyf"]._setCoordinates(
            self.yg_glyph.gname, c, ft_font["hmtx"].metrics
        )

    def scale_glyph(self) -> None:
        # Start out clean, with coordinates as in original font. That way,
        # zoom_factor always operates on the original, as opposed to the last
        # value.
        ft_font = self.yg_glyph.yg_font.ft_font
        ft_glyph = self.yg_glyph.ft_glyph
        if self.original_coordinates:
            ft_font["glyf"]._setCoordinates(
                self.yg_glyph.gname, self.original_coordinates, ft_font["hmtx"].metrics
            )
        else:
            self.original_coordinates = copy.deepcopy(
                ft_font["glyf"]._getCoordinatesAndControls(
                    self.yg_glyph.gname, ft_font["hmtx"].metrics
                )[0]
            )
        c = copy.deepcopy(self.original_coordinates)
        c.scale((self.zoom_factor, self.zoom_factor))
        ft_font["glyf"]._setCoordinates(
            self.yg_glyph.gname, c, ft_font["hmtx"].metrics
        )
        self.yg_glyph.ft_glyph.recalcBounds(self.yg_glyph.yg_font.ft_font["glyf"])
        self.adv, self.lsb = self.yg_glyph.yg_font.ft_font["hmtx"].metrics[
            self.yg_glyph.gname
        ]
        self.canvas_size = self._calc_canvas_size()
        self.setSceneRect(QRectF(0, 0, self.canvas_size[0], self.canvas_size[1]))
        self.xTranslate = self.canvas_size[2]
        self.yTranslate = self.canvas_size[3]
        for c_index, cc in enumerate(c):
            try:
                p = self.yg_point_view_list[c_index]
                p.glocation = self._font2Qt(cc[0], cc[1], p.yg_point.on_curve)
                p.setPos(p.glocation)
            except IndexError as e:
                # fontTools coordinate list has phantom points at the end, which we ignore.
                pass

        # glyph_set = {self.yg_glyph.gname: self.yg_glyph.ft_glyph}
        glyph_set = self.yg_glyph.yg_font.ft_font.getGlyphSet()
        glyph_table = self.yg_glyph.yg_font.ft_font["glyf"]
        if self.yg_glyph.is_composite:
            pass
            #freetype_pen = FreeTypePen(glyph_set)
            #print(type(freetype_pen))
            #print(type(glyph_table))
            #self.yg_glyph.ft_glyph.draw(freetype_pen, glyph_table)
            #width, height = self.yg_glyph.dimensions()
            # arr = freetype_pen.array(width = int((width * 64) * self.zoom_factor), height = int((height * 64) * self.zoom_factor))
            #arr = freetype_pen.array(width * self.zoom_factor, height * self.zoom_factor)
            #print("arr.shape: " + str(arr.shape))
            #width, height = arr.shape
            #self.glyph_img = QImage(arr, int(width * self.zoom_factor), int(height * self.zoom_factor), QImage.Format.Format_Mono)
            #
            #from matplotlib import pyplot as plt
            #plt.imshow(arr)
            #plt.show()
            #
            #qd = QDialog(self.preferences.top_window())
            #layout = QHBoxLayout()
            #l = QLabel()
            #layout.addWidget(l)
            #pm = QPixmap.fromImage(self.glyph_img)
            #l.setPixmap(pm)
            #qd.exec()
        else:
            self.path = QPainterPath()
            self.qt_pen = QtPen(glyph_set, path=self.path)
            self.yg_glyph.ft_glyph.draw(self.qt_pen, glyph_table)

    def _calc_canvas_size(self) -> Tuple[int, int, int, int]:
        """This calculates a canvas that will do for the entire font. The result
        can be awkward (see the absurd situation in Junicode, which has an
        extremely wide canvas because of one glyph, threeemdash (U+2E3B)).
        """
        f = self.yg_glyph.yg_font.ft_font
        x_size = abs(f["head"].xMin) + abs(f["head"].xMax) + (GLYPH_WIDGET_MARGIN * 2)
        y_size = abs(f["head"].yMin) + abs(f["head"].yMax) + (GLYPH_WIDGET_MARGIN * 2)
        zero_x = abs(f["head"].xMin) + GLYPH_WIDGET_MARGIN
        zero_y = abs(f["head"].yMax) + GLYPH_WIDGET_MARGIN
        return (
            round(x_size * self.zoom_factor),
            round(y_size * self.zoom_factor),
            round(zero_x * self.zoom_factor),
            round(zero_y * self.zoom_factor),
        )

    def _font2Qt(self, x: int, y: int, onCurve: bool = False) -> QPointF:
        """Converts font coordinate system to Qt, for positioning points

        The font coordinate system has zero at the baseline and
        higher y values towards the top. The Qt system has 0,0
        at the top left of the canvas and higher y values towards
        the bottom.
        """
        thisx = x + self.xTranslate
        thisy = (y * -1) + abs(self.yTranslate)
        if onCurve:
            adjust = POINT_ONCURVE_DIA / 2
        else:
            adjust = POINT_OFFCURVE_DIA / 2
        # These are the coordinates for the points
        # print("x: " + str(thisx - adjust))
        # print("y: " + str(thisy - adjust))
        return QPointF(thisx - adjust, thisy - adjust)
    
    def mid_point_y(self):
        if len(self.yg_point_view_list) > 0:
            highest, lowest = self.yg_glyph.extreme_points_y()
            highest_coord = self.yg_point_view_list[highest[0]].glocation.y()
            lowest_coord = self.yg_point_view_list[lowest[0]].glocation.y()
            return lowest_coord - round((lowest_coord - highest_coord) / 2)
        else:
            if self.owner:
                return self.owner.sceneRect().center().y()
            return 500

    #
    # Overrides
    #

    def drawBackground(self, painter: QPainter, rect) -> None:
        """The glyph outline is drawn as the background layer for this scene.
        Points and hints are drawn in the item layer, and the foreground
        layer is not used at this time.
        """

        global HINT_COLOR, SELECTED_HINT_COLOR

        if not self.initial_zoom_factor:
            visible_x = rect.width()
            visible_y = rect.height()
            optimal_x = round(visible_x * 0.8)
            optimal_y = round(visible_y * 0.8)
            self.optimal_size = (optimal_x, optimal_y)
            width, height = self.yg_glyph.dimensions()
            if width != 0:
                x_ratio = optimal_x / width
            else:
                x_ratio = 1
            if height != 0:
                y_ratio = optimal_y / height
            else:
                y_ratio = 1
            # Limit the initial zoom factor to max of 2.0. This prevents little glyphs
            # like period from becoming disconcertingly large.
            self.initial_zoom_factor = min(2.0, min(x_ratio, y_ratio))
            self.set_zoom_factor(self.initial_zoom_factor)
            if self.owner:
                self.owner.centerOn(self.center_x, self.mid_point_y())

        # this_ft_glyph = self.yg_glyph.ft_glyph
        if self.yg_glyph.is_composite:
            pass
        else:
            painter.scale(1.0, -1.0)
            painter.translate(QPointF(self.xTranslate, self.yTranslate * -1))

        pen = painter.pen()

        if self.yg_glyph.is_composite:
            pass
            # For now, anyway, we're not displaying anything for composites in the
            # main editing window. This should change, but don't get elaborate: this
            # display is of much less interest than (e.g.) the preview.
        else:
            if self.preferences["show_metrics"]:
                pen.setWidth(1)
                if self.dark_theme:
                    pen.setColor(QColor(220, 220, 220, 75))
                    HINT_COLOR = _HINT_DARK
                    SELECTED_HINT_COLOR = _SELECTED_HINT_DARK
                else:
                    pen.setColor(QColor(50, 50, 50, 50))
                    HINT_COLOR = _HINT_COLOR
                    SELECTED_HINT_COLOR = _SELECTED_HINT_COLOR
                painter.setPen(pen)
                painter.drawLine(QLine(-abs(self.xTranslate), 0, round(self.width()), 0))
                ya = -abs(self.yTranslate)
                painter.drawLine(QLine(0, ya, 0, round(self.height())))
                painter.drawLine(QLine(self.adv, ya, self.adv, round(self.height())))

            pen.setWidth(CHAR_OUTLINE_WIDTH)
            pen.setColor(QColor("gray"))
            painter.setPen(pen)
            painter.drawPath(self.path)

    #
    # Editing slots
    #

    @pyqtSlot()
    def guess_cv(self) -> None:
        """Called from a slot in ygGlyphView, this function
        guesses the right CV for selected point(s) or
        hint.
        """
        _selected_objects = self.selected_objects(False)
        selected_hint = None
        for s in _selected_objects:
            if type(s) is ygHintView or type(s) is ygHint:
                selected_hint = self._model_hint(s)
                break
        if selected_hint != None:
            htn = self.get_hint_type_num(selected_hint.hint_type)
            cv_type = "pos"
            if htn == 3:
                cv_type = "dist"
            cv_list = self.yg_glyph.yg_font.cvt.get_list(
                self.yg_glyph,
                type=cv_type,
                axis=self.current_axis(),
                cat=self.yg_glyph.get_category(),
                suffix=self.yg_glyph.get_suffixes(),
            )
            try:
                cv_name = self.yg_glyph.yg_font.cvt.get_closest_cv_name(
                    cv_list, selected_hint
                )
                selected_hint.set_cv(cv_name)
            except Exception:
                pass

    def guess_cv_for_new_hint(self, hint: ygHint) -> None:
        """Like guess_cv(), but this is called as part of the process of constructing
        a hint, and therefore should not trigger a signal.
        """
        if hint != None:
            htn = self.get_hint_type_num(hint.hint_type)
            cv_type = "pos"
            if htn == 3:
                cv_type = "dist"
            cv_list = self.yg_glyph.yg_font.cvt.get_list(
                self.yg_glyph,
                type=cv_type,
                axis=self.current_axis(),
                cat=self.yg_glyph.get_category(),
                suffix=self.yg_glyph.get_suffixes(),
            )
            try:
                cv_name = self.yg_glyph.yg_font.cvt.get_closest_cv_name(cv_list, hint)
                hint._set_cv(cv_name)
            except Exception as e:
                print(e)
                print(e.args)
                pass

    @pyqtSlot(object)
    def edit_macfunc_params(self, hint: ygHintView) -> None:
        ed_dialog = macfuncDialog(hint)
        r = ed_dialog.exec()
        if r == QDialog.DialogCode.Accepted:
            hint.yg_hint.macfunc_other_args = ed_dialog.result_dict

    @pyqtSlot()
    def toggle_off_curve_visibility(self) -> None:
        if self.yg_glyph.is_composite:
            return
        self.off_curve_points_showing = not self.off_curve_points_showing
        self.preferences.top_window().show_off_curve_points = (
            self.off_curve_points_showing
        )
        if not self.yg_glyph.is_composite:
            for p in self.yg_point_view_list:
                if not p.yg_point.on_curve:
                    if self.off_curve_points_showing:
                        p.show()
                        if self.point_numbers_showing:
                            p.add_label()
                    else:
                        p.hide()
                        if self.point_numbers_showing:
                            p.del_label()

    def make_control_value(self) -> None:
        """ With one or two points selected, launch a dialog for making a pos or dist CV.
        """
        sel = self.selected_objects(True)
        if len(sel) == 0:
            return
        if len(sel) >= 1:
            p1 = self._model_point(sel[0])
        p2 = None
        if len(sel) >= 2:
            p2 = self._model_point(sel[1])
        cv_dialog = makeCVDialog(p1, p2, self.yg_glyph, self.preferences)
        r = cv_dialog.exec()
        if r == QDialog.DialogCode.Accepted:
            self.yg_glyph.yg_font.cvt.set_clean(False)

    def name_points(self, pts: List[ygPointView]) -> None:
        msg = "Name the point"
        if len(pts) > 1:
            msg += "s"
        msg += ":"
        text, ok = QInputDialog().getText(
            self.preferences.top_window(), "Name points", msg, QLineEdit.EchoMode.Normal
        )
        if ok and text:
            mpts = []
            for p in pts:
                mpts.append(self._model_point(p))
            self.yg_glyph.names.add(mpts, text)
            self.set_point_display(
                (
                    lambda: "coord"
                    if self.preferences.top_window().points_as_coords
                    else "index"
                )()
            )

    def untouch_all(self):
        for p in self.yg_point_view_list:
            p.touched = False
            if p.changed:
                p.owners.clear()
                p._prepare_graphics()

    @pyqtSlot(object)
    def change_hint_color(self, _params: dict) -> None:
        _params["hint"].yg_hint.change_hint_color(_params["color"])

    @pyqtSlot(object)
    def toggle_hint_rounding(self, hint: ygHintView) -> None:
        self._model_hint(hint).toggle_rounding()

    @pyqtSlot(object)
    def toggle_min_dist(self, hint: ygHintView) -> None:
        self._model_hint(hint).toggle_min_dist()

    @pyqtSlot()
    def toggle_point_numbers(self) -> None:
        if self.yg_glyph.is_composite:
            return
        self.point_numbers_showing = not self.point_numbers_showing
        self.preferences.top_window().show_point_numbers = self.point_numbers_showing
        for p in self.yg_point_view_list:
            if self.point_numbers_showing:
                if p.isVisible():
                    p.add_label()
            else:
                p.del_label()

    @pyqtSlot(object)
    def set_category(self, c: str) -> None:
        if c == "Default":
            try:
                self.yg_glyph.props.del_property("category")
            except Exception:
                pass
        else:
            self.yg_glyph.set_category(c)

    def set_point_display(self, pv: str) -> None:
        if self.yg_glyph.is_composite:
            return
        for p in self.yg_point_view_list:
            p.yg_point.label_pref = pv
            if self.point_numbers_showing:
                if p.isVisible():
                    p.add_label()

    @pyqtSlot(object)
    def swap_macfunc_points(self, data: dict) -> None:
        hint = data["hint"].yg_hint
        new_pt_name = data["new_pt"]
        old_pt_name = data["old_pt"]
        hint.swap_macfunc_points(new_pt_name, old_pt_name)

    @pyqtSlot(object)
    def reverse_hint(self, h: ygHint) -> None:
        """Recipient of a signal for reversing a hint. Communicates to the
        model that a hint must be added to the hint tree.

        Parameters:
        h (ygModel.ygHint): the hint to be reversed

        """
        h.reverse_hint(h)

    @pyqtSlot(dict)
    def change_cv(self, param_dict: dict) -> None:
        """Recipient of a signal for adding or changing a control value.

        Parameters:
        param_dict (dict): A dictionary containing "hint" (the affected
        hint, ygHintView) and "cv" (the new cv)

        """
        if type(param_dict["hint"]) is ygHintView:
            param_dict["hint"].yg_hint.set_cv(param_dict["cv"])

    @pyqtSlot(object)
    def add_hint(self, h: ygHint) -> None:
        """Recipient of a signal for adding a hint. Communicates to the model
        that a hint must be added to the hint tree.

        Parameters:
        h (ygModel.ygHint): the hint to add to the tree

        """
        if type(h) is ygHint:
            h.add_hint(h)
        elif type(h) is ygHintView:
            h.add_hint(h.yg_hint)

    def install_hints(self, hint_list: List[ygHint]) -> None:
        """Installs a collection of hints sent from the model.

        Parameters:
        hint_list: All the hints for either the y or the x axis
        for this glyph, in a list.

        """
        # Remove the old hints (destroying the ygHintView wrappers) and empty
        # out the list storing them.
        for h in self.yg_hint_view_list:
            if h in self.items():
                h._remove_labels()
                self.removeItem(h)
        # This may seem crazy, but it seems most reliable and stable if we
        # delete all touch data and build it again.
        self.untouch_all()
        self.yg_hint_view_list.clear()
        # The hints we get from the model are ygModel.ygHint objects, using
        # any legal Xgridfit identifier for the points. Wrap each one in a
        # ygHintView object.
        for h in hint_list:
            vh = self._make_visible_hint(h)
            self.yg_hint_view_list.append(vh)
        self.update()
        self.yg_selection.send_signal()

    def delete_selected_hints(self) -> None:
        oo = self.selected_objects(False)
        hh = []
        for o in oo:
            if type(o) is ygHintView:
                hh.append(o.yg_hint)
        if len(hh) > 0:
            # Call a function in the model.
            hh[0].delete_hints(hh)

    def add_to_set(self):
        """Do validity check on current selection, then call ygHint.add_points."""
        profile = self.selection_profile()
        # At least one non-touched point selected
        # Exactly one hint selected
        # hint type is shift, align, or interpolate [1, 2]
        # exactly one hint selected
        if (profile[0] == 0
            and profile[1] > 0
            and profile[3][0] in [1, 2]
            and profile[4] == 1
        ):
            objects = self.selected_objects(False)
            hints = []
            points = []
            for o in objects:
                if type(o) is ygPointView:
                    points.append(self._model_point(o))
                if type(o) is ygHintView:
                    hints.append(self._model_hint(o))
            hints[0].add_points(points)

    def delete_from_set(self):
        profile = self.selection_profile()
        # if no selected points are touched,
        # or there are untouched points selected,
        # or there is not exactly one owner (hint) type,
        # or the one type is not shift, align, or interpolate,
        # or any hints are selected,
        # then we do nothing.
        if (
            profile[0] == 0
            or profile[1] > 0
            or len(profile[2]) != 1
            or not profile[2][0] in [1, 2]
            or len(profile[3]) != 0
        ):
            return
        selected_points = self.selected_objects(True)
        if len(selected_points) > 0:
            try:
                owner_hint = None
                hint_list = self.yg_glyph.hints
                model_points = []
                for p in selected_points:
                    model_points.append(self._model_point(p))
                for h in hint_list:
                    if h.contains_points(model_points):
                        owner_hint = h
                        break
                if not owner_hint:
                    print("Couldn't get an owner hint")
                    return
                owner_hint.delete_points(model_points)
            except Exception as e:
                pass

    #
    # Utilities
    #

    #def get_scene(self) -> "ygGlyphScene":
    #    """Returns the current scene (always this object!)
    #
    #    Returns:
    #    ygGlyphScene: this scene
    #    """
    #    return self

    def _mouse_over_point(self, qp: QPoint) -> ygPointView:
        """In ygGlyphScene. Determines whether the mouse is positioned over a point.

        Parameters:
        qp (QPos): The current position of the mouse

        Returns:
        ygPointView if the mouse is over a point; otherwise None

        """
        pt_keys = self.yg_point_view_index.keys()
        for pk in pt_keys:
            if self.yg_point_view_index[pk].contains(qp):
                return self.yg_point_view_index[pk]
        return None

    def _mouse_over_hint(self, qp: QPointF) -> Optional[ygHintView]:
        """Determines whether the mouse is positioned over a hint.

        Parameters:
        qp (QPos): The current position of the mouse

        Returns:
        ygHintView if the mouse is over a hint; otherwise None
        """
        for h in self.yg_hint_view_list:
            if h.contains(qp):
                return h
        return None

    def _adjust_rect(self, current_point: ygPointView) -> QRectF:
        """Flips points around to account for rubber band rotating around
        the origin point.

        Parameters:
        current_point: The fixed point at which the selection began

        Returns:
        QRectF: The adjusted selection rect
        """
        qr = QRectF(0, 0, 0, 0)
        current_x = current_point.x()
        current_y = current_point.y()
        origin_x = self.dragBeginPoint.x()
        origin_y = self.dragBeginPoint.y()
        if current_x > origin_x and current_y > origin_y:
            qr.setCoords(origin_x, origin_y, current_x, current_y)
        elif current_x < origin_x and current_y > origin_y:
            qr.setCoords(current_x, origin_y, origin_x, current_y)
        elif current_x > origin_x and current_y < origin_y:
            qr.setCoords(origin_x, current_y, current_x, origin_y)
        elif current_x < origin_x and current_y < origin_y:
            qr.setCoords(current_x, current_y, origin_x, origin_y)
        else:
            qr.setCoords(origin_x, origin_y, origin_x, origin_y)
        return qr

    def selection_profile(self) -> Tuple[int, int, List[int], List[int]]:
        """Surveys the current selection and returns a tuple containing:
        - The number of touched points
        - The number of untouched points
        - The (integer) types of the owners of touched points
        - The (integer) types of any selected hints
        - The number of selected hints
        """
        s = self.selected_objects(True)
        touched_point_count = untouched_point_count = 0
        owner_types = []
        for ss in s:
            if ss.touched:
                touched_point_count += 1
                for h in ss.owners:
                    htn = hint_type_nums[h.yg_hint.hint_type]
                    if not htn in owner_types:
                        owner_types.append(htn)
            else:
                untouched_point_count += 1
        selected_hint_types = []
        s = self.selected_objects(False)
        hint_count = 0
        for ss in s:
            if type(ss) is ygHintView:
                hint_count += 1
                htn = hint_type_nums[ss.yg_hint.hint_type]
                if not htn in selected_hint_types:
                    selected_hint_types.append(htn)
        return (
            touched_point_count,
            untouched_point_count,
            owner_types,
            selected_hint_types,
            hint_count,
        )

    def selected_objects(self, points_only: bool) -> list:
        """Get a list of objects (points and hints) selected by the user.

        Parameters:
        points_only (bool): if true, return only selected points (not hints)

        Returns:
        A list of all selected objects

        """
        if not points_only:
            return self.yg_selection.selected_objects
        result = []
        for o in self.yg_selection.selected_objects:
            if type(o) is ygPointView:
                result.append(o)
        return result

    def get_hint_type_num(self, htype: str) -> int:
        """Translates the string description of the hint type (e.g. 'stem')
        into an int used by the program for deciding the shape of the
        visible hint.

        Parameters:
        htype (str): The string that describes the hint

        Returns:
        int: 0: no reference point; 1: one reference point; any number of
        targets; 2: two reference points; any number of targets; 3: one
        reference point; one target; 4:

        """
        return hint_type_nums[htype]

    def resolve_point_identifier(
        self, pt: Union[ygPointView, ygPoint], kwargs=None
    ) -> ygPoint:
        """Gets a ygModel.ygPoint object.

        Parameters:
        pt: A ygModel.ygPoint or ygPointView object, or any kind of idenfifier
        accepted by Xgridfit.

        Returns: A ygModel.ygPoint object.

        """
        if type(pt) is ygPointView:
            return pt.yg_point
        return self.yg_glyph.resolve_point_identifier(pt)

    def _model_hint(self, h: Union[ygHintView, ygHint]) -> ygHint:
        if type(h) is ygHintView:
            return h.yg_hint
        return h  # type: ignore

    def _model_point(self, p: Union[ygPointView, ygPoint]) -> ygPoint:
        if type(p) is ygPointView:
            return p.yg_point
        return p  # type: ignore

    def current_axis(self) -> str:
        return self.yg_glyph.axis

    def _distance(
        self, pt_a: Union[ygPointView, ygPoint], pt_b: Union[ygPointView, ygPoint]
    ) -> int:
        """Returns the distance between two points (in font units) along
        the current axis.
        """
        pa = self._model_point(pt_a)
        pb = self._model_point(pt_b)
        if self.current_axis() == "y":
            return abs(pa.font_y - pb.font_y)
        return abs(pa.font_x - pb.font_x)

    #
    # Factories
    #

    def _make_visible_hint(self, hint: ygHint) -> ygHintView:
        """Builds ygHintView objects from ygHint objects and adds them to
        this ygGlyphScene (a QGraphicsScene).

        Parameters:
        hint (ygHint): The hint from the model

        Returns:
        ygHintView: The graphical hint, if one has been made (None if not)

        """
        # Make sure we've got the hint type
        hint_type = hint.hint_type
        hint_type_num = self.get_hint_type_num(hint_type)

        # Build the visible hints
        if hint_type_num == 0:
            # 0 = draw a circle around a point.
            target = self.resolve_point_identifier(hint.target)
            if type(target) is ygSet:
                target = target.main_point()
            gtarget = self.yg_point_view_index[target.id]
            hpm = ygPointMarker(self, gtarget, "anchor")
            yg_hint_view = ygHintView(self, hint, hpm)
            yg_hint_view._touch_all_points()
            yg_hint_view._prepare_graphics()
            self.addItem(yg_hint_view)
        elif hint_type_num in [1, 3]:
            # With type 1, the target can be a set.
            target = self.resolve_point_identifier(hint.target)
            if type(target) is ygSet:
                gtarget = ygSetView(self, target, hint_type)
            else:
                gtarget = self.yg_point_view_index[target.id]
            # *** If this is going to crash, need to catch it and recover. Maybe
            # mark the hint as invalid and skip it when drawing or compiling?
            if hint.ref == None:
                print("Warning: ref is None (target is " + str(target) + ")")
            ref = self.resolve_point_identifier(hint.ref)
            gref = self.yg_point_view_index[ref.id]
            ha = ygHintStem(
                gref, gtarget, self.yg_glyph.axis, hint_type, parent=self
            )
            hb = ygHintButton(self, ha.center_point(), hint)
            ah = ygArrowHead(
                ha.endPoint(), ha.arrowhead_direction, hint_type, ha.id, parent=self
            )
            ah.setPos(ha.endPoint())
            glist = [ha, hb, ah]
            if type(gtarget) is ygSetView:
                glist.extend(gtarget.visible_objects())
            yg_hint_view = ygHintView(self, hint, glist)
            yg_hint_view._touch_all_points()
            yg_hint_view._prepare_graphics()
            self.addItem(yg_hint_view)
        elif hint_type_num == 2:
            # 2 = arrows from two reference points to one interpolated point or set
            target = self.resolve_point_identifier(hint.target)
            if type(target) is ygSet:
                gtarget = ygSetView(self, target, hint_type)
            else:
                gtarget = self.yg_point_view_index[target.id]
            ref_list = hint.ref
            if type(ref_list) is list:
                ref_list = ygSet(ref_list)
            if len(ref_list.point_list) < 2:
                # This could come up with faulty code from the box, so handle it
                # with an error dialog.
                raise Exception(
                    "There must be two reference points for an interpolation hint"
                )
            gref = []
            ref_one = self.resolve_point_identifier(ref_list.point_list[0])
            ref_two = self.resolve_point_identifier(ref_list.point_list[1])
            gref.append(self.yg_point_view_index[ref_one.id])
            gref.append(self.yg_point_view_index[ref_two.id])
            ha1 = ygHintStem(
                gref[0], gtarget, self.yg_glyph.axis, hint_type, parent=self
            )
            hb1 = ygHintButton(self, ha1.center_point(), hint)
            ha2 = ygHintStem(
                gref[1], gtarget, self.yg_glyph.axis, hint_type, parent=self
            )
            ah1 = ygArrowHead(
                ha1.endPoint(), ha1.arrowhead_direction, hint_type, ha1.id, parent=self
            )
            hb2 = ygHintButton(self, ha2.center_point(), hint)
            ah2 = ygArrowHead(
                ha2.endPoint(), ha2.arrowhead_direction, hint_type, ha2.id, parent=self
            )
            ah1.setPos(ha1.endPoint())
            ah2.setPos(ha2.endPoint())
            glist = [ha1, hb1, ah1, ha2, hb2, ah2]
            if type(gtarget) is ygSetView:
                glist.extend(gtarget.visible_objects())
            yg_hint_view = ygHintView(self, hint, glist)
            yg_hint_view._touch_all_points()
            yg_hint_view._prepare_graphics()
            self.addItem(yg_hint_view)
        elif hint_type_num == 4:
            # Green anchors, surrounded by green border
            gtarget = self.resolve_point_identifier(hint.target)
            if type(gtarget) is ygParams:
                gtarget.name = hint.macfunc_name
                gtarget.hint_type = hint_type
                gtarget.other_params = hint.macfunc_other_args
                yg_params_view = ygPointCollectionView(self, gtarget)
                yg_hint_view = ygHintView(self, hint, yg_params_view.visible_objects())
                yg_hint_view._set_name(gtarget.name)
                yg_hint_view._touch_all_points()
                yg_hint_view._prepare_graphics()
                self.addItem(yg_hint_view)
            else:
                raise Exception(
                    "Something went wrong with gtarget in _make_visible_hint"
                )
        else:
            raise Exception("Unknown hint type " + str(hint_type_num))
        self.yg_hint_view_list.append(yg_hint_view)
        return yg_hint_view

    @pyqtSlot(dict)
    def make_macfunc(self, _params: dict) -> None:
        hint_type = _params["hint_type"]
        name = _params["name"]
        self.make_macfunc_from_selection(hint_type, name=name)
        # Called function will send the signal to the model.

    def get_round_default(self, hint: ygHint) -> Optional[bool]:
        t = hint.hint_type
        l = self.yg_glyph.yg_font.defaults.get_default("round")
        if l != None:
            if t in l:
                return True
        l = self.yg_glyph.yg_font.defaults.get_default("no-round")
        if l != None:
            if t in l:
                return False
        return None

    def make_hint_from_selection(
        self, hint_type: str, ctrl: bool = False, shift: bool = False
    ) -> None:
        """Make a hint based on selection in the editing panel.

        Should we be making ygModel.ygHint instances here? Since
        we're making valid yaml source, wouldn't it be better to
        pass that with the signal?
        """
        hint_type_num = self.get_hint_type_num(hint_type)
        pp = self.selected_objects(True)
        pplen = len(pp)
        new_yg_hint = None
        if hint_type_num == 0:
            if pplen >= 1:
                h = {"ptid": self._model_point(pp[0]).preferred_label()}
                new_yg_hint = ygHint(self.yg_glyph, h)
                dr = self.get_round_default(new_yg_hint)
                if dr != None:
                    new_yg_hint.set_round(dr)
                if ctrl:
                    self.guess_cv_for_new_hint(new_yg_hint)
                if shift:
                    new_yg_hint.set_round(True)
                self.sig_new_hint.emit(new_yg_hint)
        if hint_type_num in [1, 3]:
            if pplen >= 2:
                try:
                    if hint_type_num == 3:
                        hint_type = stemFinder(
                            self._model_point(pp[0]),
                            self._model_point(pp[1]),
                            self.yg_glyph,
                        ).get_color()
                except Exception as e:
                    print(e)
                ref_name = ""
                target_names = []
                for ppp in pp:
                    if ppp.touched:
                        ref_name = self._model_point(ppp).preferred_label()
                    else:
                        target_names.append(self._model_point(ppp).preferred_label())
                if len(target_names) == 1 or hint_type_num == 3:
                    tgt = target_names[0]
                else:
                    tgt = target_names
                # This should not happen if we've filtered properly before calling this.
                if ref_name == "" or len(target_names) == 0:
                    return
                h = {"ptid": tgt, "ref": ref_name, "rel": hint_type}
                new_yg_hint = ygHint(self.yg_glyph, h)
                dr = self.get_round_default(new_yg_hint)
                if dr != None:
                    new_yg_hint.set_round(dr)
                if ctrl and hint_type_num == 3:
                    self.guess_cv_for_new_hint(new_yg_hint)
                if shift:
                    new_yg_hint.set_round(True)
                self.sig_new_hint.emit(new_yg_hint)
        if hint_type_num == 2:
            if pplen >= 3:
                # If two of the three selected points are touched, they are the
                # reference points, and the untouched point is the target.
                # Otherwise, sort the points by x or y position: the middle one
                # is the target, and the ones on the ends are reference points.
                # If the program makes the wrong choice, user can rearrange
                # things in the editor.
                touched_points = []
                untouched_points = []
                for t in pp:
                    if type(t) is ygPointView:
                        if t.touched:
                            touched_points.append(self._model_point(t))
                        else:
                            untouched_points.append(self._model_point(t))
                if len(touched_points) == 2 and len(untouched_points) >= 1:
                    touched_names = [
                        touched_points[0].preferred_label(),
                        touched_points[1].preferred_label(),
                    ]
                    if len(untouched_points) == 1:
                        tgt = untouched_points[0].preferred_label()
                    else:
                        tgt = []
                        for p in untouched_points:
                            tgt.append(p.preferred_label())
                    # Think about this more. Why does mypy not like it?
                    h = {"ptid": tgt, "ref": touched_names, "rel": hint_type}  # type: ignore
                    new_yg_hint = ygHint(self.yg_glyph, h)
                else:
                    newlist = []
                    for p in pp:
                        newlist.append(self._model_point(p))
                    sorter = ygPointSorter(self.yg_glyph.axis)
                    sorter.sort(newlist)
                    target = newlist.pop(1)
                    ref_names = [
                        newlist[0].preferred_label(),
                        newlist[1].preferred_label(),
                    ]
                    target_name = target.preferred_label()
                    h = {"ptid": target_name, "ref": ref_names, "rel": hint_type}  # type: ignore
                    new_yg_hint = ygHint(self.yg_glyph, h)
                dr = self.get_round_default(new_yg_hint)
                if dr != None:
                    new_yg_hint.set_round(dr)
                if shift:
                    new_yg_hint.set_round(True)
                self.sig_new_hint.emit(new_yg_hint)

    def make_macfunc_from_selection(self, hint_type: str, **kwargs) -> None:
        hint_type_num = self.get_hint_type_num(hint_type)
        pp = self.selected_objects(True)
        if hint_type_num == 4:
            name = kwargs["name"]
            if hint_type == "function":
                fu = ygFunction(name, self.yg_glyph.yg_font)
                pt_names = fu.required_point_list() + fu.optional_point_list()
                other_params = {"nm": name}
            else:
                ma = ygMacro(name, self.yg_glyph.yg_font)
                pt_names = ma.required_point_list() + ma.optional_point_list()
                other_params = {"nm": name}

            # Got to have param names associated with these points. Gonna make
            # arbitrary assignments, which user must clean up. First assign the
            # required params, then the optional ones.
            pt_dict = {}
            for counter, p in enumerate(pt_names):
                try:
                    ppp = pp[counter]
                    if type(ppp) is ygPointView:
                        ppp = self.yg_glyph.points_to_labels(ppp.yg_point)
                    pt_dict[p] = ppp
                except IndexError as e:
                    # print("IndexError in make_macfunc_from_selection:")
                    # print(e)
                    break

            h = {"ptid": pt_dict, hint_type: other_params}
            yg_hint = ygHint(self.yg_glyph, h)

            self.sig_new_hint.emit(yg_hint)

    #
    # Event handlers
    #

    def mousePressEvent(self, event) -> None:
        # In ygGlyphScene
        super().mousePressEvent(event)
        modifier = QApplication.keyboardModifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._mouse_over_point(
                event.scenePos()
            ) and not self._mouse_over_hint(event.scenePos()):
                if (
                    modifier & Qt.KeyboardModifier.ShiftModifier
                ) != Qt.KeyboardModifier.ShiftModifier:
                    self.yg_selection._cancel_selection()
                self.dragBeginPoint = event.scenePos()
                self.selectionRect = SelectionRect(
                    QRectF(self.dragBeginPoint, QSizeF(0, 0))
                )
                self.addItem(self.selectionRect)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if self.selectionRect != None:
            thisx = abs(self.dragBeginPoint.x() - event.scenePos().x())
            thisy = abs(self.dragBeginPoint.y() - event.scenePos().y())
            if thisy > 4 or thisx > 4:
                self.selectionRect.setRect(self._adjust_rect(event.scenePos()))
                self.selectionRect.setPen(QPen(QColor("gray")))
                if self.selectionRect.isVisible():
                    self.selectionRect.update()
                else:
                    self.selectionRect.show()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self.selectionRect == None:
            return
        if (
            self.selectionRect.rect().isNull()
            or self.selectionRect.rect().height() == 0
            or self.selectionRect.rect().width() == 0
        ):
            self.removeItem(self.selectionRect)
            self.selectionRect = None
            return
        modifier = QApplication.keyboardModifiers()
        if (
            modifier & Qt.KeyboardModifier.ShiftModifier
        ) != Qt.KeyboardModifier.ShiftModifier:
            self.yg_selection._add_rect(self.selectionRect.rect(), False)
        else:
            self.yg_selection._toggle_rect(self.selectionRect.rect())
        self.removeItem(self.selectionRect)
        self.selectionRect = None

    def contextMenuEvent(self, event) -> None:
        """This seems horrible, but the most stable procedure (so far) seems
        to be to build every possible menu item and disable/hide the ones
        we don't want.

        Checklist of features:
            Toggle visibility of off-curve points: Done
            Toggle point numbers: Done
            Round touched point: Done
            Set control value: Done
            Set distance type for stem hints: Done
            Reverse stem hint: Done
            Additional parameters for functions and macros: Done
            Rearrange function/macro point params: Done
            Add point to function call: Not yet started
            Convert target point to target set in function/macro: Not yet started
            Set target and reference points for function/macro: Done bug disabled
            Make set: Doesn't yet work for functions/macros. Disabled as possibly not needed.
            Create function call: Done
            Create macro call: Done

        """

        cmenu = QMenu()
        selected_points = self.selected_objects(True)

        # This should be on a "view" top menu (when I get around to that)

        if self.off_curve_points_showing:
            toggle_off_curve_visibility = cmenu.addAction("Hide off-curve points")
        else:
            toggle_off_curve_visibility = cmenu.addAction("Show off-curve points")

        # Show/hide point numbers

        if self.point_numbers_showing:
            toggle_point_number_visibility = cmenu.addAction("Hide point numbers")
        else:
            toggle_point_number_visibility = cmenu.addAction("Show point numbers")

        # Set an override for Unicode category detection

        set_category_menu = cmenu.addMenu("Set category")
        category_actions = [set_category_menu.addAction("Default")]
        for v in unicode_cat_names.values():
            category_actions.append(set_category_menu.addAction(v))

        # "hint" will be None if the mouse pointer is not over a hint

        hint = self._mouse_over_hint(QPointF(event.scenePos()))
        try:
            ntype = hint_type_nums[hint.yg_hint.hint_type]
        except Exception:
            ntype = 10

        cv_anchor_action_list = []
        cv_stem_action_list = []
        point_param_list = []
        black_space = white_space = gray_space = None

        cmenu.addSeparator()

        # Round point (any ntype but 4)

        round_hint = QAction("Round target point", checkable=True)  # type: ignore
        cmenu.addAction(round_hint)
        if hint == None or ntype == 4:
            round_hint.setEnabled(False)
            round_hint.setVisible(False)
        else:
            if self._model_hint(hint).rounded:
                round_hint.setChecked(True)

        min_dist_action = QAction("Minimum distance", checkable=True)  # type: ignore
        cmenu.addAction(min_dist_action)
        if hint == None or ntype != 3:
            min_dist_action.setEnabled(False)
            min_dist_action.setVisible(False)
        else:
            mh = self._model_hint(hint)
            min_dist_action.setChecked(mh.min_dist)

        # Set control value for anchor hint (ntype == 0)

        set_anchor_cv = cmenu.addMenu("Set control value...")
        cv_list = self.yg_glyph.yg_font.cvt.get_list(
            self.yg_glyph,
            type="pos",
            axis=self.current_axis(),
            cat=self.yg_glyph.get_category(),
            suffix=self.yg_glyph.get_suffixes(),
        )
        cv_list.sort()
        cv_list = ["None", "Guess"] + cv_list

        for c in cv_list:
            ccv = QAction(c, self, checkable=True)  # type: ignore
            if hint != None:
                if ccv.text() == "None":
                    if hint.yg_hint.cv == None:
                        ccv.setChecked(True)
                else:
                    if c == hint.yg_hint.cv:
                        ccv.setChecked(True)
                set_anchor_cv.addAction(ccv)
                cv_anchor_action_list.append(ccv)

        if hint == None or ntype != 0:
            for c in cv_anchor_action_list:
                c.setEnabled(False)
                c.setVisible(False)
            a = set_anchor_cv.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        # Set control value for stem hint (ntype == 3)

        set_stem_cv = cmenu.addMenu("Set control value...")
        cv_list = self.yg_glyph.yg_font.cvt.get_list(
            self.yg_glyph,
            type="dist",
            axis=self.current_axis(),
            cat=self.yg_glyph.get_category(),
            suffix=self.yg_glyph.get_suffixes(),
        )
        cv_list.sort()
        cv_list = ["None", "Guess"] + cv_list
        # if len(cv_list) > 0:
        for c in cv_list:
            ccv = QAction(c, self, checkable=True)  # type: ignore
            if hint != None:
                if ccv.text() == "None":
                    if hint.yg_hint.cv == None:
                        ccv.setChecked(True)
                else:
                    if c == hint.yg_hint.cv:
                        ccv.setChecked(True)
                set_stem_cv.addAction(ccv)
                cv_stem_action_list.append(ccv)
        if hint == None or ntype != 3:
            for c in cv_stem_action_list:
                c.setEnabled(False)
                c.setVisible(False)
            a = set_stem_cv.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        # Color. We don't recommend setting the "color" bits directly,
        # but rather set "rel" to blackdist, whitedist, etc.

        hint_color_menu = cmenu.addMenu("Set distance type...")

        no_color_menu = hint == None or ntype != 3

        black_space = QAction("Black", self, checkable=True)  # type: ignore
        if hint != None:
            if hint.yg_hint.hint_type in ["stem", "blackdist"]:
                black_space.setChecked(True)
        hint_color_menu.addAction(black_space)
        if no_color_menu:
            black_space.setEnabled(False)
            black_space.setVisible(False)

        white_space = QAction("White", self, checkable=True)  # type: ignore
        if hint != None:
            if hint.yg_hint.hint_type == "whitedist":
                white_space.setChecked(True)
        hint_color_menu.addAction(white_space)
        if no_color_menu:
            white_space.setEnabled(False)
            white_space.setVisible(False)

        gray_space = QAction("Gray", self, checkable=True)  # type: ignore
        if hint != None:
            if hint.yg_hint.hint_type == "graydist":
                gray_space.setChecked(True)
        hint_color_menu.addAction(gray_space)
        if no_color_menu:
            gray_space.setEnabled(False)
            gray_space.setVisible(False)

        if no_color_menu:
            a = hint_color_menu.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        # Reverse a stem (simple arrow) hint

        reverse_hint = cmenu.addAction("Reverse hint")
        if hint == None or not ntype in [1, 3]:
            reverse_hint.setEnabled(False)
            reverse_hint.setVisible(False)

        # Other (non-point) parameters for functions and macros

        add_params = cmenu.addAction("Other parameters...")
        # Hide if no hint selected or hint is the wrong type or it has no non-
        # point parameters.
        if (
            hint == None
            or ntype != 4
            or len(
                ygCaller(
                    hint.yg_hint.hint_type, hint.yg_hint.name, self.yg_glyph.yg_font
                ).non_point_params()
            )
            == 0
        ):
            add_params.setEnabled(False)
            add_params.setVisible(False)

        # Rearrange point params for functions and macros

        disable_point_params = False
        # target_point will be ygPointMarker. The pt attribute for that is
        # a ygPointView object.
        target_point = None
        swap_old_name = None
        point_list = []
        try:
            # mouse_over_point actually returns a ygPointMarker.
            target_point = hint.mouse_over_point(QPointF(event.scenePos()))
            if hint.yg_hint.hint_type == "macro":
                mafu = ygMacro(hint.yg_hint.name, self.yg_glyph.yg_font)
                point_list = mafu.point_list
            else:
                mafu = ygFunction(hint.yg_hint.name, self.yg_glyph.yg_font)  # type: ignore
                point_list = mafu.point_list
            swap_old_name = target_point.name
            point_list.remove(swap_old_name)
        except Exception as e:
            disable_point_params = True
        point_param_menu = cmenu.addMenu("Point params")
        for p in point_list:
            point_param_list.append(point_param_menu.addAction(p))
        if hint == None or disable_point_params or ntype != 4 or len(point_list) == 0:
            for p in point_list:
                try:
                    p.setEnabled(False)
                    p.setVisible(False)
                except Exception as e:
                    pass
            a = point_param_menu.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        # Set a target or reference point for a function or macro. Only for use in ordering
        # hints: it has no effect on the rendering otherwise.

        # Is this stranded code? We're no longer offering "Make Set" via the context menu,
        # and the point of this code seems to be to set a variable that's never consulted.
        touched_point = None
        num_of_selected_points = len(selected_points)
        try:
            if num_of_selected_points >= 2:
                for p in selected_points:
                    if p.touched and len(p.owners) >= 1:
                        if hint_type_nums[p.owners[0].yg_hint.hint_type] in [1, 2]:
                            touched_point = p
                            break
        except Exception:
            pass

        # Functions and macros. Each is marked for which params are points, which are control
        # values, and which are others. For each count up the point params and show only those
        # for which that number falls within the range of possible point counts.

        functions = []
        all_functions = self.yg_glyph.yg_font.functions.keys()
        for f in all_functions:
            if (
                num_of_selected_points
                in ygFunction(f, self.yg_glyph.yg_font).point_params_range()
            ):
                functions.append(f)
        macros = []
        all_macros = self.yg_glyph.yg_font.macros.keys()
        for f in all_macros:
            if (
                num_of_selected_points
                in ygMacro(f, self.yg_glyph.yg_font).point_params_range()
            ):
                macros.append(f)

        function_menu = cmenu.addMenu("Functions")
        function_actions = []
        if len(functions) > 0:
            for f in functions:
                qa = QAction(f, self)
                function_actions.append(qa)
                function_menu.addAction(qa)
        else:
            a = function_menu.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        macro_menu = cmenu.addMenu("Macros")
        macro_actions = []
        if len(macros) > 0:
            for m in macros:
                qa = QAction(m, self)
                macro_actions.append(qa)
                macro_menu.addAction(qa)
        else:
            a = macro_menu.menuAction()
            a.setEnabled(False)
            a.setVisible(False)

        msg = None
        if len(selected_points) > 0:
            msg = "Name selected point"
        if len(selected_points) > 1:
            msg += "s"
        name_action = cmenu.addAction(msg)
        if msg == None:
            name_action.setEnabled(False)
            name_action.setVisible(False)

        action = cmenu.exec(event.screenPos())

        if action == toggle_off_curve_visibility:
            self.sig_off_curve_visibility.emit()
        if action == toggle_point_number_visibility:
            self.sig_toggle_point_numbers.emit()
        if action in category_actions:
            self.sig_set_category.emit(action.text())
        if hint and (action == reverse_hint):
            self.sig_reverse_hint.emit(hint.yg_hint)

        if hint and action in cv_anchor_action_list:
            try:
                if action.text() == "Guess":
                    action = self.yg_glyph.yg_font.cvt.get_closest_cv_action(
                        cv_anchor_action_list, self._model_hint(hint)
                    )
                self.sig_change_cv.emit({"hint": hint, "cv": action.text()})
            except Exception:
                self.yg_glyph.send_error_message(
                    {"msg": self.cv_error_msg, "mode": "console"}
                )
        if hint and action in cv_stem_action_list:
            try:
                if action.text() == "Guess":
                    action = self.yg_glyph.yg_font.cvt.get_closest_cv_action(
                        cv_stem_action_list, self._model_hint(hint)
                    )
                self.sig_change_cv.emit({"hint": hint, "cv": action.text()})
            except Exception:
                self.yg_glyph.send_error_message(
                    {"msg": self.cv_error_msg, "mode": "console"}
                )
        if hint and ntype == 3 and (action == black_space):
            self.sig_change_hint_color.emit({"hint": hint, "color": "blackdist"})
        if hint and ntype == 3 and (action == white_space):
            self.sig_change_hint_color.emit({"hint": hint, "color": "whitedist"})
        if hint and ntype == 3 and (action == gray_space):
            self.sig_change_hint_color.emit({"hint": hint, "color": "graydist"})
        if hint and ntype == 4 and (action == add_params):
            self.sig_edit_macfunc_params.emit(hint)
        if action in macro_actions:
            self.sig_make_macfunc.emit({"hint_type": "macro", "name": action.text()})
        if action in function_actions:
            self.sig_make_macfunc.emit({"hint_type": "function", "name": action.text()})
        if action in point_param_list:
            self.sig_swap_macfunc_points.emit(
                {"hint": hint, "new_pt": action.text(), "old_pt": swap_old_name}
            )
        if hint != None and action == round_hint:
            self.sig_round_hint.emit(hint)
        if hint != None and action == min_dist_action:
            self.sig_min_dist.emit(hint)
        if len(selected_points) > 0 and action == name_action:
            self.sig_name_points.emit(selected_points)


class ygGlyphView(QGraphicsView):
    """The container for the graphical hint editor.

    It holds and displays an instance of ygGlyphScene; it will hold various
    buttons and controls, plus (I hope) a preview of the hinted glyph.

    Parameters:
    yg_glyph_scene (ygGlyphScene): The QGraphicsScene that the user interacts with.

    font (ygModel.ygFont): The font object, including both a fontTools Font
    object and the yaml file (as read by the Python yaml module). Has
    convenience functions supplying various kinds of information about the
    font.

    parent: Is this used at all?
    """

    sig_goto = pyqtSignal(object)
    sig_toggle_drag_mode = pyqtSignal(object)

    def __init__(
        self,
        preferences: ygPreferences,
        yg_glyph_scene: ygGlyphScene,
        font: ygFont,
        parent=None,
    ) -> None:
        super(ygGlyphView, self).__init__(yg_glyph_scene, parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.yg_glyph_scene = yg_glyph_scene
        self.yg_font = font
        self.preferences = preferences
        self.visited_glyphs: Dict[str, ygGlyphScene] = {}
        self.drag_mode_backup = QGraphicsView.DragMode.NoDrag


    @pyqtSlot()
    def make_control_value(self) -> None:
        self.yg_glyph_scene.make_control_value()

    def setup_goto_signal(self, o: Callable) -> None:
        self.sig_goto.connect(o)

    def setup_toggle_drag_mode_signal(self, o: Callable) -> None:
        self.sig_toggle_drag_mode.connect(o)

    def _current_index(self) -> int:
        return self.yg_font.get_glyph_index(
            self.yg_glyph_scene.yg_glyph.gname, short_index=True
        )

    def go_to_glyph(self, g: str) -> None:
        self.preferences["top_window"].disconnect_editor_signals()
        try:
            self.yg_font.get_glyph_index(g, short_index=True)
            self.switch_to(g)
        except Exception as e:
            # print(e)
            self.yg_font.send_error_message(
                {"msg": "Can't load requested glyph.", "mode": "dialog"}
            )
        self.preferences["top_window"].connect_editor_signals()

    # sender returns None when we use the decorator. Rethink these signals?
    @pyqtSlot()
    def next_glyph(self) -> None:
        current_index = self._current_index()
        if current_index < len(self.yg_font.glyph_list) - 1:
            gname = self.yg_font.glyph_list[current_index + 1][1]
            self.preferences["top_window"].disconnect_editor_signals()
            self.switch_to(gname)
            self.preferences["top_window"].connect_editor_signals()

    @pyqtSlot()
    def previous_glyph(self) -> None:
        current_index = self._current_index()
        if current_index > 0:
            gname = self.yg_font.glyph_list[current_index - 1][1]
            self.preferences["top_window"].disconnect_editor_signals()
            self.switch_to(gname)
            self.preferences["top_window"].connect_editor_signals()

    def switch_from_font_viewer(self, gname: str) -> None:
        self.preferences["top_window"].disconnect_editor_signals()
        self.switch_to(gname)
        self.preferences["top_window"].connect_editor_signals()

    def switch_to(self, gname: str) -> None:
        self.yg_glyph_scene.reset_scale()
        self.yg_glyph_scene.yg_glyph.cleanup_glyph()
        # Store the current glyph if it is changed.
        if not self.yg_glyph_scene.yg_glyph.undo_stack.isClean():
            self.visited_glyphs[self.yg_glyph_scene.yg_glyph.gname] = self.yg_glyph_scene
        if gname in self.visited_glyphs:
            self.yg_glyph_scene = self.visited_glyphs[gname]
            new_glyph = self.yg_glyph_scene.yg_glyph
            # If we're returning to a glyph, we have to undo the cleanup
            # we did when we left it.
            new_glyph.undo_stack.setActive()
            new_glyph.restore_gsource()
        else:
            new_glyph = ygGlyph(self.preferences, self.yg_font, gname)
            self.yg_glyph_scene = ygGlyphScene(self.preferences, new_glyph, owner = self)
        self.preferences.set_current_glyph(self.yg_font.full_name, gname)
        self.setScene(self.yg_glyph_scene)
        self.centerOn(self.yg_glyph_scene.center_x, self.sceneRect().center().y())
        self.parent().parent().set_window_title()  # type: ignore
        ed = self.preferences.top_window().source_editor
        new_glyph.set_yaml_editor(ed)
        new_glyph.sig_hints_changed.emit(new_glyph.hints)

    @pyqtSlot()
    def guess_cv(self) -> None:
        try:
            self.yg_glyph_scene.guess_cv()
        except Exception:
            self.yg_font.send_error_message(
                {"msg": "Error while looking for a control value.", "mode": "console"}
            )

    @pyqtSlot(bool)
    def switch_to_x(self, checked: bool) -> None:
        if self.yg_glyph_scene:
            if checked and self.yg_glyph_scene.yg_glyph.axis != "x":
                # self.yg_glyph_scene.axis = "x"
                self.yg_glyph_scene.yg_glyph.switch_to_axis("x")
                win = self.parent().parent()
                win.set_window_title()  # type: ignore

    @pyqtSlot(bool)
    def switch_to_y(self, checked: bool) -> None:
        if self.yg_glyph_scene:
            if checked and self.yg_glyph_scene.yg_glyph.axis != "y":
                self.yg_glyph_scene.yg_glyph.switch_to_axis("y")
                win = self.parent().parent()
                win.set_window_title()  # type: ignore

    @pyqtSlot()
    def cleanup_yaml_code(self) -> None:
        self.yg_glyph_scene.yg_glyph.rebuild_current_block()

    @pyqtSlot()
    def make_hint_from_selection(self) -> None:
        menu_to_hint_type = {
            "Anchor (A)": "anchor",
            "Align (L)": "align",
            "Shift (H)": "shift",
            "Interpolate (I)": "interpolate",
            "Stem (T)": "graydist",
        }
        with_ctrl = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier
        ) == Qt.KeyboardModifier.ControlModifier
        with_shift = (
            QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        ) == Qt.KeyboardModifier.ShiftModifier
        self.yg_glyph_scene.make_hint_from_selection(
            menu_to_hint_type[self.sender().text()], ctrl=with_ctrl, shift=with_shift  # type: ignore
        )

    # Why does sender return None when we use the decorator? What's best in this
    # situation? Here are problems: sender_text param is not consulted. Should it be
    # omitted? Make sure params match, esp. if we change them.
    # @pyqtSlot(object)
    def zoom(self, sender_text: str) -> None:
        sender_text = self.sender().text()  # type: ignore
        if sender_text == "Original Size":
            self.yg_glyph_scene.set_zoom_factor(self.yg_glyph_scene.initial_zoom_factor)
        elif sender_text == "Zoom In":
            if self.yg_glyph_scene.zoom_factor <= 5.75:
                self.yg_glyph_scene.set_zoom_factor(self.yg_glyph_scene.zoom_factor + 0.25)
        elif sender_text == "Zoom Out":
            if self.yg_glyph_scene.zoom_factor >= 0.5:
                self.yg_glyph_scene.set_zoom_factor(self.yg_glyph_scene.zoom_factor - 0.25)
        self.centerOn(self.yg_glyph_scene.center_x, self.yg_glyph_scene.mid_point_y())

    def keyPressEvent(self, event) -> None:
        # 1. Delete key will delete any selected hints.
        # 2. Spacebar will shift Qt drag mode to ScrollHandDrag while it is
        #    down. For panning the screen.
        # 3. Hyphen (minus) removes a target point from a hint.
        # 4. Plus adds a point to a hint.
        if event.key() in [16777219, 16777223]:
            self.yg_glyph_scene.delete_selected_hints()
        elif event.key() == Qt.Key.Key_Plus:
            self.yg_glyph_scene.add_to_set()
        elif event.key() == Qt.Key.Key_Minus:
            self.yg_glyph_scene.delete_from_set()
        elif event.key() == 32 and not event.isAutoRepeat():
            self.drag_mode_backup = self.dragMode()
            if self.drag_mode_backup == QGraphicsView.DragMode.NoDrag:
                self.sig_toggle_drag_mode.emit(QGraphicsView.DragMode.ScrollHandDrag)

    def keyReleaseEvent(self, event):
        # Releasting spacebar shifts Qt drag mode back to whatever it was before
        # spacebar was pressed.
        if event.key() == 32 and not event.isAutoRepeat():
            if self.drag_mode_backup != self.dragMode():
                self.sig_toggle_drag_mode.emit(self.drag_mode_backup)


    def focusInEvent(self, event) -> None:
        self.yg_glyph_scene.yg_glyph.undo_stack.setActive(True)
