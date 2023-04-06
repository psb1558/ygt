from .freetypeFont import freetypeFont, RENDER_GRAYSCALE, RENDER_LCD_1, RENDER_LCD_2
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt6.QtGui import QPainter, QBrush, QColor
from PyQt6.QtCore import Qt, QRect, pyqtSignal, pyqtSlot, QLine


PREVIEW_WIDTH = 450
PREVIEW_HEIGHT = 700
STRING_PREVIEW_HEIGHT = 150
PREVIEW_HORI_MARGIN = 25
PREVIEW_VERT_MARGIN = 50


class ygPreviewContainer(QWidget):
    def __init__(self, preview, string_preview):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(preview)
        self.layout.addWidget(string_preview)
        self.setLayout(self.layout)


class ygPreview(QWidget):
    sig_preview_paint_done = pyqtSignal(object)

    def __init__(self, top_window):
        super().__init__()
        self.top_window = top_window
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
        self.total_height = 0
        # self.baseline_position = 0
        # The top of the grid should be offset this far from self.vertical_margin
        self.top_grid_offset = 0
        # The pixels of the glyph start this far down.
        self.top_char_margin = 0
        self.show_grid = True
        # Two- or three-dimensional array shaped by numpy.
        self.Z = []
        self.instance_dict = None
        self.instance = None
        self.colors = self.mk_color_list()
        self.render_mode = RENDER_LCD_1
        self.hinting_on = True
        self.paintEvent = self.paintEvent_b

    def set_up_signal(self, func):
        self.sig_preview_paint_done.connect(func)

    def mk_color_list(self):
        """Pre-build a list of grayscale colors--for the big preview."""
        l = [0] * 256
        for count, c in enumerate(l):
            l[count] = QColor(101, 53, 15, count)
        return l

    def fetch_glyph(self, font, glyph_index):
        """Get a temporary FreeType font, then build the specified glyph.

        params:

        font: see freetypeFont for details.

        glyph_index: Index in the font of the glyph to build.

        """
        self.glyph_index = glyph_index
        self.face = freetypeFont(font)
        self._build_glyph()

    def _build_glyph(self):
        """Shape the point array and figure some key values."""
        if self.face == None:
            return False
        self.face.set_render_mode(self.render_mode)
        self.face.set_hinting_on(self.hinting_on)
        self.face.set_size(self.char_size)
        self.face.set_instance(self.instance)
        self.face.set_char(self.glyph_index)
        gdata = self.face._get_bitmap_metrics()

        ft_bitmap = self.face.glyph_slot.bitmap
        ft_width = ft_bitmap.width
        ft_rows = ft_bitmap.rows
        self.current_glyph_height = ft_rows
        # ft_pitch  = ft_bitmap.pitch
        self.bitmap_top = self.face.glyph_slot.bitmap_top
        self.grid_height = self.face.ascender + abs(self.face.descender)
        self.total_height = self.grid_height
        top_offset = self.face.ascender - self.bitmap_top
        if top_offset < 0:
            self.top_grid_offset = abs(top_offset)
            self.total_height += self.top_grid_offset
            self.top_char_margin = 0
        else:
            self.top_grid_offset = 0
            self.top_char_margin = top_offset
        glyph_descent = ft_rows - self.bitmap_top
        if glyph_descent < 0:
            if abs(glyph_descent) > abs(self.face.descender):
                self.total_height += abs(glyph_descent) - abs(self.face.descender)

        self.pixel_size = self.max_pixel_size
        char_width = ft_width
        if self.render_mode != RENDER_GRAYSCALE:
            char_width = ft_width / 3
        preview_display_width = PREVIEW_WIDTH - (PREVIEW_HORI_MARGIN * 2)
        if char_width * self.pixel_size > preview_display_width:
            self.pixel_size = round(preview_display_width / char_width)
        preview_display_height = PREVIEW_HEIGHT - (PREVIEW_VERT_MARGIN * 2)
        if self.total_height * self.pixel_size > preview_display_height:
            self.pixel_size = round(preview_display_height / self.total_height)
        if self.render_mode == RENDER_LCD_2:
            nn = self.pixel_size % 3
            if nn != 0:
                self.pixel_size -= nn
            if self.pixel_size < 3:
                self.pixel_size = 3
        else:
            if self.pixel_size < 1:
                self.pixel_size = 1
        self.Z = self.face.mk_array(gdata, self.render_mode)
        return True

    @pyqtSlot()
    def toggle_show_hints(self):
        self.hinting_on = not self.hinting_on
        self.face.set_hinting_on(self.hinting_on)
        # self._build_glyph()
        self.update()

    @pyqtSlot()
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        # self._build_glyph()
        self.update()

    @pyqtSlot()
    def render1(self):
        self.set_render_mode(RENDER_GRAYSCALE)

    @pyqtSlot()
    def render2(self):
        self.set_render_mode(RENDER_LCD_1)

    @pyqtSlot()
    def render3(self):
        self.set_render_mode(RENDER_LCD_2)

    def set_render_mode(self, m):
        self.render_mode = m
        if self.render_mode == RENDER_GRAYSCALE:
            self.paintEvent = self.paintEvent_a
        elif self.render_mode == RENDER_LCD_1:
            self.paintEvent = self.paintEvent_b
        else:
            self.paintEvent = self.paintEvent_c
        # self._build_glyph()
        self.update()

    def set_size(self, n):
        n = int(n)
        if self.face != None:
            try:
                self.char_size = n
                if self.char_size < 10:
                    self.char_size = 10
                self.face.set_size(self.char_size)
            except Exception as e:
                return
            # self.label.setText(str(self.char_size) + "ppem")
            self.set_label_text()
            # self._build_glyph()
            self.update()

    def resize_by(self, n):
        if self.face != None and self.glyph_index != 0:
            # self.char_size += n
            # self.set_label_text()
            self.set_size(self.char_size + n)
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
        self.face.set_instance(self.instance)
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
        left = self.horizontal_margin
        height = self.grid_height
        baseline = self.face.ascender

        pen = painter.pen()
        pen.setWidth(1)
        line_length = self.face.glyph_slot.bitmap.width * self.pixel_size
        if self.render_mode != RENDER_GRAYSCALE:
            line_length = int(line_length / 3)

        for i, r in enumerate(range(height)):
            if i == baseline:
                pen.setColor(QColor("red"))
            else:
                pen.setColor(QColor(50, 50, 50, 50))
            painter.setPen(pen)
            painter.drawLine(QLine(left, top, left + line_length, top))
            top += self.pixel_size

        if self.render_mode in [RENDER_GRAYSCALE, RENDER_LCD_1]:
            grid_width = self.face.glyph_slot.bitmap.width + 1
            if self.render_mode == RENDER_LCD_1:
                grid_width = round(grid_width / 3) + 1
            y_top = self.vertical_margin + (self.top_grid_offset * self.pixel_size)
            y_bot = top - self.pixel_size
            pen.setColor(QColor(50, 50, 50, 50))
            painter.setPen(pen)
            for i, r in enumerate(range(grid_width)):
                painter.drawLine(QLine(left, y_top, left, y_bot))
                left += self.pixel_size

    def paintEvent_a(self, event):
        """Paint grayscale glyph."""
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor("white"))
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
        """Paint subpixel rendering with solid pixels."""
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor("white"))
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
        """Paint subpixel rendering with rgb pixel trios."""
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(QColor("white"))
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
                        qc = QColor(255 - elem, 0, 0)
                    elif n == 1:
                        qc = QColor(0, 255 - elem, 0)
                    elif n == 2:
                        qc = QColor(0, 0, 255 - elem)
                    qr = QRect(
                        int(xposition),
                        int(yposition),
                        int(self.pixel_size / 3),
                        int(self.pixel_size),
                    )
                    painter.fillRect(qr, qc)
                    xposition += self.pixel_size / 3
            yposition += self.pixel_size
            xposition = self.horizontal_margin
        if self.show_grid:
            self.draw_grid(painter)
        painter.end()
        self.sig_preview_paint_done.emit(None)


class ygStringPreviewPanel(QWidget):
    sig_go_to_glyph = pyqtSignal(object)

    def __init__(self, yg_preview, top_window):
        super().__init__()
        self.yg_preview = yg_preview
        self.top_window = top_window
        self.face = self.yg_preview.face
        self._text = ""
        self.minimum_x = PREVIEW_WIDTH
        self.minimum_y = 200
        self.setMinimumSize(self.minimum_x, self.minimum_y)
        self.paintEvent = self.paintEvent_a
        self.rect_list = []

    def set_go_to_signal(self, func):
        self.sig_go_to_glyph.connect(func)

    def set_face(self, face):
        self.face = face

    def set_text(self, t):
        self._text = t

    def string_to_glyph_list(self, s):
        """Get a list of glyph names needed for string s."""
        yg_font = self.top_window.glyph_pane.viewer.yg_glyph.yg_font
        result = []
        for c in s:
            try:
                if not c in result:
                    result.append(yg_font.unicode_to_name[ord(c)])
            except Exception:
                result.append(".notdef")
        return result

    def _fill_background(self, painter):
        brush = QBrush()
        brush.setColor(QColor("white"))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        rect = QRect(0, 0, self.width(), self.height())
        painter.fillRect(rect, brush)

    def paintEvent_a(self, event):
        painter = QPainter(self)
        self._fill_background(painter)
        if self.face == None:
            painter.end()
            return
        if not self.yg_preview:
            return
        self.face.reset_rect_list()
        xposition = 25
        yposition = 66
        for s in range(10, 100):
            self.face.set_params(
                glyph=self.yg_preview.glyph_index,
                render_mode=self.yg_preview.render_mode,
                hinting_on=self.yg_preview.hinting_on,
                size=s,
                instance=self.yg_preview.instance,
            )
            advance = self.face.draw_char(
                painter, xposition, yposition, spacing_mark=True
            )
            xposition += advance
            if xposition + advance > (PREVIEW_WIDTH - 50):
                if yposition == 66:
                    xposition = 25
                    yposition = 133
                else:
                    break
        self.rect_list = self.face.rect_list
        painter.end()

    def paintEvent_b(self, event):
        painter = QPainter(self)
        self._fill_background(painter)
        if not self.yg_preview:
            return
        xposition = 25
        yposition = 66
        self.face = self.yg_preview.face
        self.rect_list = self.face.draw_string(
            painter, self._text, xposition, yposition, x_limit=PREVIEW_WIDTH - 50
        )
        painter.end()

    def mousePressEvent(self, event):
        qp = event.position()
        x = int(qp.x())
        y = int(qp.y())
        rr = None
        for r in self.rect_list:
            if r.contains(x, y):
                rr = r
                break
        if rr != None:
            if self.paintEvent == self.paintEvent_a:
                self.yg_preview.set_size(rr.size)
            else:
                self.sig_go_to_glyph.emit(rr.gname.decode())


class ygStringPreview(QWidget):
    sig_string_changed = pyqtSignal(object)

    def __init__(self, yg_preview, top_window):
        super().__init__()
        self.yg_preview = yg_preview
        self.top_window = top_window

        self._layout = QVBoxLayout()

        self.panel = ygStringPreviewPanel(yg_preview, top_window)

        self.button_widget = QWidget()
        self.button_widget_layout = QHBoxLayout()
        self.button_widget_layout.addWidget(QLabel("Text:"))
        self.qle = QLineEdit()
        self.button_widget_layout.addWidget(self.qle)
        self.submit_button = QPushButton("Submit")
        self.button_widget_layout.addWidget(self.submit_button)
        self.button_widget.setLayout(self.button_widget_layout)

        self.submit_button.clicked.connect(self.got_string)
        self.sig_string_changed.connect(top_window.preview_current_glyph)
        self.qle.editingFinished.connect(self.got_string)

        self._layout.addWidget(self.panel)
        self._layout.addWidget(self.button_widget)

        self.setLayout(self._layout)

    def set_go_to_signal(self, func):
        self.panel.set_go_to_signal(func)

    def set_string_preview(self):
        self.panel.paintEvent = self.panel.paintEvent_b

    def set_size_array(self):
        self.panel.paintEvent = self.panel.paintEvent_a

    def set_face(self, f):
        if self.panel != None:
            self.panel.face = f

    def got_string(self):
        self.panel.set_text(self.qle.text())
        self.sig_string_changed.emit(self.panel._text)
