from .freetypeFont import freetypeFont, RENDER_LCD_1, RENDER_GRAYSCALE
from fontTools import subset
from .ygModel import ygFont
from math import ceil
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QScrollArea, QLabel
from PyQt6.QtGui import QPainter, QColor, QPalette, QPixmap
from tempfile import SpooledTemporaryFile
import copy


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
        #if self.yg_font.source_file.source_type == "yaml":
        #    self.face = freetypeFont(filename, size=24, render_mode=RENDER_LCD_1)
        #else:
        #    temp_font = copy.deepcopy(self.yg_font.preview_font)
        #    tf = SpooledTemporaryFile(max_size=3000000, mode='b')
        #    options = subset.Options(glyph_names=True)
        #    options.layout_features = []
        #    subsetter = subset.Subsetter(options)
        #    subsetter.populate(glyphs=self.glyph_name_list)
        #    subsetter.subset(temp_font)
        #    temp_font.save(tf, 1)
        #    tf.seek(0)
        #    self.face = freetypeFont(tf, size=24, render_mode=RENDER_LCD_1)
        #    tf.close()
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
        scroll_area = QScrollArea()
        scroll_area.setWidget(fvp)
        self._layout.addWidget(scroll_area)

        self.sig_switch_to_glyph.connect(
            self.top_window.glyph_pane.switch_from_font_viewer
        )

    def update_cell(self, g):
        gc = self.glyph_index[g]
        gc.make_pixmap()
        gc.update()

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


class fontViewCell(QLabel):
    def __init__(self, dialog: fontViewWindow, glyph: list) -> None:
        super().__init__()
        self.dialog = dialog
        self.glyph = glyph[1]
        self.setFixedSize(36, 36)
        self.has_hints = False
        self.pixmap = None
        self.make_pixmap()

    def make_pixmap(self) -> None:
        """ Make a pixmap for this cell and draw the glyph on it.
            This makes for rapid painting and fast scrolling. If there's
            a change, simply repaint the pixmap and call update() on the
            cell.
        """
        # Test to see if we really need to paint the pixmap.
        is_composite = self.dialog.yg_font.is_composite(self.glyph)
        has_hints_now = self.dialog.yg_font.has_hints(self.glyph)
        if self.pixmap != None and self.has_hints == has_hints_now:
            return
        else:
            self.has_hints = has_hints_now

        if self.pixmap == None:
            self.pixmap = QPixmap(36,36)

        fill_color = None
        alpha = 0.88
        if self.dialog.dark_theme:
            if is_composite:
                # fill_color = QColor(169, 169, 169)
                fill_color = QColor(64, 42, 9)
                alpha = 0.96
            elif self.has_hints:
                fill_color = QColor(0, 0, 186, 128)
                alpha = 0.95
            else:
                fill_color = QColor("black")
                alpha = 0.95
        else:
            if is_composite:
                # fill_color = QColor(211, 211, 211)
                fill_color = QColor(255, 239, 128)
            elif self.has_hints:
                fill_color = QColor(186, 255, 255, 128)
            else:
                fill_color = QColor("white")
        self.pixmap.fill(fill_color)

        painter = QPainter(self.pixmap)

        # print("fontViewCell: " + self.glyph)
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
