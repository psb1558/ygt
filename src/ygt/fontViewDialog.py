from .freetypeFont import freetypeFont, RENDER_GRAYSCALE
from fontTools import subset
from .ygModel import ygFont
from math import ceil
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtWidgets import QWidget, QDialog, QGridLayout, QVBoxLayout, QScrollArea
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor, QPalette
import numpy
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
        if self.yg_font.source_file.source_type == "yaml":
            self.face = freetypeFont(filename, size=24, render_mode=RENDER_GRAYSCALE)
        else:
            temp_font = copy.deepcopy(self.yg_font.preview_font)
            tf = SpooledTemporaryFile(max_size=3000000, mode='b')
            options = subset.Options(glyph_names=True)
            options.layout_features = []
            subsetter = subset.Subsetter(options)
            subsetter.populate(glyphs=self.glyph_name_list)
            subsetter.subset(temp_font)
            temp_font.save(tf, 1)
            tf.seek(0)
            self.face = freetypeFont(tf, size=24, render_mode=RENDER_GRAYSCALE)
            tf.close()
        if not self.face.valid:
            self.valid = False
            return
        self.glyph_list = glyph_list

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

    def clicked_glyph(self, g: str) -> None:
        self.sig_switch_to_glyph.emit(g)


class fontViewPanel(QWidget):
    def __init__(self, dialog: fontViewWindow) -> None:
        super().__init__()
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
            self._layout.addWidget(fontViewCell(dialog, g), row, col)
            col += 1
            if col == 10:
                row += 1
                self._layout.setRowMinimumHeight(row, 36)
                col = 0
        if dialog.dark_theme:
            self.setStyleSheet("background-color: black;")
        else:
            self.setStyleSheet("background-color: white;")


class fontViewCell(QWidget):
    def __init__(self, dialog: fontViewWindow, glyph: list) -> None:
        super().__init__()
        self.dialog = dialog
        self.glyph = glyph[1]
        self.setFixedSize(36, 36)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        dark_theme = self.dialog.dark_theme

        brush = QBrush()
        if self.dialog.yg_font.has_hints(self.glyph):
            if dark_theme:
                brush.setColor(QColor(0, 0, 186, 128))
            else:
                brush.setColor(QColor(186, 255, 255, 128))
        else:
            if dark_theme:
                brush.setColor(QColor("black"))
            else:
                brush.setColor(QColor("white"))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)

        ind = self.dialog.face.name_to_index(self.glyph)
        self.dialog.face.set_char(ind)
        baseline = (
            round((36 - self.dialog.face.face_height) / 2) + self.dialog.face.ascender
        )
        xpos = round((36 - self.dialog.face.advance) / 2)
        self.dialog.face.draw_char(painter, xpos, baseline, dark_theme = dark_theme)

        painter.end()

    def mousePressEvent(self, event) -> None:
        self.dialog.clicked_glyph(self.glyph)
