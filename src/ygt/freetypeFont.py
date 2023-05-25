from typing import Optional
import freetype as ft # type: ignore
import numpy
import copy
from tempfile import SpooledTemporaryFile
from PyQt6.QtGui import QColor, QPen, QImage, QRegion, QBitmap, QPixmap, QPainter
from PyQt6.QtCore import QRect, QLine

RENDER_GRAYSCALE = 1
RENDER_LCD_1 = 2
RENDER_LCD_2 = 3


class ygLetterBox:
    def __init__(self, x1, y1, x2, y2, glyph_index=0, gname=None, size=30):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.glyph_index = glyph_index
        self.size = size
        self.gname = gname

    def contains(self, x, y):
        return x >= self.x1 and x <= self.x2 and y >= self.y1 and y <= self.y2


class freetypeFont:
    """Holds a FreeType font. It will also keep the metrics and supply
    key info, e.g. the ascender, or the top of a bitmap for a specific
    character. It will keep a record of the current render state, and
    it will draw a character (given a QPainter).

    params:

    font: must be either a SpooledTemporaryFile or a str (filename).

    size (int): The initial size of the characters (in pixels per em).
    Default is 30.

    Minimal example, to draw a character in the default size:
      ftf = freetypeFont("Elstob-Regular.ttf")
      # The GID of the desired character
      ftf.set_char(60)
      ftf.draw_char(painter)
    """

    def __init__(
        self,
        font: SpooledTemporaryFile | str,
        size: int = 30,
        render_mode: int = RENDER_LCD_1,
        hinting_on: bool = True,
        instance: str = None,
        keep_open: bool = False
    ) -> None:
        self.valid = True
        try:
            if type(font) is SpooledTemporaryFile:
                font.seek(0)
                self.face = ft.Face(font)
                if not keep_open:
                    font.close()
            else:
                self.face = ft.Face(font)

        except Exception as e:
            print("Error in freetypeFont.__init__:")
            print(e.args)
            print(e)
            self.valid = False
            return
        self.char_size = size * 64
        self.size = 30
        self.ascender = 0
        self.descender = 0
        self.face_height = 0
        self.advance = 0
        self.glyph_slot: Optional[ft.GlyphSlot] = None
        self.glyph_index = 0
        self.bitmap_top = 0
        self.bitmap_left = 0
        self.top_offset = 0
        self.instance = instance
        self.hinting_on = hinting_on
        self.bw_colors = self.mk_bw_color_list()
        self.bw_colors_dark = self.mk_bw_color_list(dark = True)
        self.draw_char = self._draw_char_lcd
        self.set_render_mode(render_mode)
        self.face.set_char_size(self.char_size)
        self._get_font_metrics()
        self.last_glyph_index = None
        self.rect_list: list = []

    def mk_bw_color_list(self, dark: bool = False) -> list:
        l = [0] * 256
        for count, c in enumerate(l):
            if dark:
                l[count] = QColor(255, 255, 255, count)
            else:
                l[count] = QColor(0, 0, 0, count)
        return l

    def reset_rect_list(self):
        self.rect_list = []

    def set_params(
        self, glyph=None, render_mode=None, hinting_on=None, size=None, instance=None
    ):
        if render_mode != None:
            self.set_render_mode(render_mode)
        if hinting_on == None:
            self.set_hinting_on(hinting_on)
        if instance != None:
            self.set_instance(instance)
        if size != None:
            self.set_size(size)
        if glyph != None:
            self.set_char(glyph)

    def set_render_mode(self, render_mode):
        self.render_mode = render_mode
        if self.render_mode == RENDER_LCD_1:
            self.draw_char = self._draw_char_lcd
        elif self.render_mode == RENDER_LCD_2:
            self.draw_char = self._draw_char_lcd
        else:
            self.draw_char = self._draw_char_grayscale

    def set_hinting_on(self, h):
        self.hinting_on = h

    def toggle_hinting(self):
        self.hinting_on = not self.hinting_on

    def set_size(self, i):
        self.size = i
        self.face.set_char_size(i * 64)
        self._get_font_metrics()

    def font_to_pixels(self, val):
        return round(ft.FT_MulDiv(val, self.face.size.x_scale, 0x10000) / 64)

    def _get_font_metrics(self):
        """Populate class variables with basic metrics info for this font
        at the current size.
        """
        self.ascender = round(self.face.size.ascender / 64)
        self.descender = round(self.face.size.descender / 64)
        self.face_height = self.ascender + abs(self.descender)

    def set_instance(self, instance):
        self.instance = instance
        if self.instance != None:
            self.face.set_var_named_instance(self.instance)

    def set_char(self, glyph_index):
        """Load a glyph (given its index in the font), generating the appropriate
        kind of bitmap, and populate class variables with glyph-specific metrics
        info.
        """
        self.glyph_index = glyph_index
        flags = 4  # i.e. grayscale
        if self.render_mode in [RENDER_LCD_1, RENDER_LCD_2]:
            flags = ft.FT_LOAD_RENDER | ft.FT_LOAD_TARGET_LCD
        if not self.hinting_on:
            flags = flags | ft.FT_LOAD_NO_HINTING | ft.FT_LOAD_NO_AUTOHINT
        self.face.load_glyph(self.glyph_index, flags=flags)
        self.glyph_slot = self.face.glyph
        self.advance = round(self.glyph_slot.advance.x / 64)
        self.bitmap_top = self.glyph_slot.bitmap_top
        self.bitmap_left = self.glyph_slot.bitmap_left
        self.top_offset = self.ascender - self.bitmap_top

    def _get_bitmap_metrics(self):
        r = {}
        r["width"] = self.glyph_slot.bitmap.width
        r["rows"] = self.glyph_slot.bitmap.rows
        r["pitch"] = self.glyph_slot.bitmap.pitch
        r["bitmap_top"] = self.glyph_slot.bitmap_top
        r["bitmap_left"] = self.glyph_slot.bitmap_left
        r["advance"] = round(self.glyph_slot.advance.x / 64)
        return r

    def mk_array(self, metrics, render_mode):
        data = []
        rows = metrics["rows"]
        width = metrics["width"]
        pitch = metrics["pitch"]
        for i in range(rows):
            data.extend(self.glyph_slot.bitmap.buffer[i * pitch : i * pitch + width])
        if render_mode == RENDER_GRAYSCALE:
            return numpy.array(data, dtype=numpy.ubyte).reshape(rows, width)
        else:
            return numpy.array(data, dtype=numpy.ubyte).reshape(rows, int(width / 3), 3)


    def _draw_char_lcd(
            self,
            painter,
            x,
            y,
            spacing_mark = False,
            dark_theme = False,
            is_target = False,
            x_offset = 0,
            y_offset = 0
        ):
        """Draws a bitmap with subpixel rendering (suitable for an lcd screen)

        Params:

        painter (QPainter): a Qt tool to draw with

        x (int): The left origin of the glyph

        y (int): The baseline

        spacing_mark: Make nonspacing mark a spacing char.

        dark_theme: true if letters lighter than background.

        is_target: Whether this glyph matches the one in the big preview.

        """
        gdata = self._get_bitmap_metrics()

        # Get the Freetype bitmap into a numpy array and get dimensions.
        Z = self.mk_array(gdata, RENDER_LCD_1)
        height, width, channel = Z.shape
        bytesPerLine = channel * width

        have_outline = (not (0 in list(Z.shape)))

        if not dark_theme:
            Z = (255-Z)

        # Get starting position and metrics. For zero-width marks, we expand the width,
        # but only if spacing_mark=True.
        starting_ypos = (y - gdata["bitmap_top"]) - y_offset
        is_mark = spacing_mark and (gdata["advance"] == 0)
        if is_mark:
            starting_xpos = xpos = x
            xpos += 2
            gdata["advance"] = self.advance = round(gdata["width"] / 3) + 4
        else:
            starting_xpos = xpos = (x + gdata["bitmap_left"]) + x_offset

        # Get QImage from Z; set composition mode; draw the glyph.
        if have_outline:
            img = QImage(Z.data, width, height, bytesPerLine, QImage.Format.Format_RGB888)
            if dark_theme:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
            else:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            # painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, on=False)
            painter.drawImage(starting_xpos, starting_ypos, img)

        # Draw a red line under target glyph (the one in the current resolution).
        ending_xpos = starting_xpos + round(gdata["advance"])
        ending_ypos = starting_ypos + gdata["rows"]
        if is_target:
            ul_y = ending_ypos + 4
            qc = QPen(QColor("red"))
            qc.setWidth(2)
            painter.setPen(qc)
            painter.drawLine(QLine(starting_xpos, ul_y, ending_xpos, ul_y))
        if abs(ending_ypos - starting_ypos) <= 5:
            starting_ypos -= 3
            ending_ypos += 3

        # Get a QRect for this glyph (will be a target for clicks).
        self.rect_list.append(
            ygLetterBox(
                starting_xpos,
                starting_ypos,
                ending_xpos,
                ending_ypos,
                glyph_index=self.glyph_index,
                size=self.size,
                gname=self.index_to_name(self.glyph_index),
            )
        )
        return gdata["advance"]


    def _draw_char_grayscale(
            self,
            painter,
            x,
            y,
            spacing_mark=False,
            dark_theme = False,
            is_target = False,
            x_offset = 0,
            y_offset = 0,
        ):
        """Draws a bitmap with grayscale rendering

        Params:

        painter (QPainter): a Qt tool to draw with

        x (int): The left origin of the glyph

        y (int): The baseline

        """
        gdata = self._get_bitmap_metrics()
        Z = self.mk_array(gdata, RENDER_GRAYSCALE)
        ypos = (y - gdata["bitmap_top"]) - y_offset
        starting_ypos = ypos
        is_mark = spacing_mark and (gdata["advance"] == 0)
        if is_mark:
            starting_xpos = xpos = x
            xpos += 2
            gdata["advance"] = self.advance = gdata["width"] + 4
        else:
            starting_xpos = xpos = (x + gdata["bitmap_left"]) + x_offset
        qp = QPen(QColor("black"))
        qp.setWidth(1)
        for row in Z:
            xpos = starting_xpos
            for col in row:
                if dark_theme:
                    qp.setColor(self.bw_colors_dark[col])
                else:
                    qp.setColor(self.bw_colors[col])
                painter.setPen(qp)
                painter.drawPoint(xpos, ypos)
                xpos += 1
            ypos += 1
        ending_xpos = starting_xpos + round(gdata["advance"])
        ending_ypos = starting_ypos + gdata["rows"]
        if is_target:
            ul_y = ending_ypos + 4
            qc = QPen(QColor("red"))
            qc.setWidth(2)
            painter.setPen(qc)
            painter.drawLine(QLine(starting_xpos, ul_y, ending_xpos, ul_y))
        if abs(ending_ypos - starting_ypos) <= 5:
            starting_ypos -= 3
            ending_ypos += 3
        self.rect_list.append(
            ygLetterBox(
                starting_xpos,
                starting_ypos,
                ending_xpos,
                ending_ypos,
                glyph_index=self.glyph_index,
                size=self.size,
                gname=self.index_to_name(self.glyph_index),
            )
        )
        return gdata["advance"]

    def name_to_index(self, gname):
        if type(gname) is str:
            gname = gname.encode()
        try:
            r = self.face.get_name_index(gname)
            return r
        except Exception as e:
            return None
        
    def names_to_indices(self, l):
        result = []
        for n in l:
            result.append(self.name_to_index(n))
        return result

    def index_to_name(self, index):
        try:
            return self.face.get_glyph_name(index)
        except Exception as e:
            print("Error in index_to_name:")
            print(e)
            return ".notdef"
        
    def indices_to_names(self, index_list):
        result = []
        for i in index_list:
            result.append(self.index_to_name(i))
        return result


    def char_to_index(self, char):
        try:
            return self.face.get_char_index(char)
        except Exception:
            return None

    def string_to_indices(self, s):
        indices = []
        for ss in s:
            try:
                i = self.char_to_index(ss)
                if i != None:
                    indices.append(i)
            except Exception:
                pass
        return indices

    def draw_string(self,
                    painter,
                    s: str | list,
                    x,
                    y,
                    background_image: QImage,
                    positions: list = [],
                    x_limit = 200,
                    y_increment = 67,
                    dark_theme = False,
        ):

        self.last_glyph_index = None
        self.reset_rect_list()

        if type(s) is str:
            indices = self.string_to_indices(s)
        else:
            indices = self.names_to_indices(s)

        xpos = x
        ypos = y
        for count, i in enumerate(indices):
            self.set_char(i)
            x_offset = 0
            y_offset = 0
            x_advance = -1
            # If possible, use positions from Harfbuzz. This will include kerning
            # and correct positioning of diacritics.
            if len(positions):
                x_offset = self.font_to_pixels(positions[count].x_offset)
                y_offset = self.font_to_pixels(positions[count].y_offset)
                x_advance = self.font_to_pixels(positions[count].x_advance)

            #if self.last_glyph_index != None:
            #    k = self.face.get_kerning(
            #        self.last_glyph_index, i, ft.FT_KERNING_DEFAULT
            #    )
            #    xpos += k.x
            adv = self.draw_char(painter, xpos, ypos, dark_theme = dark_theme, x_offset = x_offset, y_offset = y_offset)
            if x_advance >= 0:
                adv = x_advance
            xpos += adv
            if xpos >= x_limit:
                xpos = x
                ypos += y_increment
                self.last_glyph_index = None
            if ypos > y + y_increment:
                break
            self.last_glyph_index = i
        return self.rect_list
