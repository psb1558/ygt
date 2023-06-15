from .freetypeFont import RENDER_LCD_1, RENDER_GRAYSCALE
from .ygModel import ygFont
from .ygLabel import ygLabel
from math import ceil
from PyQt6.QtCore import pyqtSignal, QRect
from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QScrollArea
from PyQt6.QtGui import QPainter, QColor, QPalette, QPixmap, QPen


FONT_VIEW_DARK_COMPOSITE = QColor(64, 42, 9)
FONT_VIEW_DARK_HINTED    = QColor(0, 0, 186, 128)
FONT_VIEW_DARK_UNHINTED  = QColor("black")
FONT_VIEW_COMPOSITE      = QColor(255, 239, 128)
FONT_VIEW_HINTED         = QColor(186, 255, 255, 128)
FONT_VIEW_UNHINTED       = QColor("white")
FONT_VIEW_HIGHLIGHT      = QColor(255, 0, 0, 128)


# A window (not a dialog, despite the filename, retained to avoid complicating
# the history in the repository) that displays all the non-composite glyphs
# in the font, with those already hinted highlighted in blue. Click on any
# glyph in the window to navigate to that glyph.


class fontViewWindow(QWidget):
    """This window presents a grid showing all the glyphs in glyph_list--
    that is, those glyphs that are not made of composites. This display
    indicates which characters are hinted (their cells have blue backgrounds).
    It also works as a navigation aid: just click on any character.

    """
    sig_switch_to_glyph = pyqtSignal(object)

    def __init__(
            self, filename: str, yg_font: ygFont, glyph_list: list, top_window
        ) -> None:
        super().__init__()
        self.valid = True
        self.top_window = top_window
        self.setWindowTitle("Font View")
        self.glyph_name_list = []
        for g in glyph_list:
            self.glyph_name_list.append(g[1])
        self.yg_font = yg_font
        self.face = self.yg_font.freetype_font
        self.face.set_size(24)
        if not self.face.valid:
            self.valid = False
            return
        self.glyph_list = glyph_list
        self.glyph_index = {}

        text_hsv_value = self.palette().color(QPalette.ColorRole.WindowText).value()
        bg_hsv_value = self.palette().color(QPalette.ColorRole.Base).value()
        self.dark_theme = text_hsv_value > bg_hsv_value

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        fvp = fontViewPanel(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(fvp)
        self._layout.addWidget(self.scroll_area)

        self.sig_switch_to_glyph.connect(
            self.top_window.glyph_pane.switch_from_font_viewer
        )

    def set_glyph_visible(self, g: str) -> None:
        gc = self.glyph_index[g]
        self.scroll_area.ensureWidgetVisible(gc, xMargin=0)

    def update_cell(self, g, force_redraw: bool = False):
        gc = self.glyph_index[g]
        gc.make_pixmap(force_redraw = force_redraw)
        gc.update()

    def set_current_glyph(self, g: str, b: bool) -> None:
        gc = self.glyph_index[g]
        gc._current_glyph = b
        self.update_cell(g, force_redraw = True)
        #gc.make_pixmap()
        #gc.update()

    def clicked_glyph(self, g: str) -> None:
        self.sig_switch_to_glyph.emit(g)


class fontViewPanel(QWidget):
    def __init__(self, dialog: fontViewWindow) -> None:
        super().__init__()
        self.dialog = dialog
        gl = dialog.glyph_list
        numchars = len(gl)
        cols = 10
        rows = ceil(numchars / 10)
        self.setMinimumSize(cols * 36, rows * 36)
        self._layout = QGridLayout()
        self._layout.setHorizontalSpacing(0)
        self._layout.setVerticalSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        row = 0
        col = 0
        self._layout.setRowMinimumHeight(row, 36)
        for g in gl:
            fvc = fontViewCell(dialog, g)
            self._layout.addWidget(fvc, row, col)
            self.dialog.glyph_index[g[1]] = fvc
            col += 1
            if col == 10:
                row += 1
                self._layout.setRowMinimumHeight(row, 36)
                col = 0
        if dialog.dark_theme:
            self.setStyleSheet("background-color: black;")
        else:
            self.setStyleSheet("background-color: white;")


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
