from .freetypeFont import freetypeFont, RENDER_GRAYSCALE
from math import ceil
from PyQt6.QtCore import (Qt, QRect, pyqtSignal)
from PyQt6.QtWidgets import (QWidget, QDialog, QGridLayout, QVBoxLayout, QScrollArea)
from PyQt6.QtGui import (QPainter, QBrush, QPen, QColor)
import numpy

class fontViewDialog(QDialog):
    """ This dialog presents a grid showing all the glyphs in glyph_list--
        that is, those glyphs that are not made of composites. This display
        indicates which characters are hinted (their cells have blue backgrounds).
        It also works as a navigation aid: just click on any character.

    """

    sig_switch_to_glyph = pyqtSignal(object)

    def __init__(self, filename, yg_font, glyph_list, top_window):
        super().__init__()
        self.top_window = top_window
        self.setWindowTitle("Font View")
        self.face = freetypeFont(filename, size=24, render_mode=RENDER_GRAYSCALE)
        self.yg_font = yg_font
        self.glyph_list = glyph_list

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        fvp = fontViewPanel(self)
        scroll_area = QScrollArea()
        scroll_area.setWidget(fvp)
        self.layout.addWidget(scroll_area)

        self.sig_switch_to_glyph.connect(self.top_window.glyph_pane.switch_from_font_viewer)

    def clicked_glyph(self, g):
        self.sig_switch_to_glyph.emit(g)


class fontViewPanel(QWidget):
    def __init__(self, dialog):
        super().__init__()
        gl = dialog.glyph_list
        numchars = len(gl)
        cols = 10
        rows = ceil(numchars / 10)
        self.setMinimumSize(cols*36,rows*36)
        self.layout = QGridLayout()
        self.layout.setHorizontalSpacing(0)
        self.layout.setVerticalSpacing(0)
        self.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        row = 0
        col = 0
        self.layout.setRowMinimumHeight(row, 36)
        for g in gl:
            self.layout.addWidget(fontViewCell(dialog, g), row, col)
            col += 1
            if col == 10:
                row += 1
                self.layout.setRowMinimumHeight(row, 36)
                col = 0
        self.setStyleSheet("background-color: white;")

class fontViewCell(QWidget):
    def __init__(self, dialog, glyph):
        super().__init__()
        self.dialog = dialog
        self.glyph = glyph[1]
        self.setFixedSize(36,36)

    def paintEvent(self, event):
        painter = QPainter(self)

        brush = QBrush()
        if self.dialog.yg_font.has_hints(self.glyph):
            brush.setColor(QColor(186,255,255,128))
        else:
            brush.setColor(QColor('white'))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)

        self.dialog.face.set_char(self.dialog.face.name_to_index(self.glyph))
        baseline = round((36 - self.dialog.face.face_height) / 2) + self.dialog.face.ascender
        xpos = round((36 - self.dialog.face.advance) / 2)
        self.dialog.face.draw_char(painter, xpos, baseline)

        painter.end()

    def mousePressEvent(self, event):
        self.dialog.clicked_glyph(self.glyph)
