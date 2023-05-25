import uharfbuzz as hb
from tempfile import SpooledTemporaryFile
from .freetypeFont import freetypeFont
# from PyQt6.QtCore import pyqtSlot


class harfbuzzFont:
    LANG_DEFAULT = 0xFFFF

    SCRIPT_DEFAULT = 0

    LAYOUT_TAGS = {
        "abvf": "Above-base Forms",
        "abvm": "Above-base Mark Positioning",
        "abvs": "Above-base Substitutions",
        "blwf": "Below-base Forms",
        "blwm": "Below-base Mark Positioning",
        "blws": "Below-base Substitutions",
        "pref": "Pre-base Forms",
        "pres": "Pre-base Substitutions",
        "psts": "Post-base Substitutions",
        "pstf": "Post-base Forms",
        "dist": "Distance",
        "akhn": "Akhand",
        "haln": "Halant Forms",
        "half": "Half Form",
        "nukt": "Nukta Forms",
        "rkrf": "Rakar Forms",
        "rphf": "Reph Form",
        "vatu": "Vattu Variants",
        "cjct": "Conjunct Forms",
        "cfar": "Conjunct Form After Ro",
        "smpl": "Simplified Forms",
        "trad": "Traditional Forms",
        "tnam": "Traditional Name Forms",
        "expt": "Expert Forms",
        "hojo": "Hojo Kanji Forms",
        "nlck": "NLC Kanji Forms",
        "jp78": "JIS 78 Forms",
        "jp83": "JIS 83 Forms",
        "jp90": "JIS 90 Forms",
        "jp04": "JIS 04 Forms",
        "hngl": "Hangul",
        "ljmo": "Leading Jamo Forms",
        "tjmo": "Trailing Jamo Forms",
        "vjmo": "Vowel Jamo Forms",
        "fwid": "Full Widths",
        "hwid": "Half Widths",
        "halt": "Alternate Half Widths",
        "twid": "Third Widths",
        "qwid": "Quarter Widths",
        "pwid": "Proportional Widths",
        "palt": "Proportional Alternates",
        "pkna": "Proportional Kana",
        "ruby": "Ruby Notation Forms",
        "hkna": "Horizontal Kana Alternates",
        "vkna": "Vertical Kana",
        "cpct": "Centered CJK Punctuation",
        "curs": "Cursive Positioning",
        "jalt": "Justification Alternates",
        "mset": "Mark Positioning via Substitution",
        "rclt": "Required Contextual Alternates",
        "rlig": "Required Ligatures",
        "isol": "Isolated Forms",
        "init": "Initial Forms",
        "medi": "Medial Forms",
        "med2": "Medial Form #2",
        "fina": "Terminal Forms",
        "fin2": "Terminal Form #2",
        "fin3": "Terminal Form #3",
        "falt": "Final Glyph on Line Alternates",
        "stch": "Stretching Glyph Decomposition",
        "smcp": "Small Caps",
        "c2sc": "Capitals to Small Caps",
        "pcap": "Petite Caps",
        "c2pc": "Capitals to Petite Caps",
        "unic": "Unicase",
        "cpsp": "Capital Spacing",
        "case": "Case Sensitive Forms",
        "ital": "Italics",
        "ordn": "Ordinals",
        "valt": "Alternative Vertical Metrics",
        "vhal": "Alternative Vertical Half Metrics",
        "vpal": "Proportional Alternate Vertical Metrics",
        "vert": "Vertical Alternates",
        "vrt2": "Vertical Alternates and Rotation",
        "vrtr": "Vertical Alternates for Rotation",
        "vkrn": "Vertical Kerning",
        "ltra": "Left-to-right glyph alternates",
        "ltrm": "Left-to-right mirrored forms",
        "rtla": "Right-to-left glyph alternates",
        "rtlm": "Right-to-left mirrored forms",
        "lnum": "Lining Figures",
        "onum": "Oldstyle Figures",
        "pnum": "Proportional Figures",
        "tnum": "Tabular Figures",
        "frac": "Fractions",
        "afrc": "Alternative Fractions",
        "dnom": "Denominator",
        "numr": "Numerator",
        "sinf": "Scientific Inferiors",
        "zero": "Slashed Zero",
        "mgrk": "Mathematical Greek",
        "flac": "Flattened accent forms",
        "dtls": "Dotless Forms",
        "ssty": "Math script style alternates",
        "aalt": "Access All Alternates",
        "swsh": "Swash",
        "cswh": "Contextual Swash",
        "calt": "Contextual Alternates",
        "hist": "Historical Forms",
        "locl": "Localized Forms",
        "rand": "Randomize",
        "nalt": "Alternate Annotation Forms",
        "salt": "Stylistic Alternates",
        "subs": "Subscript",
        "sups": "Superscript",
        "titl": "Titling Alternates",
        "rvrn": "Required Variation Alternates",
        "clig": "Contextual Ligatures",
        "dlig": "Discretionary Ligatures",
        "hlig": "Historical Ligatures",
        "liga": "Standard Ligatures",
        "ccmp": "Glyph Composition/Decomposition",
        "kern": "Kerning",
        "mark": "Mark Positioning",
        "mkmk": "Mark-to-mark Positioning",
        "opbd": "Optical Bounds",
        "lfbd": "Left Bounds",
        "rtbd": "Right Bounds",
        "ornm": "Ornaments",
    }

    def __init__(
        self,
        font: SpooledTemporaryFile | str,
        ft_font: freetypeFont,
        keep_open=False,
    ):
        self.ft_font = ft_font

        #
        # Read the font
        #
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

        #
        # Get tag lists: script, language, features
        #
        self._pos_features = hb._harfbuzz.ot_layout_language_get_feature_tags(
            self.hb_face, "GPOS"
        )
        self._sub_scripts = hb.ot_layout_table_get_script_tags(self.hb_face, "GSUB")
        self._sub_languages = ["dflt"]
        self._sub_features = []
        self._active_features = []
        self.current_script_tag = ""
        self.current_language_tag = ""
        if "DFLT" in self._sub_scripts:
            self.current_script_tag = "DFLT"
        else:
            if len(self._sub_scripts):
                self.current_script_tag = self._sub_scripts[0]
        if self.current_script_tag:
            self._sub_languages.extend(
                hb.ot_layout_script_get_language_tags(
                    self.hb_face, "GSUB", script_index=self.current_script_index
                )
            )
            self.current_language_tag = "dflt"
            self._sub_features = hb._harfbuzz.ot_layout_language_get_feature_tags(
                self.hb_face,
                "GSUB",
                script_index=self.current_script_index,
                language_index=self.current_language_index,
            )
            self._sub_features = sorted(self._sub_features)
            self.set_default_features()

    def set_default_features(self):
        self._active_features.clear()
        if "ccmp" in self._sub_features:
            self._active_features.append("ccmp")
        if "liga" in self._sub_features:
            self._active_features.append("liga")
        if "calt" in self._sub_features:
            self._active_features.append("calt")
        if "rlig" in self._sub_features:
            self._active_features.append("rlig")
        if "locl" in self._sub_features:
            self._active_features.append("locl")
        if "kern" in self._pos_features:
            self._active_features.append("kern")
        if "mark" in self._pos_features:
            self._active_features.append("mark")
        if "mkmk" in self._pos_features:
            self._active_features.append("mkmk")

    @property
    def current_script_index(self) -> int:
        try:
            return self._sub_scripts.index(self.current_script_tag)
        except ValueError:
            return harfbuzzFont.SCRIPT_DEFAULT

    @property
    def current_language_index(self) -> int:
        try:
            ind = self._sub_languages.index(self.current_language_tag)
            if ind == 0:
                ind = harfbuzzFont.LANG_DEFAULT
            else:
                ind -= 1
        except ValueError:
            ind = harfbuzzFont.LANG_DEFAULT
        return ind

    @property
    def sub_features(self) -> list:
        return self._sub_features

    @property
    def sub_scripts(self) -> list:
        return self._sub_scripts

    @property
    def sub_languages(self) -> list:
        return self._sub_languages

    @property
    def pos_features(self) -> list:
        return self._pos_features

    #@property
    #def all_features(self) -> list:
    #    result = []
    #    result.extend(self.sub_features)
    #    result.extend(self.pos_features)
    #    return result

    @property
    def active_features(self) -> list:
        return self._active_features

    @classmethod
    def expanded_feature_name(self, tag) -> str:
        assert len(tag) == 4, "Length of layout tag must be 4 (1)."
        ss = tag
        prefix = tag[0:2]
        try:
            if prefix == "cv":
                ss = tag + " - " + "Character Variant " + tag[2:4]
            elif prefix == "ss":
                ss = tag + " - " + "Stylistic Set " + tag[2:4]
            else:
                ss = tag + " - " + harfbuzzFont.LAYOUT_TAGS[tag]
        except Exception:
            pass
        return ss

    @classmethod
    def tag_only(self, s) -> str:
        tag = s.split(" ")[0]
        assert len(tag) == 4, "Length of layout tag must be 4 (2)."
        return tag

    def select_script(self, s: str) -> None:
        """If the currently selected language is not available for the newly
        selected script, change language to 'dflt'.
        """
        if s in self._sub_scripts:
            self.current_script_tag = s
        self.select_language(self.current_language_tag)

    def select_language(self, l: str) -> None:
        """New tag should have been selected from a list of available tags.
        And set up feature list for newly selected language.
        """
        self.current_language_tag = ""
        self._sub_languages.clear()
        self._sub_languages.append("dflt")
        self._sub_languages.extend(
            hb.ot_layout_script_get_language_tags(
                self.hb_face, "GSUB", script_index=self.current_script_index
            )
        )
        if l in self._sub_languages:
            self.current_language_tag = l
        else:
            self.current_language_tag = "dflt"
        self._sub_features.clear()
        self._sub_features.extend(hb._harfbuzz.ot_layout_language_get_feature_tags(
            self.hb_face,
            "GSUB",
            script_index=self.current_script_index,
            language_index=self.current_language_index,
        ))
        self._sub_features = sorted(self._sub_features)
        self.set_default_features()

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
        if self.current_script_tag:
            buf.script = self.current_script_tag
            if self.current_language_tag:
                buf.language = self.current_language_tag
        info, pos = self.shape(buf)
        indices = []
        for i in info:
            indices.append(i.codepoint)
        return self.ft_font.indices_to_names(indices), pos

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

    # @pyqtSlot()
    def reset_features(self):
        self.set_default_features()
