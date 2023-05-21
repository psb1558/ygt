import uharfbuzz as hb
from tempfile import SpooledTemporaryFile
from .freetypeFont import freetypeFont
from PyQt6.QtCore import pyqtSlot

class harfbuzzFont:
    def __init__(
            self,
            font: SpooledTemporaryFile | str,
            ft_font: freetypeFont,
            keep_open = False,
            top_window = None
    ):
        self.ft_font = ft_font
        if type(font) is SpooledTemporaryFile:
            font.seek(0)
            font_data = font.read()
            if not keep_open:
                font.close()
        else:
            font_file = open(font, "rb")
            font_data = font_file.read()
            if not keep_open:
                font_file.close()
        self.hb_face = hb.Face(font_data)
        self.hb_font = hb.Font(self.hb_face)

        self._sub_features = hb._harfbuzz.ot_layout_language_get_feature_tags(self.hb_face, "GSUB")
        self._sub_features = sorted(self._sub_features)
        self._pos_features = hb._harfbuzz.ot_layout_language_get_feature_tags(self.hb_face, "GPOS")
        self._active_features = []
        self.set_default_features()
        self.top_window = top_window

    def set_default_features(self):
        self._active_features.clear()
        if "ccmp" in self._sub_features:
            self._active_features.append("ccmp")
        if "liga" in self._sub_features:
            self._active_features.append("liga")
        if "calt" in self._sub_features:
            self._active_features.append("calt")
        if "kern" in self._pos_features:
            self._active_features.append("kern")
        if "mark" in self._pos_features:
            self._active_features.append("mark")
        if "mkmk" in self._pos_features:
            self._active_features.append("mkmk")

    @property
    def sub_features(self) -> list:
        return self._sub_features
    
    @property
    def pos_features(self) -> list:
        return self._pos_features
    
    @property
    def all_features(self) -> list:
        result = []
        result.extend(self.sub_features)
        result.extend(self.pos_features)
        return result
    
    @property
    def active_features(self) -> list:
        return self._active_features
    
    def activate_feature(self, f) -> None:
        add_feature = False
        if f in self._pos_features:
            add_feature = True
        if f in self._sub_features:
            add_feature = True
        if add_feature and not f in self._active_features:
            self._active_features.append(f)

    def deactivate_feature(self, f: str) -> None:
        try:
            self._active_features.remove(f)
        except ValueError:
            pass

    def get_shaped_names(self, s):
        buf = self.hb_buffer(s)
        info, pos = self.shape(buf)
        indices = []
        for i in info:
            indices.append(i.codepoint)
        return self.ft_font.indices_to_names(indices)

    def shape(self, buf):
        buf.guess_segment_properties()
        features = {f: True for f in self.active_features}
        hb.shape(self.hb_font, buf, features)
        char_info = buf.glyph_infos
        char_pos = buf.glyph_positions
        return buf.glyph_infos, buf.glyph_positions

    def hb_buffer(self, s: str) -> hb.Buffer:
        buf = hb.Buffer.create()
        buf.add_str(s)
        return buf
    
    def reset_features(self):
        self.set_default_features()
