import numpy
import freetype
from freetype import (
    FT_LOAD_RENDER,
    FT_LOAD_TARGET_LCD,
    FT_LOAD_NO_HINTING,
    FT_LOAD_NO_AUTOHINT
)
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
    pyqtSlot,
    QLine
)

class ygPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.face = None
        self.hinting = "on"
        self.glyph_index = 0
        self.char_size = 30
        self.label = QLabel()
        self.label.setStyleSheet("QLabel {background-color: transparent; color: red;}")
        self.label.setText(str(self.char_size) + "ppem")
        self.label.setParent(self)
        self.label.move(50, 30)
        self.setMinimumSize(600, 1000)
        self.vertical_margin = 50
        self.horizontal_margin = 50
        self.max_pixel_size = 12
        self.pixel_size = 12
        self.current_glyph_height = 0
        self.bitmap_top = 0
        self.show_grid = True
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.colors = self.mk_color_list()
        self.render_mode = 2
        self.hinting_on = True
        self.paintEvent = self.paintEvent_b

    def mk_color_list(self):
        l = [0] * 256
        for count, c in enumerate(l):
            l[count] = QColor(101,53,15,count)
        return l

    def fetch_glyph(self, font, glyph_index):
        """ The font has to be a handle to an open temporary file. Once
            we've gotten the glyph from it, we close it and it disappears.
        """
        self.glyph_index = glyph_index
        font.seek(0)
        self.face = freetype.Face(font)
        font.close()
        self._build_glyph()

    def _build_glyph(self):
        if self.render_mode > 1:
            flags = FT_LOAD_RENDER | FT_LOAD_TARGET_LCD 
        else:
            flags = 4
        if not self.hinting_on:
            flags = flags | FT_LOAD_NO_HINTING | FT_LOAD_NO_AUTOHINT
        self.face.set_char_size(self.char_size * 64)
        if self.instance != None:
            self.face.set_var_named_instance(self.instance)
        self.face.load_glyph(self.glyph_index, flags=flags)
        ft_bitmap = self.face.glyph.bitmap
        ft_width  = self.face.glyph.bitmap.width
        ft_rows   = self.face.glyph.bitmap.rows
        self.current_glyph_height = ft_rows
        ft_pitch  = self.face.glyph.bitmap.pitch
        self.bitmap_top = self.face.glyph.bitmap_top
        self.pixel_size = self.max_pixel_size
        char_width = ft_width
        if self.render_mode > 1:
            char_width = ft_width / 3
        if char_width * self.pixel_size > 500:
            self.pixel_size = round(500/char_width)
        if ft_rows * self.pixel_size > 500:
            self.pixel_size = round(500/ft_rows)
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

    @pyqtSlot()
    def toggle_show_hints(self):
        self.hinting_on = not self.hinting_on
        self._build_glyph()
        self.update()

    @pyqtSlot()
    def toggle_grid(self):
        self.show_grid = not self.show_grid
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

    def instance_list(self):
        l = []
        if self.instance_dict:
            kk = self.instance_dict.keys()
            for k in kk:
                l.append(k)
        return l

    @pyqtSlot()
    def next_instance(self):
        if self.instance and self.instance_dict:
            kk = self.instance_dict.keys()
            il = self.instance_list()
            i = il.index(self.instance)
            try:
                k = il[i + 1]
            except Exception:
                k = il[0]
            self.instance = k
            self._set_instance()
            
    @pyqtSlot()
    def prev_instance(self):
        if self.instance and self.instance_dict:
            kk = self.instance_dict.keys()
            il = self.instance_list()
            i = il.index(self.instance)
            try:
                k = il[i - 1]
            except Exception:
                k = il[-1]
            self.instance = k
            self._set_instance()

    @pyqtSlot()
    def set_instance(self):
        self.instance = self.sender().text()
        self._set_instance()

    def _set_instance(self):
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

    def draw_grid(self, painter):
        if self.pixel_size < 5:
            return
        top = self.vertical_margin
        left= self.horizontal_margin
        height = self.current_glyph_height
        if self.bitmap_top > self.current_glyph_height:
            height = self.bitmap_top
        height += 1
        baseline = self.bitmap_top
        pen = painter.pen()
        pen.setWidth(1)
        line_length = (self.face.glyph.bitmap.width * self.pixel_size)
        if self.render_mode > 1:
            line_length = int(line_length / 3)
        for i, r in enumerate(range(height)):
            if i == baseline:
                pen.setColor(QColor("red"))
            else:
                pen.setColor(QColor(50,50,50,50))
            painter.setPen(pen)
            painter.drawLine(QLine(left, top, left + line_length, top))
            top += self.pixel_size
        if self.render_mode < 3:
            grid_width = self.face.glyph.bitmap.width + 1
            if self.render_mode == 2:
                grid_width = round(grid_width / 3) + 1
            y_top = self.vertical_margin
            y_bot = top - self.pixel_size
            pen.setColor(QColor(50,50,50,50))
            painter.setPen(pen)
            for i, r in enumerate(range(grid_width)):
                painter.drawLine(QLine(left, y_top, left, y_bot))
                left += self.pixel_size


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
        for row in self.Z:
            for col in row:
                qr = QRect(xposition, yposition, self.pixel_size, self.pixel_size)
                # qb = QBrush(QColor(101,53,15,col))
                painter.fillRect(qr, self.colors[col])
                xposition += self.pixel_size
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        if self.show_grid:
            self.draw_grid(painter)
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
        for row in self.Z:
            for col in row:
                rgb = []
                for elem in col:
                    rgb.append(elem)
                qc = QColor(255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
                qr = QRect(xposition, yposition, self.pixel_size, self.pixel_size)
                painter.fillRect(qr, qc)
                xposition += self.pixel_size
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        if self.show_grid:
            self.draw_grid(painter)
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
        if self.show_grid:
            self.draw_grid(painter)
        painter.end()

class ygSizeLabel(QLabel):
    def __init__():
        super().__init__()
        self.current_size = 40
