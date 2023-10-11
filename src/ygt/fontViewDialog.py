#from typing import Any, TypeVar, Union, Optional, List, Callable, overload, Iterable
from .freetypeFont import RENDER_LCD_1, RENDER_GRAYSCALE
from .ygModel import ygFont
from .ygLabel import ygLabel
from math import ceil
# import copy
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QRect
from PyQt6.QtWidgets import ( QWidget,
                              QGridLayout,
                              QVBoxLayout,
                              QScrollArea,
                              QHBoxLayout,
                              QLabel,
                              QLineEdit,
                              QPushButton )

from PyQt6.QtGui import QPainter, QColor, QPalette, QPixmap, QPen


FONT_VIEW_DARK_COMPOSITE = QColor(64, 42, 9)
FONT_VIEW_DARK_HINTED    = QColor(0, 0, 186, 128)
FONT_VIEW_DARK_UNHINTED  = QColor("black")
FONT_VIEW_COMPOSITE      = QColor(255, 239, 128)
FONT_VIEW_HINTED         = QColor(186, 255, 255, 128)
FONT_VIEW_UNHINTED       = QColor("white")
FONT_VIEW_HIGHLIGHT      = QColor(255, 0, 0, 128)

# The font view is now a window, not a dialog. "Dialog" is retained in the
# file name to avoid obscuring the history in the repository.

# A window that displays all the glyphs
# in the font, with those already hinted highlighted in blue and composites
# in gold. The current glyph is outlined in red. Current glyph is guaranteed to
# be visible when the font view window is first opened, but this is not necessarily
# true afterwards. Click on any glyph in the window to navigate to that glyph.


class fontViewWindow(QWidget):
    """ A window that displays all the glyphs
        in the font, with those already hinted highlighted in blue and composites
        in gold. The current glyph is outlined in red. Current glyph is guaranteed to
        be visible when the font view window is first opened, but this is not necessarily
        true afterwards. Click on any glyph in the window to navigate to that glyph.

        Glyphs in the font view are painted with Freetype rather than using system
        facilities. The Freetype font is the one already loaded by the ygFont object
        for the current window. The font view may employ hints already in the font, but
        it will not show the current hinting of the font.
    """
    sig_switch_to_glyph = pyqtSignal(object)

    def __init__(
            self, filename: str, yg_font: ygFont, glyph_list: list, top_window
        ) -> None:
        super().__init__()

        # Creat a search panel.
        self.search_panel = QHBoxLayout()
        self.search_panel.addWidget(QLabel("Filter:"))
        self.search_editor = QLineEdit()
        self.search_editor.setClearButtonEnabled(True)
        self.search_panel.addWidget(self.search_editor)
        self.submit_button = QPushButton("Submit")
        self.search_panel.addWidget(self.submit_button)

        # General initializations: state, data.
        self.valid = True
        self.top_window = top_window
        self.setWindowTitle("Font View")
        # We don't seem to have an actual use for this.
        # self.glyph_name_list = [g[1] for g in glyph_list]
        self.yg_font = yg_font
        self.face = self.yg_font.freetype_font
        self.face.set_size(24)
        if not self.face.valid:
            self.valid = False
            return
        # glyph_list and current_glyph_list are lists of tuples, with the first member a
        # Unicode number and the second the name of the glyph. fvc_index is a dict of
        # fontViewCell objects keyed by glyph name.
        self.glyph_list = self.current_glyph_list = glyph_list
        self.fvc_index = {}

        text_hsv_value = self.palette().color(QPalette.ColorRole.WindowText).value()
        bg_hsv_value = self.palette().color(QPalette.ColorRole.Base).value()
        self.dark_theme = text_hsv_value > bg_hsv_value

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self.fvp = fontViewPanel(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setWidget(self.fvp)
        self._layout.addLayout(self.search_panel)
        self._layout.addWidget(self.scroll_area)

        self.sig_switch_to_glyph.connect(
            self.top_window.glyph_pane.switch_from_font_viewer
        )
        self.submit_button.clicked.connect(self.got_search_term)
        self.search_editor.editingFinished.connect(self.got_search_term)

    def set_glyph_visible(self, g: str) -> None:
        """ Scrolls the window so that glyph g is visible. """
        gc = self.fvc_index[g]
        self.scroll_area.ensureWidgetVisible(gc, xMargin=0)

    def update_cell(self, g, force_redraw: bool = False):
        """ Requests an repainting of cell for glyph g.
            force_redraw makes the request more insistent.
        """
        gc = self.fvc_index[g]
        gc.make_pixmap(force_redraw = force_redraw)
        gc.update()

    def set_current_glyph(self, g: str, b: bool) -> None:
        """ Sets the current glyph to g. Forces repainting
            of the cell because we need to add a red border.
        """
        gc = self.fvc_index[g]
        gc._current_glyph = b
        self.update_cell(g, force_redraw = True)

    def clicked_glyph(self, g: str) -> None:
        """ When a cell is clicked, emit a signal requesting
            that that become the current glyph.
        """
        self.sig_switch_to_glyph.emit(g)

    @pyqtSlot()
    def got_search_term(self):
        self.fvp.makeFilteredLayout(self.search_editor.text())


class fontViewPanel(QWidget):
    def __init__(self, dialog: fontViewWindow) -> None:
        super().__init__()
        self.dialog = dialog
        self._layout = QGridLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.makeFreshLayout(self.dialog.current_glyph_list, delete_old = False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        if dialog.dark_theme:
            self.setStyleSheet("background-color: black;")
        else:
            self.setStyleSheet("background-color: white;")

    def makeFreshLayout(self, glyph_list: list, delete_old: bool = True) -> None:
        """Given a list of glyphs, causes those glyphs to be displayed in
           the font window. That is, it filters the font's glyph list to
           reflect a search result.

           params:

           glyph_list: A list of tuples: (Unicode, glyph_name)

           delete_old: whether to delete (or hide, actually) the cells
           currently displayed in the font view window. Should be false
           when initializing the window, true when displaying the result
           of a searchk.
        """
        # glyph_list has got to be a list of tuples (Unicode, name)
        if delete_old:
            while self._layout.count() > 0:
                i = self._layout.itemAt(0).widget()
                self._layout.removeWidget(i)
                i.hide()
        numchars = len(glyph_list)
        cols = 10
        rows = ceil(numchars / 10)
        self.setMinimumSize(cols * 36, rows * 36)
        self._layout.setHorizontalSpacing(0)
        self._layout.setVerticalSpacing(0)
        row = col = 0
        self._layout.setRowMinimumHeight(row, 36)
        for g in glyph_list:
            gn = g[1]
            try:
                fvc = self.dialog.fvc_index[gn]
            except KeyError:
                fvc = fontViewCell(self.dialog, g)
                self.dialog.fvc_index[gn] = fvc
            self._layout.addWidget(fvc, row, col)
            if delete_old:
                fvc.setVisible(True)
            col += 1
            if col == 10:
                row += 1
                self._layout.setRowMinimumHeight(row, 36)
                col = 0


    def makeFilteredLayout(self, s: str) -> None:
        """Given a string, this searches the font's glyph list and passes
            the result to makeFreshLayout, which rebuilds the display of
            glyphs. If the string is empty, it displays the whole font.

            param:

            s: the string to search for.
        """
        if len(s):
            search_result = [i for i in self.dialog.glyph_list if s in i[1]]
        else:
            search_result = self.dialog.glyph_list
        self.makeFreshLayout(search_result)
        if len(s) and len(search_result):
            self.dialog.scroll_area.ensureWidgetVisible(self._layout.itemAt(0).widget(), xMargin=0)


class fontViewCell(ygLabel):
    def __init__(self, dialog: fontViewWindow, glyph: list) -> None:
        super().__init__()
        self.dialog = dialog
        self.glyph = glyph[1]
        self.setFixedSize(36, 36)
        self.has_hints = False
        self.pixmap = None
        self._current_glyph = False
        self.make_pixmap()

    #@property
    #def current_glyph(self) -> bool:
    #    return self._current_glyph
    
    #@current_glyph.setter
    #def current_glyph(self, b: bool) -> None:
    #    self._current_glyph = b

    def make_pixmap(self, force_redraw: bool = False) -> None:
        """ Make a pixmap for this cell and draw the glyph on it.
            This makes for rapid painting and fast scrolling. If there's
            a change, simply repaint the pixmap and call update() on the
            cell.
        """
        # Test to see if we really need to paint the pixmap.
        is_composite = self.dialog.yg_font.is_composite(self.glyph)
        has_hints_now = self.dialog.yg_font.has_hints(self.glyph)
        if self.pixmap != None and self.has_hints == has_hints_now and not force_redraw:
            return
        else:
            self.has_hints = has_hints_now

        if self.pixmap == None:
            self.pixmap = QPixmap(36,36)

        fill_color = None
        if self.dialog.dark_theme:
            if is_composite:
                fill_color = FONT_VIEW_DARK_COMPOSITE
            elif self.has_hints:
                fill_color = FONT_VIEW_DARK_HINTED
            else:
                fill_color = FONT_VIEW_DARK_UNHINTED
        else:
            if is_composite:
                fill_color = FONT_VIEW_COMPOSITE
            elif self.has_hints:
                fill_color = FONT_VIEW_HINTED
            else:
                fill_color = FONT_VIEW_UNHINTED
        self.pixmap.fill(fill_color)

        painter = QPainter(self.pixmap)

        if self._current_glyph:
            highlight_color = FONT_VIEW_HIGHLIGHT
            r = QRect(1, 1, 34, 34)
            qp = QPen(highlight_color)
            qp.setWidth(2)
            painter.setPen(qp)
            painter.drawRect(r)

        ind = self.dialog.face.name_to_index(self.glyph.encode(encoding="utf-8"))
        self.dialog.face.set_render_mode(RENDER_LCD_1)
        self.dialog.face.set_char(ind)
        baseline = (
            round((36 - self.dialog.face.face_height) / 2) + self.dialog.face.ascender
        )
        xpos = round((36 - self.dialog.face.advance) / 2)
        self.dialog.face.draw_char(
            painter,
            xpos,
            baseline,
            dark_theme = self.dialog.dark_theme
        )

        painter.end()

        self.setPixmap(self.pixmap)

    def mousePressEvent(self, event) -> None:
        self.dialog.clicked_glyph(self.glyph)
