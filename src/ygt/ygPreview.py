import numpy
import os
import freetype
from freetype import FT_LOAD_RENDER, FT_LOAD_TARGET_LCD 
from PyQt6.QtWidgets import (
    QWidget,
    QLabel
)
from PyQt6.QtGui import (
    QPainter,
    QBrush,
    QColor
)
from PyQt6.QtCore import (
    Qt,
    QRect,
    pyqtSlot
)

class ygPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.face = None
        self.hinting = "on"
        self.glyph_index = 0
        self.char_size = 40
        self.label = QLabel()
        self.label.setStyleSheet("QLabel {background-color: transparent; color: red;}")
        self.label.setText(str(self.char_size) + "ppem")
        self.label.setParent(self)
        self.label.move(50, 30)
        self.setMinimumSize(800, 1000)
        self.vertical_margin = 50
        self.horizontal_margin = 50
        self.max_pixel_size = 10
        self.pixel_size = 10
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.colors = self.mk_color_list()

    def mk_color_list(self):
        l = [0] * 256
        for count, c in enumerate(l):
            l[count] = QColor(101,53,15,count)
        return l

    def fetch_glyph(self, filename, glyph_index):
        """ For use only with temporary fonts! This removes the file from which
            the glyph has been fetched.
        """
        self.glyph_index = glyph_index
        self.face = freetype.Face(filename)
        os.remove(filename)
        self._build_glyph()

    def _build_glyph(self):
        # flags = FT_LOAD_RENDER | FT_LOAD_TARGET_LCD 
        self.face.set_char_size(self.char_size * 64)
        if self.instance != None:
            self.face.set_var_named_instance(self.instance)
        # self.face.load_glyph(self.glyph_index, flags=flags)
        self.face.load_glyph(self.glyph_index)
        ft_bitmap = self.face.glyph.bitmap
        print(ft_bitmap.buffer)
        ft_width  = self.face.glyph.bitmap.width
        ft_rows   = self.face.glyph.bitmap.rows
        ft_pitch  = self.face.glyph.bitmap.pitch
        self.pixel_size = self.max_pixel_size
        if ft_width * self.pixel_size > 700:
            self.pixel_size = round(700/ft_width)
        if ft_rows * self.pixel_size > 700:
            self.pixel_size = round(700/ft_rows)
        if self.pixel_size < 1:
            self.pixel_size = 1
        data = []
        for i in range(ft_rows):
            data.extend(ft_bitmap.buffer[i*ft_pitch:i*ft_pitch+ft_width])
        self.Z = numpy.array(data,dtype=numpy.ubyte).reshape(ft_rows, ft_width)

    def toggle_hinting(self):
        """ This can't be used right now, since including the no hinting flag
            in a call to load_glyph causes a crash.
        """
        if self.glyph_index != 0 and self.face != None:
            if self.hinting == "on":
                self.hinting = "off"
            else:
                self.hinting = "on"
            self._build_glyph()
            self.update()

    def set_size(self, n):
        if self.face != None and self.glyph_index != 0:
            try:
                self.char_size = int(n)
                if self.char_size < 10:
                    self.char_size = 10
            except Exception as e:
                return
            # self.label.setText(str(self.char_size) + "ppem")
            self.set_label_text()
            self._build_glyph()
            self.update()

    def resize_by(self, n):
        if self.face != None and self.glyph_index != 0:
            # self.label.setText(str(self.char_size) + "ppem")
            self.char_size += n
            self.set_label_text()
            self._build_glyph()
            self.update()

    def set_label_text(self):
        t = str(self.char_size) + "ppem"
        if self.instance != None:
            t += " — " + self.instance
        self.label.setText(t)
        self.label.adjustSize()

    def add_instances(self, instances):
        self.instance_dict = instances

    @pyqtSlot()
    def set_instance(self):
        self.instance = self.sender().text()
        self.set_label_text()
        self._build_glyph()
        self.update()        

    @pyqtSlot()
    def bigger_one(self):
        self.resize_by(1)

    @pyqtSlot()
    def bigger_ten(self):
        self.resize_by(10)

    @pyqtSlot()
    def smaller_one(self):
        if self.char_size > 10:
            self.resize_by(-1)

    @pyqtSlot()
    def smaller_ten(self):
        if self.char_size > 20:
            self.resize_by(-10)

    def paintEvent(self, event):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor('white'))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        if len(self.Z) == 0:
            painter.end()
            return
        xposition = self.horizontal_margin
        yposition = self.vertical_margin
        for row in self.Z:
            for col in row:
                qr = QRect(xposition, yposition, self.pixel_size, self.pixel_size)
                # qb = QBrush(QColor(101,53,15,col))
                painter.fillRect(qr, self.colors[col])
                xposition += self.pixel_size
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        painter.end()

class ygSizeLabel(QLabel):
    def __init__():
        super().__init__()
        self.current_size = 40
