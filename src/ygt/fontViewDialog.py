from freetype import *
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
        self.setWindowTitle("Font View")
        self.face = freetype.Face(filename)
        self.face.set_char_size(24*64)
        self.yg_font = yg_font
        self.glyph_list = glyph_list
        self.top_window = top_window

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
        self.glyph_index = dialog.yg_font.get_glyph_index(self.glyph)

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

        face = self.dialog.face
        face.load_glyph(self.glyph_index)
        ft_slot = face.glyph
        ft_bitmap = face.glyph.bitmap
        ft_width  = face.glyph.bitmap.width
        ft_rows   = face.glyph.bitmap.rows
        ft_pitch  = face.glyph.bitmap.pitch
        self.pixel_size = 1
        data = []
        for i in range(ft_rows):
            data.extend(ft_bitmap.buffer[i*ft_pitch:i*ft_pitch+ft_width])
        Z = numpy.array(data,dtype=numpy.ubyte).reshape(ft_rows, ft_width)

        if len(Z) == 0:
            painter.end()
            return

        yposition = int((36 - ft_rows) / 2)
        xposition = int((36 - ft_width) / 2)

        pixmap_index = 0
        qp = QPen(QColor('black'))
        qp.setWidth(1)
        painter.setPen(qp)
        for row in Z:
            px = xposition
            for col in row:
                qp.setColor(QColor(0,0,0,col))
                painter.setPen(qp)
                painter.drawPoint(px, yposition)
                px += 1
            yposition += 1
        painter.end()

    def mousePressEvent(self, event):
        self.dialog.clicked_glyph(self.glyph)
