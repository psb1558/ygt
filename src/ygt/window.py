# import inspect
from typing import Any, TypeVar, Union, Optional
import sys
import os
import copy
import yaml
from .ygModel import ygFont, ygGlyph, unicode_cat_names
from .fontViewDialog import fontViewWindow
from .ygPreview import ygPreview, ygStringPreview, ygPreviewContainer
from .ygYAMLEditor import ygYAMLEditor, editorDialog
from .ygHintEditor import ygGlyphScene, ygGlyphView
from .ygPreferences import ygPreferences, open_config
from .ygSchema import (
    is_cvt_valid,
    is_prep_valid,
    are_macros_valid,
    are_functions_valid,
    are_defaults_valid,
    are_names_valid,
    are_properties_valid,
)
from .ygError import ygErrorMessages
from .makeCVDialog import fontInfoWindow
from xgridfit import compile_list # type: ignore
from xgridfit import run as xgf_run # type: ignore
from fontTools import ufoLib # type: ignore
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSlot, pyqtSignal, QObject, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QMainWindow,
    QSplitter,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QFileDialog,
    QScrollArea,
    QSizePolicy,
    QGraphicsView,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QMenu,
)
from PyQt6.QtGui import (
    QKeySequence,
    QIcon,
    QPixmap,
    QActionGroup,
    QUndoStack,
    QUndoGroup,
    QCloseEvent,
    QAction,
    QFontDatabase,
    QPainter,
)
from fontTools import ttLib, ufoLib # type: ignore
from .harfbuzzFont import harfbuzzFont

# FileNameVar = TypeVar("FileNameVar", str, tuple[str, Any])
FileNameVar = Union[str, tuple[str, Any]]
# FileNameVar = Any
ygt_version = "0.2.3"


class ygPreviewFontMaker(QThread):
    """To be run from a QThread. This is because it can take the better
    part of a second to generate a preview, even on a pretty fast
    machine, and we want to be able to run this on a signal without
    making the GUI balky.

    Parameters:

    font: a fontTools representation of the font

    source: the source for this font's hints

    glyph_list: the names of the glyphs for which we want to make the preview.
    """

    sig_preview_ready = pyqtSignal(object)
    sig_preview_error = pyqtSignal()

    def __init__(self, font: ttLib.TTFont, source: dict, glyph_list: list) -> None:
        super().__init__()
        self.ft_font = font
        self.source = source
        self.glyph_list = []
        for g in glyph_list:
            try:
                self.glyph_list.append(g.decode(encoding="utf-8"))
            except Exception:
                self.glyph_list.append(g)
        # self.glyph_list = glyph_list
        self.error = False

    def run(self) -> None:
        try:
            font = copy.deepcopy(self.ft_font)
            tmp_font, glyph_index, failed_glyph_list = compile_list(
                font, self.source, self.glyph_list
            )
            self.sig_preview_ready.emit(
                {"font": tmp_font, "gindex": glyph_index, "failed": failed_glyph_list}
            )
        except Exception as e:
            self.sig_preview_error.emit()


class ygFontGenerator(QThread):
    """For generating whole fonts."""

    sig_font_gen_done = pyqtSignal(object)
    sig_font_gen_error = pyqtSignal()

    def __init__(
            self,
            font: ttLib.TTFont,
            source: dict,
            output_font: str,
            mergemode: bool = False,
            replaceprep: bool = False,
            functionbase: int = 0,
            initgraphics: bool = False,
            assume_y: bool = False,
            cleartype: bool = True, # Not yet hooked up
            use_truetype_defaults: bool = False, # Not yet hooked up
        ) -> None:
        super().__init__()
        self.ft_font = font
        self.source = source
        self.output_font = output_font
        self.error = False
        self.mergemode = mergemode
        self.replaceprep = replaceprep
        self.functionbase = functionbase
        self.initgraphics = initgraphics
        self.assume_y = "no"
        if assume_y:
            self.assume_y = "yes"
        self.cleartype = "no"
        if cleartype:
            self.cleartype = "yes"
        self.use_truetype_defaults = use_truetype_defaults

    def run(self) -> None:
        try:
            font = copy.deepcopy(self.ft_font)
            err, failed_glyph_list = xgf_run(
                font = font,
                yaml = self.source,
                outputfont = self.output_font,
                quiet = 3,
                mergemode = self.mergemode,
                replaceprep = self.replaceprep,
                functionbase = self.functionbase,
                initgraphics = self.initgraphics,
                assume_y = self.assume_y,
            )
            self.sig_font_gen_done.emit(failed_glyph_list)
        except KeyError as e:
            self.sig_font_gen_error.emit()


class MainWindow(QMainWindow):
    def __init__(
            self,
            app: QApplication,
            win_list: Optional[list] = None,
            prefs: Optional[ygPreferences] = None,
            parent = None
        ):
        super(MainWindow, self).__init__(parent=parent)
        # undo_group will hold undo stacks for each edited glyph and
        # font-level data.
        self.undo_group = QUndoGroup()
        self.undo_group.cleanChanged.connect(self.clean_changed)
        self.error_manager = ygErrorMessages(self)
        if not win_list:
            self.win_list = [self]
        else:
            self.win_list = win_list
        self.filename = ""
        self.font_info_editor: Optional[fontInfoWindow] = None
        self.cvt_editor: Optional[editorDialog] = None
        self.prep_editor: Optional[editorDialog] = None
        self.function_editor: Optional[editorDialog] = None
        self.macro_editor: Optional[editorDialog] = None
        self.default_editor: Optional[editorDialog] = None
        self.font_viewer: Optional[fontViewWindow] = None
        self.statusbar = self.statusBar()
        self.statusbar_label = QLabel()
        self.statusbar_label.setStyleSheet(
            "QLabel {font-family: Source Code Pro, monospace; margin-left: 10px; }"
        )
        self.statusbar.addWidget(self.statusbar_label)

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.icon_path = os.path.split(sys._MEIPASS)[0]
            self.icon_path = os.path.join(sys._MEIPASS, "icons")
        else:
            self.icon_path = os.path.split(__file__)[0]
            self.icon_path = os.path.join(self.icon_path, "icons/")

        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setWindowTitle("YGT")
        self.toolbar = self.addToolBar("Tools")
        self.toolbar.setIconSize(QSize(32, 32))
        self.progress_bar: Optional[QProgressBar] = None
        self.progress_bar_action: Optional[QAction] = None
        self.spacer = QWidget()
        self.spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.spacer_action = self.toolbar.addWidget(self.spacer)
        self.preview_container = QVBoxLayout()
        self.qs = QSplitter(self)
        self.glyph_pane: Optional[ygGlyphView] = None
        self.preview_glyph_name: Optional[str] = None
        self.preview_glyph_name_list: list = []
        self.yg_font: Optional[ygFont] = None
        self.source_editor: Optional[ygYAMLEditor] = None
        self.preview_scroller: Optional[QScrollArea] = None
        self.yg_preview = None # type: Optional[ygPreview]
        self.yg_string_preview: Optional[ygStringPreview] = None
        self.app = app

        # Stuff that's stored in the preference file
        self.preferences: Optional[ygPreferences] = None
        self.points_as_coords = False
        self.zoom_factor: Optional[float] = None
        self.show_off_curve_points: Optional[bool] = None
        self.show_point_numbers: Optional[bool] = None
        self.current_axis = "y"
        if prefs == None:
            self.get_preferences(ygPreferences())
        else:
            self.get_preferences(prefs)

        self.recents_display: list = []
        self.recents_actions: list = []
        self.instance_actions: list = []
        self.script_actions: list = []
        self.script_menu = None
        self.language_actions: list = []
        self.language_menu = None
        self.feature_actions: list = []
        self.feature_menu = None
        self.feature_reset_action = None
        self.window_list: list = []
        self.preview_maker: Optional[ygPreviewFontMaker] = None
        self.font_generator: Optional[ygFontGenerator] = None
        self.auto_preview_update = True

        #
        # Build menus and toolbar
        #

        self.menu = self.menuBar()

        #
        # File menu
        #

        self.file_menu = self.menu.addMenu("&File")

        self.open_action = self.file_menu.addAction("Open")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)

        self.close_action = self.file_menu.addAction("Close")
        self.close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.close_action.setEnabled(False)

        self.save_action = self.file_menu.addAction("Save")
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setEnabled(False)

        self.save_as_action = self.file_menu.addAction("Save As...")
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.setEnabled(False)

        self.recent_menu = self.file_menu.addMenu("Recent Files...")

        self.save_font_action = self.file_menu.addAction("Export Font...")
        self.save_font_action.setShortcut(QKeySequence("Ctrl+e"))
        self.save_font_action.setEnabled(False)

        self.quit_action = self.file_menu.addAction("Quit")
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)

        self.file_menu.addSeparator()

        self.font_info_action = self.file_menu.addAction("Font Info")
        self.font_info_action.setShortcut(QKeySequence("Ctrl+i"))
        self.font_info_action.setEnabled(False)

        self.file_menu.addSeparator()

        self.about_action = self.file_menu.addAction("About YGT")
        self.about_action.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)

        self.file_menu.aboutToShow.connect(self.file_menu_about_to_show)

        #
        # Edit Menu
        #

        self.edit_menu = self.menu.addMenu("&Edit")

        self.undo_action = self.edit_menu.addAction("Undo")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setEnabled(False)

        self.redo_action = self.edit_menu.addAction("Redo")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setEnabled(False)

        self.cut_action = self.edit_menu.addAction("Cut")
        self.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        self.cut_action.setEnabled(False)

        self.copy_action = self.edit_menu.addAction("Copy")
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setEnabled(False)

        self.paste_action = self.edit_menu.addAction("Paste")
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.setEnabled(False)

        self.goto_action = self.edit_menu.addAction("Go to...")
        self.goto_action.setShortcut(QKeySequence("Ctrl+G"))
        self.goto_action.setEnabled(False)

        self.edit_menu.aboutToShow.connect(self.edit_menu_about_to_show)

        #
        # Preview Menu
        #

        self.preview_menu = self.menu.addMenu("&Preview")

        self.pv_show_hints_action = self.preview_menu.addAction("Hint preview")
        self.pv_show_hints_action.setShortcut(QKeySequence("Ctrl+p"))
        self.pv_show_hints_action.setCheckable(True)
        self.pv_show_hints_action.setChecked(True)
        self.pv_show_hints_action.setEnabled(False)

        self.save_current_glyph_action = self.preview_menu.addAction("Update Preview")
        self.save_current_glyph_action.setShortcut(QKeySequence("Ctrl+u"))
        self.save_current_glyph_action.setEnabled(False)

        self.toggle_auto_preview_action = self.preview_menu.addAction("Auto update")
        self.toggle_auto_preview_action.setCheckable(True)
        self.toggle_auto_preview_action.setChecked(True)
        self.toggle_auto_preview_action.setEnabled(False)

        self.preview_menu.addSeparator()

        self.pv_bigger_one_action = self.preview_menu.addAction("Grow by One")
        self.pv_bigger_one_action.setShortcut(
            QKeySequence.StandardKey.MoveToPreviousLine
        )
        self.pv_bigger_one_action.setEnabled(False)

        self.pv_bigger_ten_action = self.preview_menu.addAction("Grow by Ten")
        self.pv_bigger_ten_action.setShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Up) # type: ignore
        )
        self.pv_bigger_ten_action.setEnabled(False)

        self.pv_smaller_one_action = self.preview_menu.addAction("Shrink by One")
        self.pv_smaller_one_action.setShortcut(QKeySequence.StandardKey.MoveToNextLine)
        self.pv_smaller_one_action.setEnabled(False)

        self.pv_smaller_ten_action = self.preview_menu.addAction("Shrink by Ten")
        self.pv_smaller_ten_action.setShortcut(
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Down) # type: ignore
        )
        self.pv_smaller_ten_action.setEnabled(False)

        self.pv_set_size_action = self.preview_menu.addAction("Set size...")
        self.pv_set_size_action.setShortcut(QKeySequence("Ctrl+l"))
        self.pv_set_size_action.setEnabled(False)

        self.preview_menu.addSeparator()

        self.pv_show_grid_action = self.preview_menu.addAction("Show grid")
        self.pv_show_grid_action.setCheckable(True)
        self.pv_show_grid_action.setChecked(True)
        self.pv_show_grid_action.setEnabled(False)

        self.instance_menu: Optional[QMenu] = None

        self.pv_theme_menu = self.preview_menu.addMenu("Theme")
        self.pv_theme_auto_action = self.pv_theme_menu.addAction("Auto")
        self.pv_theme_light_action = self.pv_theme_menu.addAction("Black on white")
        self.pv_theme_dark_action = self.pv_theme_menu.addAction("White on black")
        self.theme_action_group = QActionGroup(self.pv_theme_menu)
        self.theme_action_group.addAction(self.pv_theme_auto_action)
        self.theme_action_group.addAction(self.pv_theme_light_action)
        self.theme_action_group.addAction(self.pv_theme_dark_action)
        self.pv_theme_auto_action.setCheckable(True)
        self.pv_theme_light_action.setCheckable(True)
        self.pv_theme_dark_action.setCheckable(True)
        self.pv_theme_auto_action.setChecked(True)
        self.pv_theme_menu.setEnabled(False)

        self.pv_render_mode_menu = self.preview_menu.addMenu("Render mode")
        self.pv_mode_1_action = self.pv_render_mode_menu.addAction("Grayscale")
        self.pv_mode_2_action = self.pv_render_mode_menu.addAction("Subpixel (1)")
        self.pv_mode_3_action = self.pv_render_mode_menu.addAction("Subpixel (2)")
        self.render_action_group = QActionGroup(self.pv_render_mode_menu)
        self.render_action_group.addAction(self.pv_mode_1_action)
        self.render_action_group.addAction(self.pv_mode_2_action)
        self.render_action_group.addAction(self.pv_mode_3_action)
        self.pv_mode_1_action.setCheckable(True)
        self.pv_mode_2_action.setCheckable(True)
        self.pv_mode_2_action.setChecked(True)
        self.pv_mode_3_action.setCheckable(True)
        self.pv_render_mode_menu.setEnabled(False)

        self.preview_menu.addSeparator()

        self.script_menu = self.preview_menu.addMenu("Script")
        self.script_menu.setEnabled(False)
        self.language_menu = self.preview_menu.addMenu("Language")
        self.language_menu.setEnabled(False)
        self.feature_menu = self.preview_menu.addMenu("Features")
        self.feature_menu.setEnabled(False)
        self.feature_reset_action = self.preview_menu.addAction("Reset features")
        self.feature_reset_action.setEnabled(False)

        self.preview_menu.aboutToShow.connect(self.preview_menu_about_to_show)

        #
        # View Menu
        #

        self.view_menu = self.menu.addMenu("&View")

        self.zoom_in_action = self.view_menu.addAction("Zoom In")
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)

        self.zoom_out_action = self.view_menu.addAction("Zoom Out")
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)

        self.original_size_action = self.view_menu.addAction("Original Size")
        self.original_size_action.setShortcut(QKeySequence("Ctrl+0"))

        self.view_menu.addSeparator()

        self.index_label_action = self.view_menu.addAction("Point indices")
        self.coord_label_action = self.view_menu.addAction("Point coordinates")

        self.view_menu.addSeparator()

        self.next_glyph_action = self.view_menu.addAction("Next Glyph")
        self.next_glyph_action.setShortcut(QKeySequence.StandardKey.MoveToNextChar)

        self.previous_glyph_action = self.view_menu.addAction("Previous Glyph")
        self.previous_glyph_action.setShortcut(
            QKeySequence.StandardKey.MoveToPreviousChar
        )

        self.view_menu.addSeparator()

        self.font_view_action = self.view_menu.addAction("Show Font Viewer")

        self.view_menu.aboutToShow.connect(self.view_menu_about_to_show)

        self.view_menu.setEnabled(False)

        #
        # Code Menu
        #

        self.code_menu = self.menu.addMenu("&Code")

        self.compile_action = self.code_menu.addAction("Compile")
        self.compile_action.setShortcut(QKeySequence("Ctrl+r"))

        self.cleanup_action = self.code_menu.addAction("Clean up")

        self.to_coords_action = self.code_menu.addAction("Indices to Coords")

        self.to_indices_action = self.code_menu.addAction("Coords to Indices")

        self.code_menu.addSeparator()

        self.edit_names_action = self.code_menu.addAction("Edit point names...")

        self.edit_properties_action = self.code_menu.addAction(
            "Edit glyph properties..."
        )

        self.code_menu.addSeparator()

        self.edit_cvt_action = self.code_menu.addAction("Edit cvt...")

        self.edit_prep_action = self.code_menu.addAction("Edit prep...")

        # self.edit_cvar_action = self.code_menu.addAction("Edit cvar...")

        self.edit_functions_action = self.code_menu.addAction("Edit Functions...")

        self.edit_macros_action = self.code_menu.addAction("Edit Macros...")

        self.edit_defaults_action = self.code_menu.addAction("Edit Defaults...")

        self.code_menu.setEnabled(False)

        #
        # Toolbar
        #

        axis_action_group = QActionGroup(self.toolbar)
        axis_action_group.setExclusive(True)

        self.vertical_action = self.toolbar.addAction("Vertical hinting")
        vertical_icon = QIcon()
        vertical_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "vertical-on.png")), state=QIcon.State.On
        )
        vertical_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "vertical-off.png")), state=QIcon.State.Off
        )
        self.vertical_action.setIcon(vertical_icon)
        self.vertical_action.setCheckable(True)

        self.horizontal_action = self.toolbar.addAction("Horizontal hinting")
        horizontal_icon = QIcon()
        horizontal_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "horizontal-on.png")), state=QIcon.State.On
        )
        horizontal_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "horizontal-off.png")), state=QIcon.State.Off
        )
        self.horizontal_action.setIcon(horizontal_icon)
        self.horizontal_action.setCheckable(True)

        axis_action_group.addAction(self.vertical_action)
        axis_action_group.addAction(self.horizontal_action)
        self.vertical_action.setChecked(True)
        self.vertical_action.setEnabled(False)
        self.horizontal_action.setEnabled(False)

        cursor_action_group = QActionGroup(self.toolbar)
        cursor_action_group.setExclusive(True)

        self.cursor_action = self.toolbar.addAction("Editing cursor")
        cursor_icon = QIcon()
        cursor_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "cursor-icon-on.png")), state=QIcon.State.On
        )
        cursor_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "cursor-icon-off.png")), state=QIcon.State.Off
        )
        self.cursor_action.setIcon(cursor_icon)
        self.cursor_action.setCheckable(True)

        self.toolbar.insertSeparator(self.cursor_action)

        self.hand_action = self.toolbar.addAction("Panning Cursor (spacebar)")
        hand_icon = QIcon()
        hand_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "hand-icon-on.png")), state=QIcon.State.On
        )
        hand_icon.addPixmap(
            QPixmap(os.path.join(self.icon_path, "hand-icon-off.png")), state=QIcon.State.Off
        )
        self.hand_action.setIcon(hand_icon)
        self.hand_action.setCheckable(True)

        cursor_action_group.addAction(self.cursor_action)
        cursor_action_group.addAction(self.hand_action)
        self.cursor_action.setChecked(True)
        self.cursor_action.setEnabled(False)
        self.hand_action.setEnabled(False)

        self.stem_action = self.toolbar.addAction("Stem (T)")
        self.stem_action.setIcon(QIcon(QPixmap(os.path.join(self.icon_path, "stem_distance.png"))))
        self.stem_action.setShortcuts(
            [
                QKeySequence(Qt.Key.Key_T),
                QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_T), # type: ignore
                QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_T), # type: ignore
                QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_T), # type: ignore
            ]
        )
        self.stem_action.setEnabled(False)

        self.toolbar.insertSeparator(self.stem_action)

        self.shift_action = self.toolbar.addAction("Shift (H)")
        self.shift_action.setIcon(QIcon(QPixmap(os.path.join(self.icon_path, "shift.png"))))
        self.shift_action.setShortcuts(
            [QKeySequence(Qt.Key.Key_H), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_H)] # type: ignore
        )
        self.shift_action.setEnabled(False)

        self.align_action = self.toolbar.addAction("Align (L)")
        self.align_action.setIcon(QIcon(QPixmap(os.path.join(self.icon_path, "align.png"))))
        self.align_action.setShortcuts(
            [QKeySequence(Qt.Key.Key_L), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_L)] # type: ignore
        )
        self.align_action.setEnabled(False)

        self.interpolate_action = self.toolbar.addAction("Interpolate (I)")
        self.interpolate_action.setIcon(
            QIcon(QPixmap(os.path.join(self.icon_path, "interpolate.png")))
        )
        self.interpolate_action.setShortcuts(
            [QKeySequence(Qt.Key.Key_I), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_I)] # type: ignore
        )
        self.interpolate_action.setEnabled(False)

        self.anchor_action = self.toolbar.addAction("Anchor (A)")
        self.anchor_action.setIcon(QIcon(QPixmap(os.path.join(self.icon_path, "anchor.png"))))
        self.anchor_action.setShortcuts(
            [
                QKeySequence(Qt.Key.Key_A),
                QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_A), # type: ignore
                QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_A), # type: ignore
                QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_A), # type: ignore
            ]
        )
        self.anchor_action.setEnabled(False)

        self.make_cv_guess_action = self.toolbar.addAction("Guess Control Value (?)")
        self.make_cv_guess_action.setIcon(
            QIcon(QPixmap(os.path.join(self.icon_path, "cv_guess.png")))
        )
        self.make_cv_guess_action.setShortcut(QKeySequence(Qt.Key.Key_Question))
        self.make_cv_guess_action.setEnabled(False)

        self.make_cv_action = self.toolbar.addAction("Make Control Value (C)")
        self.make_cv_action.setIcon(QIcon(QPixmap(os.path.join(self.icon_path, "cv.png"))))
        self.make_cv_action.setShortcut(QKeySequence(Qt.Key.Key_C))
        self.make_cv_action.setEnabled(False)

        self.central_widget = self.qs
        self.setCentralWidget(self.central_widget)

        self.setup_file_connections()

        self.setup_edit_connections()

        self.setup_undo_connections()

        self.mwe = mainWinEventFilter(self)
        self.installEventFilter(self.mwe)

    #
    # Panning and Editing buttons
    #

    @pyqtSlot(bool)
    def set_mouse_panning(self, panning_on: bool) -> None:
        if self.glyph_pane:
            if panning_on:
                self.glyph_pane.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    @pyqtSlot(bool)
    def set_mouse_editing(self, editing_on: bool) -> None:
        if self.glyph_pane:
            if editing_on:
                self.glyph_pane.setDragMode(QGraphicsView.DragMode.NoDrag)

    @pyqtSlot(object)
    def set_panning_editing(self, mode) -> None:
        if mode == QGraphicsView.DragMode.ScrollHandDrag:
            self.hand_action.setChecked(True)
        else:
            self.cursor_action.setChecked(True)

    #
    # Preview panes
    #

    @pyqtSlot()
    def preview_error(self) -> None:
        emsg = "Error compiling YAML or Xgridfit code. "
        emsg += "Check the correctness of your code (including any "
        emsg += "functions or macros and the prep program) and try again."
        self.error_manager.new_message({"msg": emsg, "mode": "console"})

    def check_axis_button(self) -> None:
        if self.current_axis == "y":
            self.vertical_action.setChecked(True)
        else:
            self.horizontal_action.setChecked(True)

    @pyqtSlot(object)
    def preview_ready(self, args: dict) -> None:
        try:
            glyph_index = args["gindex"][self.preview_glyph_name]
            self.yg_preview.fetch_glyph(args["font"], glyph_index)
            self.yg_preview.make_pixmap()
            self.yg_preview.update()
        except Exception:
            pass

    @pyqtSlot()
    def toggle_auto_preview(self) -> None:
        self.auto_preview_update = not self.auto_preview_update
        try:
            self.glyph_pane.yg_glyph_scene.yg_glyph.set_auto_preview_connection()
        except Exception as e:
            # print(e)
            pass

    @pyqtSlot()
    def preview_current_glyph(self) -> None:
        self._preview_current_glyph()

    def _preview_current_glyph(self) -> None:
        try:
            if self.preview_maker != None and self.preview_maker.isRunning():
                return
        except RuntimeError as e:
            # We get this RuntimeError when self.thread has been garbage collected.
            # It means that it's safe to run the rest of this function.
            pass
        source = self.yg_font.source
        font = self.yg_font.preview_font
        self.preview_glyph_name = self.glyph_pane.yg_glyph_scene.yg_glyph.gname
        preview_text = self.yg_string_preview.panel._text
        self.preview_glyph_name_list = []
        if preview_text != None and len(preview_text) > 0:
            l_full, p_full = self.yg_font.harfbuzz_font.get_shaped_names(preview_text)
            l_full_fixed = [c.decode() for c in l_full]
            # l is the list with redundancies removed (for making a subsetted font)
            l = list(set(l_full_fixed))
            self.preview_glyph_name_list.extend(l)
            # Store the full list for later use.
            self.yg_string_preview.full_glyph_list = l_full_fixed
            self.yg_string_preview.full_pos_list = p_full
        if not self.preview_glyph_name in self.preview_glyph_name_list:
            self.preview_glyph_name_list.append(self.preview_glyph_name)
            self.preview_glyph_name_list.extend(
                list(set(self.yg_font.additional_component_names([self.preview_glyph_name])))
            )

        # What function does this line serve?
        self.yg_string_preview.set_face(self.yg_preview.face)

        self.preview_maker = ygPreviewFontMaker(
            font, source, self.preview_glyph_name_list
        )
        self.preview_maker.finished.connect(self.preview_maker.deleteLater)
        self.preview_maker.sig_preview_ready.connect(self.preview_ready)
        self.preview_maker.sig_preview_error.connect(self.preview_error)
        self.preview_maker.start()

        self.pv_bigger_one_action.setEnabled(True)
        self.pv_bigger_ten_action.setEnabled(True)
        self.pv_smaller_one_action.setEnabled(True)
        self.pv_smaller_ten_action.setEnabled(True)
        self.pv_set_size_action.setEnabled(True)
        self.pv_show_hints_action.setEnabled(True)
        self.pv_show_grid_action.setEnabled(True)
        self.toggle_auto_preview_action.setEnabled(True)
        if self.instance_menu != None:
            self.prev_instance_action.setEnabled(True)
            self.next_instance_action.setEnabled(True)
            self.instance_menu.setEnabled(True)

    @pyqtSlot(object)
    def update_string_preview(self, s) -> None:
        preview_text = self.yg_string_preview.panel._text
        if preview_text != None and len(preview_text) > 0:
            self.yg_string_preview.set_string_preview()
        else:
            self.yg_string_preview.set_size_array()
        self.yg_string_preview.set_face(self.yg_preview.face)
        self.yg_string_preview.panel.make_pixmap()
        self.yg_string_preview.update()

    #
    # Font view window
    #

    @pyqtSlot()
    def show_font_view(self) -> None:
        """Display the modeless dialog in fontViewWindow.py."""
        if not self.font_viewer:
            font_name = self.yg_font.font_files.in_font
            glyph_list = self.yg_font.glyph_list
            self.font_viewer = fontViewWindow(font_name, self.yg_font, glyph_list, self)
        if self.font_viewer.valid:
            self.font_viewer.show()
            self.font_viewer.raise_()
            self.font_viewer.activateWindow()
        else:
            self.error_manager.new_message(
                {"msg": "Can't create the font view dialog.", "mode": "console"}
            )

    #
    # Indices vs. coordinates outline display
    #

    @pyqtSlot()
    def index_labels(self) -> None:
        self.points_as_coords = False
        self.glyph_pane.yg_glyph_scene.set_point_display("index")

    @pyqtSlot()
    def coord_labels(self) -> None:
        self.points_as_coords = True
        self.glyph_pane.yg_glyph_scene.set_point_display("coord")

    #
    # Prep for menu display
    #

    def setup_script_menu(self):
        if not self.yg_font:
            return
        self.script_menu.clear()
        self.script_actions.clear()
        scripts = self.yg_font.harfbuzz_font.sub_scripts
        for s in scripts:
            sa = self.script_menu.addAction(s)
            sa.setCheckable(True)
            sa.setChecked(s == self.yg_font.harfbuzz_font.current_script_tag)
            sa.triggered.connect(self.set_script)
            self.script_actions.append(sa)
        self.script_menu.setEnabled(len(scripts) > 0)

    def setup_language_menu(self):
        if not self.yg_font:
            return
        self.language_menu.clear()
        self.language_actions.clear()
        languages = self.yg_font.harfbuzz_font.sub_languages
        for l in languages:
            la = self.language_menu.addAction(l)
            la.setCheckable(True)
            la.setChecked(l == self.yg_font.harfbuzz_font.current_language_tag)
            la.triggered.connect(self.set_language)
            self.language_actions.append(la)
        self.language_menu.setEnabled(len(languages) > 0)

    def setup_feature_menu(self):
        if not self.yg_font:
            return
        self.feature_menu.clear()
        self.feature_actions.clear()
        features = self.yg_font.harfbuzz_font.sub_features
        for f in features:
            fa = self.feature_menu.addAction(harfbuzzFont.expanded_feature_name(f))
            fa.setCheckable(True)
            fa.setChecked(f in self.yg_font.harfbuzz_font._active_features)
            fa.triggered.connect(self.toggle_feature)
            self.feature_actions.append(fa)
        self.feature_menu.setEnabled(len(features) > 0)
        self.feature_reset_action.setEnabled(len(features) > 0)
            

    @pyqtSlot()
    def view_menu_about_to_show(self) -> None:
        if self.points_as_coords:
            self.index_label_action.setEnabled(True)
            self.coord_label_action.setEnabled(False)
        else:
            self.index_label_action.setEnabled(False)
            self.coord_label_action.setEnabled(True)

    @pyqtSlot()
    def file_menu_about_to_show(self) -> None:
        self.recents_display = []
        self.disconnect_recents_connections()
        self.recent_menu.clear()
        self.recents_actions.clear()
        self.recents_display.clear()
        if len(self.preferences["recents"]) > 0:
            self.recent_menu.setEnabled(True)
            dups = []
            for f in self.preferences["recents"]:
                shorter_fn = os.path.split(f)[1]
                if shorter_fn in self.recents_display:
                    dups.append(shorter_fn)
                else:
                    self.recents_display.append(shorter_fn)
            if len(dups) > 0:
                self.recents_display.clear()
                for f in self.preferences["recents"]:
                    shorter_fn = os.path.split(f)[1]
                    if shorter_fn in dups:
                        self.recents_display.append(f)
                    else:
                        self.recents_display.append(shorter_fn)
            for f in self.recents_display:
                self.recents_actions.append(self.recent_menu.addAction(f))
            self.setup_recents_connections()
        else:
            self.recent_menu.setEnabled(False)

    @pyqtSlot()
    def preview_menu_about_to_show(self) -> None:
        if self.yg_preview != None:
            if self.yg_preview.face != None:
                self.pv_render_mode_menu.setEnabled(True)
            self.pv_theme_menu.setEnabled(True)
            self.pv_show_hints_action.setChecked(self.yg_preview.hinting_on)
            self.pv_show_grid_action.setChecked(self.yg_preview.show_grid)
        self.toggle_auto_preview_action.setChecked(self.auto_preview_update)
        self.setup_script_menu()
        self.setup_language_menu()
        self.setup_feature_menu()


    @pyqtSlot()
    def edit_menu_about_to_show(self) -> None:
        if self.undo_group.canUndo():
            self.undo_action.setEnabled(True)
            self.undo_action.setText("Undo " + self.undo_group.undoText())
        else:
            self.undo_action.setText("Undo")
            self.undo_action.setEnabled(False)
        if self.undo_group.canRedo():
            self.redo_action.setEnabled(True)
            self.redo_action.setText("Redo " + self.undo_group.redoText())
        else:
            self.redo_action.setText("Redo")
            self.redo_action.setEnabled(False)

    #
    # Connection setup
    #

    # In the hierarchy of major objects, MainWindow and ygGlyphView are always present, while
    # ygGlyph and ygGlyphScene are destroyed whenever we move from one glyph to another.
    # To avoid complications, avoid connecting signals to ygGlyph and ygGlyphScene; otherwise,
    # we've got to kill one connection and create another whenever we switch from one glyph
    # to another.
    #
    # These connect menus and toolbar buttons; ygGlyph and ygGlyphScene have their own
    # signals.

    def setup_editor_connections(self) -> None:
        self.compile_action.triggered.connect(self.source_editor.yaml_source)

    def setup_file_connections(self):
        self.save_action.triggered.connect(self.save_yaml_file)
        self.save_as_action.triggered.connect(self.save_as)
        self.quit_action.triggered.connect(
            self.quit, type=Qt.ConnectionType.QueuedConnection
        )
        self.open_action.triggered.connect(self.open_file)
        self.save_font_action.triggered.connect(self.export_font)
        self.font_info_action.triggered.connect(self.edit_font_info)
        self.about_action.triggered.connect(self.show_about_dialog)

    def setup_recents_connections(self) -> None:
        for a in self.recents_actions:
            a.triggered.connect(self.open_recent)

    def disconnect_recents_connections(self) -> None:
        for a in self.recents_actions:
            a.triggered.disconnect(self.open_recent)

    def setup_hint_connections(self) -> None:
        self.stem_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.anchor_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.interpolate_action.triggered.connect(
            self.glyph_pane.make_hint_from_selection
        )
        self.shift_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.align_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.make_cv_action.triggered.connect(self.glyph_pane.make_control_value)
        self.make_cv_guess_action.triggered.connect(self.glyph_pane.guess_cv)
        self.vertical_action.toggled.connect(self.glyph_pane.switch_to_y)
        self.horizontal_action.toggled.connect(self.glyph_pane.switch_to_x)

    def setup_edit_connections(self) -> None:
        self.edit_cvt_action.triggered.connect(self.edit_cvt)
        self.edit_prep_action.triggered.connect(self.edit_prep)
        self.edit_functions_action.triggered.connect(self.edit_functions)
        self.edit_macros_action.triggered.connect(self.edit_macros)
        self.edit_defaults_action.triggered.connect(self.edit_defaults)
        self.edit_names_action.triggered.connect(self.edit_names)
        self.edit_properties_action.triggered.connect(self.edit_properties)
        self.to_coords_action.triggered.connect(self.indices_to_coords)
        self.to_indices_action.triggered.connect(self.coords_to_indices)

    def setup_preview_connections(self) -> None:
        self.save_current_glyph_action.triggered.connect(self.preview_current_glyph)
        self.toggle_auto_preview_action.triggered.connect(self.toggle_auto_preview)
        self.pv_bigger_one_action.triggered.connect(self.yg_preview.bigger_one)
        self.pv_bigger_ten_action.triggered.connect(self.yg_preview.bigger_ten)
        self.pv_smaller_one_action.triggered.connect(self.yg_preview.smaller_one)
        self.pv_smaller_ten_action.triggered.connect(self.yg_preview.smaller_ten)
        self.pv_set_size_action.triggered.connect(self.show_ppem_dialog)
        self.pv_mode_1_action.triggered.connect(self.yg_preview.render1)
        self.pv_mode_2_action.triggered.connect(self.yg_preview.render2)
        self.pv_mode_3_action.triggered.connect(self.yg_preview.render3)
        self.pv_theme_auto_action.triggered.connect(self.yg_preview.set_theme_auto)
        self.pv_theme_light_action.triggered.connect(self.yg_preview.set_theme_light)
        self.pv_theme_dark_action.triggered.connect(self.yg_preview.set_theme_dark)
        self.pv_show_hints_action.triggered.connect(self.yg_preview.toggle_show_hints)
        self.pv_show_grid_action.triggered.connect(self.yg_preview.toggle_grid)
        self.feature_reset_action.triggered.connect(self.yg_font.harfbuzz_font.reset_features)

    def setup_preview_instance_connections(self) -> None:
        if self.yg_font.is_variable_font and self.instance_actions != None:
            self.prev_instance_action.triggered.connect(self.yg_preview.next_instance)
            self.next_instance_action.triggered.connect(self.yg_preview.prev_instance)
            for i in self.instance_actions:
                i.triggered.connect(self.yg_preview.set_instance)

    def setup_zoom_connections(self) -> None:
        self.zoom_in_action.triggered.connect(self.glyph_pane.zoom)
        self.zoom_out_action.triggered.connect(self.glyph_pane.zoom)
        self.original_size_action.triggered.connect(self.glyph_pane.zoom)

    def setup_point_label_connections(self) -> None:
        self.index_label_action.triggered.connect(self.index_labels)
        self.coord_label_action.triggered.connect(self.coord_labels)

    def setup_nav_connections(self) -> None:
        self.next_glyph_action.triggered.connect(self.glyph_pane.next_glyph)
        self.previous_glyph_action.triggered.connect(self.glyph_pane.previous_glyph)
        self.goto_action.triggered.connect(self.show_goto_dialog)
        self.glyph_pane.setup_goto_signal(self.show_goto_dialog)
        self.glyph_pane.setup_toggle_drag_mode_signal(self.set_panning_editing)
        self.font_view_action.triggered.connect(self.show_font_view)

    def setup_undo_connections(self) -> None:
        self.undo_action.triggered.connect(self.undo_group.undo)
        self.redo_action.triggered.connect(self.undo_group.redo)

    def setup_cursor_connections(self) -> None:
        self.hand_action.toggled.connect(self.set_mouse_panning)
        self.cursor_action.toggled.connect(self.set_mouse_editing)

    def setup_glyph_pane_connections(self) -> None:
        self.setup_nav_connections()
        self.setup_zoom_connections()
        self.source_editor.setup_editor_signals(
            self.glyph_pane.yg_glyph_scene.yg_glyph.save_editor_source
        )
        self.source_editor.setup_status_indicator(self.set_status_validity_msg)
        self.setup_cursor_connections()

    def connect_editor_signals(self) -> None:
        self.source_editor.setup_editor_signals(
            self.glyph_pane.yg_glyph_scene.yg_glyph.save_editor_source
        )

    def disconnect_editor_signals(self) -> None:
        self.source_editor.disconnect_editor_signals(
            self.glyph_pane.yg_glyph_scene.yg_glyph.save_editor_source
        )

    #
    # GUI setup
    #

    def set_up_instance_list(self) -> None:
        if self.yg_font.is_variable_font and hasattr(self.yg_font, "instances"):
            self.preview_menu.addSeparator()
            self.prev_instance_action = self.preview_menu.addAction("Previous instance")
            self.prev_instance_action.setShortcut(QKeySequence(Qt.Key.Key_Less))
            self.next_instance_action = self.preview_menu.addAction("Next instance")
            self.next_instance_action.setShortcut(QKeySequence(Qt.Key.Key_Greater))
            self.instance_menu = self.preview_menu.addMenu("&Instances")
            self.instance_actions = []
            instance_names = []
            for k in self.yg_font.instances.keys():
                self.instance_actions.append(self.instance_menu.addAction(k))
                instance_names.append(k)
            self.yg_preview.add_instances(self.yg_font.instances)
            self.yg_preview.instance = self.yg_font.default_instance
            self.prev_instance_action.setEnabled(False)
            self.next_instance_action.setEnabled(False)
            self.instance_menu.setEnabled(False)

    def set_up_feature_list(self) -> None:
        pass

    def set_size_and_position(self):
        """Set size and position of the main window."""
        if self.preferences.geometry_valid():
            self.setGeometry(
                self.preferences["top_window_pos_x"],
                self.preferences["top_window_pos_y"],
                self.preferences["top_window_width"],
                self.preferences["top_window_height"],
            )
        else:
            qg = self.screen().availableGeometry()
            x = qg.x() + 20
            y = qg.y() + 20
            width = qg.width() * 0.66
            height = qg.height() * 0.75
            self.setGeometry(int(x), int(y), int(width), int(height))

    def add_preview(self) -> None:
        self.yg_preview = ygPreview(self)
        self.yg_string_preview = ygStringPreview(self.yg_preview, self)
        self.yg_string_preview.set_go_to_signal(self.go_to_glyph)
        ygpc = ygPreviewContainer(self.yg_preview, self.yg_string_preview)
        self.qs.addWidget(ygpc)
        self.setup_preview_connections()

    def add_editor(self, editor: ygYAMLEditor):
        self.source_editor = editor
        self.source_editor.setup_error_signal(self.error_manager.new_message)
        self.qs.addWidget(self.source_editor)

    def add_glyph_pane(self, g: ygGlyphView) -> None:
        # Must be a ygGlyphView(QGraphicsView) object.
        self.glyph_pane = g
        self.qs.addWidget(self.glyph_pane)
        self.setup_glyph_pane_connections()
        self.setup_hint_connections()
        self.cleanup_action.triggered.connect(self.glyph_pane.cleanup_yaml_code)

    def set_axis_buttons(self) -> None:
        """To be run right after preferences are loaded and before a file is
        loaded.

        """
        if self.current_axis == "y":
            self.vertical_action.setChecked(True)
        else:
            self.horizontal_action.setChecked(True)
        self.vertical_action.setEnabled(False)
        self.horizontal_action.setEnabled(False)

    def add_undo_stack(self, s: QUndoStack) -> None:
        self.undo_group.addStack(s)

    def set_all_clean(self):
        s = self.undo_group.stacks()
        for ss in s:
            ss.setClean()

    # Could be a property
    def is_file_clean(self):
        s = self.undo_group.stacks()
        for ss in s:
            if not ss.isClean():
                return False
        return True

    #
    # File operations
    #

    @pyqtSlot()
    def save_yaml_file(self) -> None:
        self._save_yaml_file()

    def _save_yaml_file(self) -> None:
        if self.yg_font and (not self.is_file_clean()):
            glyph = self.glyph_pane.yg_glyph_scene.yg_glyph
            glyph_backup = copy.deepcopy(glyph.gsource)
            glyph.cleanup_glyph()
            self.yg_font.cleanup_font(glyph.gname)
            self.yg_font.source_file.save_source()
            glyph.gsource.clear()
            for k in glyph_backup.keys():
                glyph.gsource[k] = glyph_backup[k]
            self.set_all_clean()
            self.set_window_title()

    def save_as(self) -> None:
        self.yg_font.source_file.filename = QFileDialog(parent=self).getSaveFileName()[
            0
        ]
        if not self.yg_font.source_file.filename:
            return
        self.preferences.add_recent(self.yg_font.source_file.filename)
        glyph = self.glyph_pane.yg_glyph_scene.yg_glyph
        glyph_backup = copy.deepcopy(glyph.gsource)
        glyph.cleanup_glyph()
        self.yg_font.source_file.save_source(top_window=self)
        glyph.gsource.clear()
        for k in glyph_backup.keys():
            glyph.gsource[k] = glyph_backup[k]
        self.set_all_clean()

    @pyqtSlot()
    def export_font(self) -> None:
        try:
            if self.font_generator != None and self.font_generator.isRunning():
                return
        except RuntimeError as e:
            # We get this RuntimeError when self.thread has been garbage collected.
            # It means that it's safe to run the rest of this function.
            pass
        source = self.yg_font.source
        new_file_name = self.yg_font.font_files.out_font
        in_file_name = self.yg_font.font_files.in_font
        if new_file_name == None or in_file_name == None:
            return
        source = self.yg_font.source
        font = self.yg_font.preview_font
        msg_box = QMessageBox(self)
        msg_box.setText("Ready to export " + new_file_name + "?")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save
        )
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msg_box.exec()
        if ret == QMessageBox.StandardButton.Cancel:
            return
        mergemode = bool(self.yg_font.defaults.get_default("merge-mode"))
        replaceprep = bool(self.yg_font.defaults.get_default("replace-prep"))
        initgraphics = bool(self.yg_font.defaults.get_default("init-graphics"))
        assume_y = bool(self.yg_font.defaults.get_default("assume-always-y"))
        try:
            functionbase = int(self.yg_font.defaults.get_default("function-base"))
        except TypeError:
            functionbase = 0
        self.font_generator = ygFontGenerator(
            font,
            source,
            new_file_name,
            mergemode = mergemode,
            replaceprep = replaceprep,
            functionbase = functionbase,
            initgraphics = initgraphics,
            assume_y = assume_y
        )
        self.font_generator.finished.connect(self.font_generator.deleteLater)
        self.font_generator.sig_font_gen_done.connect(self.font_gen_finished)
        self.font_generator.sig_font_gen_error.connect(self.font_gen_error)
        self.font_generator.start()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar_action = self.toolbar.insertWidget(
            self.spacer_action, self.progress_bar
        )

    @pyqtSlot(object)
    def font_gen_finished(self, failed_list: list) -> None:
        self.toolbar.removeAction(self.progress_bar_action)
        self.progress_bar = None
        self.progress_bar_action = None
        if len(failed_list) > 0:
            emsg = "Failed to compile one or more glyphs: "
            for f in failed_list:
                emsg += f + " "
            self.error_manager.new_message({"msg": emsg, "mode": "console"})

    @pyqtSlot()
    def font_gen_error(self) -> None:
        self.toolbar.removeAction(self.progress_bar_action)
        self.progress_bar = None
        self.progress_bar_action = None
        emsg = "Failed to generate the font. This most likely due to an error "
        emsg += "in function, macro, or prep code or in your cvt or cvar "
        emsg += "entries."
        self.error_manager.new_message({"msg": emsg, "mode": "console"})

    @pyqtSlot()
    def open_recent(self) -> None:
        f = self.sender().text() # type: ignore
        ff = None
        try:
            i = self.recents_display.index(f)
            ff = self.preferences["recents"][i]
        except Exception as e:
            print("Failure while trying to open recent file:")
            print(e)
        if ff:
            result = self._open(ff)
            if result == 1:
                self.set_preferences()
                w = MainWindow(self.app, win_list=self.win_list, prefs=self.preferences)
                result = w._open(ff)
                if result == 0:
                    w.show()
                    self.win_list.append(w)

    @pyqtSlot()
    def open_file(self) -> None:
        f: FileNameVar = QFileDialog.getOpenFileName(
            self, "Open TrueType font or YAML file", "", "Files (*.ttf *.ufo *.yaml)"
        )
        result = 1
        try:
            os.chdir(os.path.split(f[0])[0])
            result = self._open(f)
        except FileNotFoundError:
            emsg = "Can't find file '" + str(f) + "'."
            if type(f) is tuple:
                emsg += f[0]
            elif type(f) is str:
                emsg += f
            else:
                emsg += str(f)
            self.error_manager.new_message({"msg": emsg, "mode": "console"})
        if result == 1:
            self.set_preferences()
            w = MainWindow(self.app, win_list=self.win_list, prefs=self.preferences)
            result = w._open(f)
            if result == 0:
                w.show()
                self.win_list.append(w)

    def _initialize_source(
        self, filename: FileNameVar, fn_base: str, extension: str
    ) -> dict:
        prep_code = """<code xmlns=\"http://xgridfit.sourceforge.net/Xgridfit2\">
            <!-- Turn off hinting above 300 ppem -->
            <if test="pixels-per-em &gt; 300">
                <disable-instructions/>
            </if>
            <!-- Dropout control -->
            <push>4 511</push>
            <command name="SCANCTRL"/>
            <command name="SCANTYPE"/>
            </code>"""
        function_code = """<code xmlns="http://xgridfit.sourceforge.net/Xgridfit2">
        <command name="SDB"/>
        <command name="DUP"/>
        <push>0</push>
        <command name="NEQ"/>
        <command name="IF"/>
        <command name="DUP"/>
        <push>0</push>
        <command name="LT"/>
        <command name="IF"/>
        <push>8</push>
        <command name="ADD"/>
        <command name="ELSE"/>
        <push>7</push>
        <command name="ADD"/>
        <command name="EIF"/>
        <command name="SWAP"/>
        <push>1</push>
        <command name="DELTAP1"/>
        <command name="ELSE"/>
        <command name="POP"/>
        <command name="POP"/>
        <command name="EIF"/>
        <push>8</push>
        <command name="SDB"/>
        </code>"""
        yaml_source: dict = {}
        yaml_source["font"] = {}
        yaml_source["font"]["in"] = copy.copy(filename)
        if extension == ".ufo":
            yaml_source["font"]["out"] = filename
        else:
            yaml_source["font"]["out"] = fn_base + "-hinted" + extension
        yaml_source["defaults"] = {}
        yaml_source["cvt"] = {}
        yaml_source["prep"] = {}
        yaml_source["prep"] = {"code": prep_code}
        # Supply a pre-built delta function.
        yaml_source["functions"] = {
            "delta": {
                "primitive": True,
                "stack-safe": True,
                "size": {"type": "int", "val": 25},
                "distance": {"type": "int", "val": 0},
                "pt": {"type": "point", "subtype": "target"},
                "code": function_code,
            }
        }
        yaml_source["macros"] = {}
        yaml_source["glyphs"] = {}
        return yaml_source

    def _open(self, f: FileNameVar) -> int:
        """Returns 0 if file opened in this window
        Returns 1 if this window already has a file open
        Returns 2 if the file is already open (the window is activated and brought to top)

        f param can be:
        - the name of a .yaml file
        - the name of a .ttf font
        - the name of a .ufo font (treated differently if it contains ygt source)
        """
        # If this window already has content, return 1 as a signal that a new window
        # has to be created.
        if self.glyph_pane:
            return 1
        # A string with the filename if this was one of the recents. A tuple with the
        # filename at index [0] if from a dialog.
        if type(f) is str:
            filename = f
        else:
            filename = f[0]
        # If the file is already open, raise its window.
        for w in self.win_list:
            if filename == w.filename:
                w.activateWindow()
                w.raise_()
                return 2
        # If still here, we've got the name of a .ttf, .ufo, or .yaml.
        self.filename = filename

        # Set up menus and toolbar.
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)
        self.save_font_action.setEnabled(True)
        self.font_info_action.setEnabled(True)
        self.goto_action.setEnabled(True)
        self.vertical_action.setEnabled(True)
        self.horizontal_action.setEnabled(True)
        self.cursor_action.setEnabled(True)
        self.hand_action.setEnabled(True)
        self.save_current_glyph_action.setEnabled(True)
        self.code_menu.setEnabled(True)
        self.view_menu.setEnabled(True)

        if filename:
            self.preferences.add_recent(filename)
            split_fn = os.path.splitext(filename)
            fn_base = split_fn[0]
            extension = split_fn[1]
            yaml_source = {}
            # If file is .ttf, create a skeleton yaml_source and a ygt_filename.
            # If file is .ufo, read yaml source if possible, or if not create skeleton.
            if extension == ".ttf":
                ygt_filename = fn_base + ".yaml"
                self.preferences.add_recent(ygt_filename)
                yaml_source = self._initialize_source(filename, fn_base, extension)
            if extension == ".ufo":
                self.preferences.add_recent(filename)
                ygt_filename = filename
                try:
                    u = ufoLib.UFOReader(filename)
                    y = u.readData("org.ygthinter/source.yaml")
                    u.close()
                    yaml_source = yaml.safe_load(y.decode("utf-8"))
                except Exception:
                    yaml_source = self._initialize_source(filename, fn_base, extension)

            self.preferences["current_font"] = filename

            # If opening ttf, we have both yaml_source and ygt_filename
            # If opening ufo, ygt_filename is the same as the font name
            # If opening yaml, we just pass the filename (since font is identified in the file)
            if len(yaml_source) > 0:
                self.yg_font = ygFont(self, yaml_source, ygt_filename=ygt_filename)
            else:
                self.yg_font = ygFont(self, filename)
            self.yg_font.setup_error_signal(self.error_manager.new_message)

            self.setup_script_menu()
            self.setup_language_menu()
            self.setup_feature_menu()

            self.add_preview()
            self.yg_preview.set_up_signal(self.update_string_preview)

            self.source_editor = ygYAMLEditor(self.preferences)
            self.add_editor(self.source_editor)

            if (
                "current_glyph" in self.preferences
                and self.yg_font.full_name in self.preferences["current_glyph"]
            ):
                initGlyph = self.preferences["current_glyph"][self.yg_font.full_name]
            else:
                initGlyph = "A"
            modelGlyph = ygGlyph(self.preferences, self.yg_font, initGlyph)
            modelGlyph.set_yaml_editor(self.source_editor)
            yg_glyph_scene = ygGlyphScene(self.preferences, modelGlyph)
            view = ygGlyphView(self.preferences, yg_glyph_scene, self.yg_font)
            yg_glyph_scene.owner = view
            self.add_glyph_pane(view)
            w = self.width()
            self.qs.setSizes([int(w * 0.2961), int(w * 0.1497), int(w * 0.5542)])
            view.centerOn(view.yg_glyph_scene.center_x, view.sceneRect().center().y())
            self.set_window_title()
            self.set_up_instance_list()
            self.set_up_feature_list()
            self.setup_editor_connections()
            self.setup_preview_instance_connections()
            self.setup_point_label_connections()
            # Should we send a signal for preview update from here?
            self._preview_current_glyph()
        return 0

    #
    # GUI management
    #

    def setup_stem_buttons(self, axis):
        pass

    @pyqtSlot(object)
    def selection_changed(self, selection_profile: list):
        total_selected = selection_profile[0] + selection_profile[1]
        # fix up make cv button
        if total_selected >= 1 and total_selected <= 2:
            self.make_cv_action.setEnabled(True)
        else:
            self.make_cv_action.setEnabled(False)
        if 0 in selection_profile[3] or 3 in selection_profile[3]:
            self.make_cv_guess_action.setEnabled(True)
        else:
            self.make_cv_guess_action.setEnabled(False)
        if selection_profile[0] == 0 and selection_profile[1] == 1:
            # enable anchor button
            self.anchor_action.setEnabled(True)
            self.stem_action.setEnabled(False)
            self.shift_action.setEnabled(False)
            self.align_action.setEnabled(False)
            self.interpolate_action.setEnabled(False)
        elif selection_profile[0] == 1 and selection_profile[1] >= 1:
            if selection_profile[1] == 1:
                self.stem_action.setEnabled(True)
            else:
                self.stem_action.setEnabled(False)
            # shift_action and align_action if 1 pt touched and 1 or more untouched.
            if selection_profile[1] >= 1:
                self.shift_action.setEnabled(True)
                self.align_action.setEnabled(True)
            else:
                self.shift_action.setEnabled(False)
                self.align_action.setEnabled(False)
            self.interpolate_action.setEnabled(False)
            self.anchor_action.setEnabled(False)
        elif selection_profile[0] == 2 and selection_profile[1] >= 1:
            # Enable interpolation button
            self.interpolate_action.setEnabled(True)
            self.stem_action.setEnabled(False)
            self.shift_action.setEnabled(False)
            self.align_action.setEnabled(False)
            self.anchor_action.setEnabled(False)
            #self.make_set_action.setEnabled(False)
        else:
            # "Disable all hint editing buttons
            self.stem_action.setEnabled(False)
            self.shift_action.setEnabled(False)
            self.align_action.setEnabled(False)
            self.interpolate_action.setEnabled(False)
            self.anchor_action.setEnabled(False)

    @pyqtSlot()
    def clean_changed(self):
        self.set_window_title()

    def set_window_title(self) -> None:
        """And also the status bar"""
        base = "YGT"
        if self.yg_font:
            base += (
                " -- "
                + self.yg_font.full_name
            )
            if not self.is_file_clean():
                base += "*"
        self.setWindowTitle(base)
        if self.glyph_pane:
            self.set_statusbar_text(None)

    def set_statusbar_text(self, valid: Union[bool, None]) -> None:
        status_text = self.glyph_pane.yg_glyph_scene.yg_glyph.gname
        status_text += (
            " - " + unicode_cat_names[self.glyph_pane.yg_glyph_scene.yg_glyph.get_category()]
        )
        status_text += " (" + self.current_axis + ")"
        if valid != None:
            status_text += " ("
            if valid:
                status_text += "Valid)"
            else:
                status_text += "Invalid)"
        self.statusbar_label.setText(status_text)

    def set_status_validity_msg(self, t: str) -> None:
        self.set_statusbar_text(bool(t))

    @pyqtSlot()
    def show_about_dialog(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("About YGT")
        msg.setText("YGT " + ygt_version)
        detailed_text = "TrueType Hint Editor.\n"
        detailed_text += "Copyright © 2023 by Peter S. Baker.\n"
        detailed_text += "Apache License, version 2.0. \n\n"
        detailed_text += "For further information, visit https://github.com/psb1558/ygt."
        msg.setDetailedText(detailed_text)
        # Will need to mess with size hints and policies to do this.
        # msg.resize(round(msg.width() * 2), round(msg.height() * 2))
        msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
        msg.exec()

    def show_error_message(self, msg_list: list) -> None:
        msg = QMessageBox(self)
        if msg_list[0] == "Warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif msg_list[0] == "Error":
            msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(msg_list[1])
        msg.setText(msg_list[2])
        msg.exec()

    #
    # Editors in dialogs
    #

    @pyqtSlot()
    def indices_to_coords(self) -> None:
        try:
            self.glyph_pane.yg_glyph_scene.yg_glyph.indices_to_coords()
        except Exception as e:
            print(e)

    @pyqtSlot()
    def coords_to_indices(self) -> None:
        try:
            self.glyph_pane.yg_glyph_scene.yg_glyph.coords_to_indices()
        except Exception as e:
            print(e)

    @pyqtSlot()
    def edit_cvt(self) -> None:
        self.cvt_editor = editorDialog(
            self.preferences, self.yg_font.cvt, "cvt", is_cvt_valid
        )
        self.cvt_editor.show()
        self.cvt_editor.activateWindow()

    @pyqtSlot()
    def edit_font_info(self) -> None:
        if not self.font_info_editor:
            self.font_info_editor = fontInfoWindow(self.yg_font, self.preferences)
        self.yg_font.setup_signal(self.font_info_editor.refresh)
        self.font_info_editor.show()
        self.font_info_editor.raise_()
        self.font_info_editor.activateWindow()

    @pyqtSlot()
    def edit_prep(self) -> None:
        self.prep_editor = editorDialog(
            self.preferences, self.yg_font.prep, "prep", is_prep_valid
        )
        self.prep_editor.show()
        self.prep_editor.activateWindow()

    @pyqtSlot()
    def edit_functions(self) -> None:
        self.function_editor = editorDialog(
            self.preferences,
            self.yg_font.functions_func,
            "functions",
            are_functions_valid,
        )
        self.function_editor.show()
        self.function_editor.activateWindow()

    @pyqtSlot()
    def edit_macros(self) -> None:
        self.macro_editor = editorDialog(
            self.preferences, self.yg_font.macros_func, "macros", are_macros_valid
        )
        self.macro_editor.show()
        self.macro_editor.activateWindow()

    @pyqtSlot()
    def edit_defaults(self) -> None:
        self.default_editor = editorDialog(
            self.preferences, self.yg_font.defaults, "defaults", are_defaults_valid
        )
        self.default_editor.show()
        self.default_editor.activateWindow()

    @pyqtSlot()
    def edit_names(self) -> None:
        self.names_editor = editorDialog(
            self.preferences,
            self.glyph_pane.yg_glyph_scene.yg_glyph.names,
            "names",
            are_names_valid,
        )
        self.names_editor.show()
        self.names_editor.activateWindow()

    @pyqtSlot()
    def edit_properties(self) -> None:
        self.properties_editor = editorDialog(
            self.preferences,
            self.glyph_pane.yg_glyph_scene.yg_glyph.props,
            "properties",
            are_properties_valid,
        )
        self.properties_editor.show()
        self.properties_editor.activateWindow()

    #
    # Miscellaneous dialogs
    #

    @pyqtSlot()
    def show_goto_dialog(self) -> None:
        text, ok = QInputDialog().getText(
            self, "Go to glyph", "Glyph name:", QLineEdit.EchoMode.Normal
        )
        if ok and text:
            self.glyph_pane.go_to_glyph(text)

    @pyqtSlot(object)
    def go_to_glyph(self, g: str) -> None:
        self.glyph_pane.go_to_glyph(g)

    @pyqtSlot()
    def show_ppem_dialog(self):
        i, ok = QInputDialog().getInt(
            self,
            "Set Size",
            "Pixels per em:",
            value = 25,
            min = 10,
            max = 400,
        )
        if ok:
            self.yg_preview.set_size(i)
    
    @pyqtSlot()
    def toggle_feature(self):
        f = harfbuzzFont.tag_only(self.sender().text())
        if f in self.yg_font.harfbuzz_font.active_features:
            self.yg_font.harfbuzz_font.deactivate_feature(f)
        else:
            self.yg_font.harfbuzz_font.activate_feature(f)

    @pyqtSlot()
    def set_script(self):
        tag = self.sender().text()
        self.yg_font.harfbuzz_font.select_script(tag)
        for s in self.script_actions:
            s.setChecked(tag == s.text())

    @pyqtSlot()
    def set_language(self):
        tag = self.sender().text()
        self.yg_font.harfbuzz_font.select_language(tag)
        for l in self.language_actions:
            l.setChecked(tag == l.text())

    #
    # Program exit
    #

    def save_query(self) -> int:
        msg_box = QMessageBox()
        msg_box.setText("This font’s hints have been modified.")
        msg_box.setInformativeText("Do you want to save your work?")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
            | QMessageBox.StandardButton.Save
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msg_box.exec()
        if ret == QMessageBox.StandardButton.Cancel:
            return 1
        if ret == QMessageBox.StandardButton.Save:
            self._save_yaml_file()
            return 0
        return 2

    def del_from_win_list(self, w: Any) -> None:
        try:
            self.win_list.remove(w)
        except ValueError:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.yg_font == None:
            self.del_from_win_list(self)
            event.accept()
        elif self.is_file_clean():
            self.del_from_win_list(self)
            self.set_preferences()
            event.accept()
        else:
            result = self.save_query()
            if result == 1:
                event.ignore()
            else:
                self.del_from_win_list(self)
                event.accept()

    # Could be property
    def all_clean(self) -> bool:
        for w in self.win_list:
            if not w.is_file_clean():
                return False
        return True

    def quit(self) -> None:
        if self.yg_font == None:
            self.app.quit()
        elif self.all_clean():
            self.set_preferences()
            self.preferences.save_config()
            self.app.quit()
        else:
            exiting = True
            del_list = []
            for w in self.win_list:
                if not w.is_file_clean():
                    r = w.save_query()
                    if r in [0, 2]:
                        if r == 2:
                            w.set_all_clean()
                        del_list.append(w)
                    else:
                        exiting = False
                        break
            for d in del_list:
                try:
                    self.win_list.remove(d)
                except ValueError:
                    pass
            if exiting:
                self.preferences.save_config()
                self.app.quit()

    def resizeEvent(self, event):
        self.preferences.set_top_window_size(
            event.size().width(), event.size().height()
        )

    def moveEvent(self, event):
        if hasattr(self, "preferences"):
            self.preferences.set_top_window_pos(event.pos().x(), event.pos().y())

    def event(self, event) -> bool:
        if event.type() == event.Type.WindowActivate and self.glyph_pane:
                self.glyph_pane.yg_glyph_scene.yg_glyph.undo_stack.setActive(True)
        return super().event(event)

    def get_preferences(self, prefs: Optional[ygPreferences]) -> None:
        self.preferences = prefs
        self.points_as_coords = self.preferences.points_as_coords()
        self.zoom_factor = self.preferences.zoom_factor()
        self.show_off_curve_points = self.preferences.show_off_curve_points()
        self.show_point_numbers = self.preferences.show_point_numbers()

    def set_preferences(self) -> None:
        self.preferences.set_points_as_coords(self.points_as_coords)
        self.preferences.set_zoom_factor(self.zoom_factor)
        self.preferences.set_show_off_curve_points(self.show_off_curve_points)
        self.preferences.set_show_point_numbers(self.show_point_numbers)

    # Could be property
    def current_glyph(self):
        return self.glyph_pane.yg_glyph_scene.yg_glyph


class mainWinEventFilter(QObject):
    def __init__(self, top_win):
        super().__init__()
        self.top_window = top_win

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ActivationChange:
            if self.top_window.isActiveWindow():
                self.top_window.preferences["top_window"] = self.top_window
        return super().eventFilter(source, event)


def main():
    import uharfbuzz
    #from inspect import getfullargspec, signature
    print(dir(uharfbuzz._harfbuzz.GlyphPosition))
    # print(dir(QPainter))
    #print(dir(hb._harfbuzz.Font))
    #print(dir(hb._harfbuzz.Buffer))

    app = QApplication([])

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        font_path = os.path.join(
            sys._MEIPASS,
            "fonts",
            "SourceCodePro-Regular.ttf"
        )
    else:
        font_path = os.path.join(
            os.path.dirname(__file__),
            "fonts/SourceCodePro-Regular.ttf"
        )

    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        print("Can't find font Source Code Pro.")
    top_window = MainWindow(app)
    top_window.get_preferences(open_config(top_window))
    app.setWindowIcon(QIcon(top_window.icon_path + "program.png"))
    top_window.set_size_and_position()
    top_window.show()
    sys.exit(app.exec())
