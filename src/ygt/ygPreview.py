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
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout
)
from PyQt6.QtGui import (
    QPainter,
    QBrush,
    QColor,
    QPen
)
from PyQt6.QtCore import (
    Qt,
    QRect,
    pyqtSignal,
    pyqtSlot,
    QLine
)


PREVIEW_WIDTH         = 450
PREVIEW_HEIGHT        = 700
STRING_PREVIEW_HEIGHT = 150
PREVIEW_HORI_MARGIN   = 25
PREVIEW_VERT_MARGIN   = 50


class ygPreviewContainer(QWidget):
    def __init__(self, preview, string_preview):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(preview)
        self.layout.addWidget(string_preview)
        self.setLayout(self.layout)



class ygPreview(QWidget):

    sig_preview_paint_done = pyqtSignal(object)

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
        self.minimum_x = PREVIEW_WIDTH
        self.minimum_y = PREVIEW_HEIGHT
        self.setMinimumSize(self.minimum_x, self.minimum_y)
        self.vertical_margin = PREVIEW_VERT_MARGIN
        self.horizontal_margin = PREVIEW_HORI_MARGIN
        self.max_pixel_size = 12
        self.pixel_size = 12
        # absolute height of the glyph, from top pixel to bottom pixel.
        self.current_glyph_height = 0
        # Corresponds to font's ascender number
        self.ascender = 0
        # Corresponds to the font's descender number
        self.descender = 0
        # The height of the glyph above the baseline. Should be able to subtract
        # this from self.ascender to get where on the grid we should start laying
        # down pixels. If the result of the subtraction is negative, we need to
        # display grid above the ascender number.
        self.bitmap_top = 0
        self.grid_height = 0
        # self.baseline_position = 0
        # The top of the grid should be offset this far from self.vertical_margin
        self.top_grid_offset = 0
        # The pixels of the glyph start this far down.
        self.top_char_margin = 0
        self.show_grid = True
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.colors = self.mk_color_list()
        self.render_mode = 2
        self.hinting_on = True
        self.paintEvent = self.paintEvent_b

    def set_up_signal(self, func):
        self.sig_preview_paint_done.connect(func)

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
        if self.face == None:
            return False
        self.face.set_char_size(self.char_size * 64)
        self.ascender = round(self.face.size.ascender/64)
        self.descender = round(self.face.size.descender/64)
        if self.instance != None:
            self.face.set_var_named_instance(self.instance)
        self.face.load_glyph(self.glyph_index, flags=flags)
        ft_bitmap = self.face.glyph.bitmap
        ft_width  = self.face.glyph.bitmap.width
        ft_rows   = self.face.glyph.bitmap.rows
        self.current_glyph_height = ft_rows
        ft_pitch  = self.face.glyph.bitmap.pitch
        self.bitmap_top = self.face.glyph.bitmap_top
        self.grid_height = self.ascender + abs(self.descender)
        top_offset = self.ascender - self.bitmap_top
        if top_offset < 0:
            self.top_grid_offset = abs(top_offset)
            self.top_char_margin = 0
        else:
            self.top_grid_offset = 0
            self.top_char_margin = top_offset
        self.pixel_size = self.max_pixel_size
        char_width = ft_width
        if self.render_mode > 1:
            char_width = ft_width / 3
        preview_display_width = PREVIEW_WIDTH - (PREVIEW_HORI_MARGIN * 2)
        if char_width * self.pixel_size > preview_display_width:
            self.pixel_size = round(preview_display_width/char_width)
        preview_display_height = PREVIEW_HEIGHT - (PREVIEW_VERT_MARGIN * 2)
        if ft_rows * self.pixel_size > preview_display_height:
            self.pixel_size = round(preview_display_height/ft_rows)
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
        return True

    @pyqtSlot()
    def toggle_show_hints(self):
        self.hinting_on = not self.hinting_on
        # self._build_glyph()
        self.update()

    @pyqtSlot()
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        # self._build_glyph()
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
        # self._build_glyph()
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
            # self._build_glyph()
            self.update()

    def resize_by(self, n):
        if self.face != None and self.glyph_index != 0:
            # self.label.setText(str(self.char_size) + "ppem")
            self.char_size += n
            self.set_label_text()
            # self._build_glyph()
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
        # self._build_glyph()
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
        top = self.vertical_margin + (self.top_grid_offset * self.pixel_size)
        left= self.horizontal_margin
        # height = self.current_glyph_height
        height = self.grid_height
        #if self.bitmap_top > self.current_glyph_height:
        #    height = self.bitmap_top
        #height += 1
        # baseline = self.bitmap_top
        baseline = self.ascender
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
            y_top = self.vertical_margin + (self.top_grid_offset * self.pixel_size)
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
        if not self._build_glyph():
            painter.end()
            return
        if len(self.Z) == 0:
            painter.end()
            return
        xposition = self.horizontal_margin
        yposition = self.vertical_margin + (self.top_char_margin * self.pixel_size)
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
        self.sig_preview_paint_done.emit(None)

    def paintEvent_b(self, event):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor('white'))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        if not self._build_glyph():
            painter.end()
            return
        if len(self.Z) == 0:
            painter.end()
            return
        xposition = self.horizontal_margin
        yposition = self.vertical_margin + (self.top_char_margin * self.pixel_size)
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
        self.sig_preview_paint_done.emit(None)

    def paintEvent_c(self, event):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor('white'))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        if not self._build_glyph():
            painter.end()
            return
        if len(self.Z) == 0:
            painter.end()
            return
        xposition = self.horizontal_margin
        yposition = self.vertical_margin + (self.top_char_margin * self.pixel_size)
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
        self.sig_preview_paint_done.emit(None)

class ygStringPreviewPanel(QWidget):
    def __init__(self, yg_preview, top_window):
        super().__init__()
        self.yg_preview = yg_preview
        # self.yg_font = top_window.glyph_pane.viewer.yg_glyph.yg_font
        # self.yg_font = None
        self.top_window = top_window
        self.face = None
        self.hinting = "on"
        self._text = ""
        self.char_size = self.yg_preview.char_size
        self.minimum_x = PREVIEW_WIDTH
        self.minimum_y = 200
        self.setMinimumSize(self.minimum_x, self.minimum_y)
        self.vertical_margin = 25
        self.horizontal_margin = 50
        self.current_glyph_height = 0
        # Corresponds to font's ascender number
        self.ascender = 0
        # Corresponds to the font's descender number
        self.descender = 0
        # The height of the glyph above the baseline. Should be able to subtract
        # this from self.ascender to get where on the grid we should start laying
        # down pixels. If the result of the subtraction is negative, we need to
        # display grid above the ascender number.
        self.bitmap_top = 0
        self.top_char_margin = 0
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.render_mode = 2
        self.hinting_on = True
        self.paintEvent = self.paintEvent_a

    def set_text(self, t):
        self._text = t
        if self._text != None and len(self._text) > 0:
            self.sig_have_text.emit(self.string_to_glyph_list(t))
            pass
        else:
            # build the default display (a cascade of the current character,
            # borrowing the Face from self.yg_preview, if possible)
            pass

    def string_to_glyph_list(self, s):
        yg_font = self.top_window.glyph_pane.viewer.yg_glyph.yg_font
        result = []
        for c in s:
            try:
                if not c in result:
                    result.append(yg_font.unicode_to_name[ord(c)])
            except Exception:
                result.append(".notdef")
        return result

    def paintEvent_a(self, event):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor('white'))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)
        if self.yg_preview.face == None:
            painter.end()
            return
        if not self.yg_preview:
            return
        # return
        xposition = 25
        yposition = 66
        for s in range(10,100):
            advance   = ygLetter(painter,
                                 self.yg_preview.face,
                                 self.yg_preview.glyph_index,
                                 s,
                                 xposition,
                                 yposition,
                                 self.yg_preview.render_mode,
                                 self.yg_preview.hinting_on).draw()
            xposition += advance
            if xposition + advance > (PREVIEW_WIDTH - 50):
                if yposition == 66:
                    xposition = 25
                    yposition = 133
                else:
                    break
        painter.end()


class ygLetter:
    def __init__(self, painter, face, glyph_index, size, base_x, base_y, render_mode, hinting_on):
        self.hinting_on = hinting_on
        self.render_mode = render_mode
        self.painter = painter
        self.size = size
        self.base_x = base_x
        self.base_y = base_y
        face.set_char_size(size * 64)
        self.ascender = round(face.size.ascender/64)
        if render_mode > 1:
            self.flags = FT_LOAD_RENDER | FT_LOAD_TARGET_LCD 
        else:
            self.flags = 4
        if not self.hinting_on:
            self.flags = self.flags | FT_LOAD_NO_HINTING | FT_LOAD_NO_AUTOHINT
        face.load_glyph(glyph_index, flags=self.flags)
        self.glyph_slot = face.glyph
        self.bitmap = self.glyph_slot.bitmap
        self.width = self.glyph_slot.bitmap.width
        self.rows = self.glyph_slot.bitmap.rows
        self.pitch = self.glyph_slot.bitmap.pitch
        self.bitmap_top = self.glyph_slot.bitmap_top
        self.bitmap_left = self.glyph_slot.bitmap_left
        self.top_offset = self.ascender - self.bitmap_top
        # print("advance.x: " + str(self.glyph_slot.advance.x))
        # print("linearHoriAdvance: " + str(self.glyph_slot.linearHoriAdvance))
        self.advance = round(self.glyph_slot.advance.x / 64)
        self.glyph_top = self.base_y - self.bitmap_top
        if self.render_mode == 1:
            self.draw = self.draw_a
        else:
            self.draw = self.draw_b

    def draw_a(self):
        # print("draw_a")
        data = []
        for i in range(self.rows):
            data.extend(self.bitmap.buffer[i*self.pitch:i*self.pitch+self.width])
        Z = numpy.array(data,dtype=numpy.ubyte).reshape(self.rows, self.width)
        qp = QPen(QColor('black'))
        qp.setWidth(1)
        # self.painter.setPen(qp)
        y = self.glyph_top
        for row in Z:
            x = self.base_x + self.bitmap_left
            for col in row:
                qp.setColor(QColor(0,0,0,col))
                self.painter.setPen(qp)
                self.painter.drawPoint(x, y)
                x += 1
            y += 1
        return self.advance

    def draw_b(self):
        # print("draw_b")
        data = []
        for i in range(self.rows):
            data.extend(self.bitmap.buffer[i*self.pitch:i*self.pitch+self.width])
        Z = numpy.array(data,dtype=numpy.ubyte).reshape(self.rows, int(self.width/3), 3)
        y = self.glyph_top
        qp = QPen(QColor('black'))
        qp.setWidth(1)
        white_color = QColor("white")
        for row in Z:
            x = self.base_x + self.bitmap_left
            for col in row:
                rgb = []
                for elem in col:
                    rgb.append(elem)
                qc = QColor(255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
                if qc != white_color:
                    qp.setColor(qc)
                    self.painter.setPen(qp)
                    self.painter.drawPoint(x, y)
                x += 1
            y += 1
        return self.advance



class ygStringPreview(QWidget):
    def __init__(self, yg_preview, top_window):
        super().__init__()
        self.yg_preview = yg_preview
        self.top_window = top_window

        self._layout = QVBoxLayout()

        self.panel = ygStringPreviewPanel(yg_preview, top_window)

        self.button_widget = QWidget()
        self.button_widget_layout = QHBoxLayout()
        self.button_widget_layout.addWidget(QLabel("Text:"))
        self.button_widget_layout.addWidget(QLineEdit())
        self.submit_button = QPushButton("Submit")
        self.button_widget_layout.addWidget(self.submit_button)
        self.button_widget.setLayout(self.button_widget_layout)

        self.submit_button.clicked.connect(top_window.string_preview_text)

        self._layout.addWidget(self.panel)
        self._layout.addWidget(self.button_widget)

        self.setLayout(self._layout)
    



class ygSizeLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.current_size = 40
