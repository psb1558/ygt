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
        self.max_pixel_size = 12
        self.pixel_size = 12
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.colors = self.mk_color_list()
        self.render_mode = 2
        self.paintEvent = self.paintEvent_b

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
        print(filename)
        filename.seek(0)
        self.face = freetype.Face(filename)
        # os.remove(filename)
        filename.close()
        self._build_glyph()

    def _build_glyph(self):
        if self.render_mode > 1:
            flags = FT_LOAD_RENDER | FT_LOAD_TARGET_LCD 
        else:
            flags = 4
        self.face.set_char_size(self.char_size * 64)
        if self.instance != None:
            self.face.set_var_named_instance(self.instance)
        # Experiment with default flags = 4
        self.face.load_glyph(self.glyph_index, flags=flags)
        print(self.face.charmap.index)
        # self.face.load_glyph(self.glyph_index)
        ft_bitmap = self.face.glyph.bitmap
        # print(ft_bitmap.buffer)
        ft_width  = self.face.glyph.bitmap.width
        ft_rows   = self.face.glyph.bitmap.rows
        ft_pitch  = self.face.glyph.bitmap.pitch
        self.pixel_size = self.max_pixel_size
        char_width = ft_width
        if self.render_mode > 1:
            char_width = ft_width / 3
        if char_width * self.pixel_size > 700:
            self.pixel_size = round(700/char_width)
        if ft_rows * self.pixel_size > 700:
            self.pixel_size = round(700/ft_rows)
        if self.render_mode == 3:
            nn = self.pixel_size % 3
            if nn != 0:
                self.pixel_size -= nn
            if self.pixel_size < 3:
                self.pixel_size = 3
        else:
            if self.pixel_size < 1:
                self.pixel_size = 1
        data = []
        for i in range(ft_rows):
            data.extend(ft_bitmap.buffer[i*ft_pitch:i*ft_pitch+ft_width])
        if self.render_mode > 1:
            self.Z = numpy.array(data,dtype=numpy.ubyte).reshape(ft_rows, int(ft_width/3), 3)
        else:
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

    @pyqtSlot()
    def render1(self):
        self.set_render_mode(1)

    @pyqtSlot()
    def render2(self):
        self.set_render_mode(2)

    @pyqtSlot()
    def render3(self):
        self.set_render_mode(3)

    def set_render_mode(self, m):
        self.render_mode = m
        if self.render_mode == 1:
            self.paintEvent = self.paintEvent_a
        elif self.render_mode == 2:
            self.paintEvent = self.paintEvent_b
        else:
            self.paintEvent = self.paintEvent_c
        self._build_glyph()
        self.update()

    def set_size(self, n):
        n = int(n)
        if self.face != None and self.glyph_index != 0:
            try:
                self.char_size = n
                if self.char_size < 12:
                    self.char_size = 12
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

    def paintEvent_a(self, event):
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
        print("pixel-size: " + str(self.pixel_size))
        for row in self.Z:
            for col in row:
                qr = QRect(xposition, yposition, self.pixel_size, self.pixel_size)
                # qb = QBrush(QColor(101,53,15,col))
                painter.fillRect(qr, self.colors[col])
                xposition += self.pixel_size
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        painter.end()

    def paintEvent_b(self, event):
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
        print("pixel-size: " + str(self.pixel_size))
        for row in self.Z:
            for col in row:
                rgb = []
                for elem in col:
                    rgb.append(elem)
                qc = QColor(255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
                qr = QRect(xposition, yposition, self.pixel_size, self.pixel_size)
                #qb = QBrush(qc)
                #painter.setBrush(qb)
                # painter.fillRect(qr, self.colors[col])
                painter.fillRect(qr, qc)
                xposition += self.pixel_size
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        painter.end()

    def paintEvent_c(self, event):
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
        print("pixel-size: " + str(self.pixel_size))
        for row in self.Z:
            for col in row:
                for n, elem in enumerate(col):
                    if n == 0:
                        qc = QColor(255-elem, 0, 0)
                    elif n == 1:
                        qc = QColor(0, 255-elem, 0)
                    elif n == 2:
                        qc = QColor(0, 0, 255-elem)
                    qr = QRect(int(xposition), int(yposition), int(self.pixel_size/3), int(self.pixel_size))
                    painter.fillRect(qr, qc)
                    xposition += self.pixel_size/3
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        painter.end()

class ygSizeLabel(QLabel):
    def __init__():
        super().__init__()
        self.current_size = 40
