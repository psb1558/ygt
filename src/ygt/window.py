import sys
import os
import copy
from .ygModel import ygFont, ygGlyph, unicode_cat_names
from .fontViewDialog import fontViewDialog
from .ygPreview import ygPreview, ygStringPreview, ygPreviewContainer
from .ygYAMLEditor import ygYAMLEditor, editorDialog
from .ygHintEditor import ygGlyphViewer, MyView
from .ygPreferences import ygPreferences, open_config
from .ygSchema import (
    is_cvt_valid,
    is_cvar_valid,
    is_prep_valid,
    are_macros_valid,
    are_functions_valid,
    are_defaults_valid,
    are_names_valid,
    are_properties_valid)
from xgridfit import compile_one, compile_all
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
    QVBoxLayout
)
from PyQt6.QtGui import (
    QKeySequence,
    QIcon,
    QPixmap,
    QActionGroup
)

class ygPreviewFontMaker(QThread):
    """ To be run from a QThread. This is because it can take the better
        part of a second to generate a preview, even on a pretty fast
        machine, and we want to be able to run this on a signal without
        making the GUI balky.

        Parameters:

        font: a fontTools representation of the font

        source: the source for this font's hints

        glyph_name: the name of the glyph for which we want to make the preview.
    """

    sig_preview_ready = pyqtSignal(object)
    sig_preview_error = pyqtSignal()

    def __init__(self, font, source, glyph_name):
        super().__init__()
        self.ft_font = font
        self.source = source
        self.glyph_name = glyph_name
        self.error = False

    def run(self):
        try:
            font = copy.deepcopy(self.ft_font)
            tmp_font, glyph_index, failed_glyph_list = compile_one(font, self.source, self.glyph_name)
            self.sig_preview_ready.emit({"font": tmp_font, "gindex": glyph_index, "failed": failed_glyph_list})
        except Exception as e:
            # print(e.args)
            self.sig_preview_error.emit()



class ygFontGenerator(QThread):

    sig_font_gen_done  = pyqtSignal(object)
    sig_font_gen_error = pyqtSignal()

    def __init__(self, font, source, output_font):
        super().__init__()
        self.ft_font = font
        self.source = source
        self.output_font = output_font
        self.error = False

    def run(self):
        try:
            font = copy.deepcopy(self.ft_font)
            failed_glyph_list = compile_all(font, self.source, self.output_font)
            self.sig_font_gen_done.emit(failed_glyph_list)
        except KeyError as e:
            print(e.args)
            self.sig_font_gen_error.emit()


class MainWindow(QMainWindow):
    def __init__(self, app, win_list=None, prefs=None, parent=None):
        super(MainWindow,self).__init__(parent=parent)

        if not win_list:
            self.win_list = [self]
        else:
            self.win_list = win_list
        self.filename = None
        self.cvt_editor = None
        self.cvar_editor = None
        self.function_editor = None
        self.macro_editor = None
        self.default_editor = None
        self.font_viewer = None
        self.statusbar = self.statusBar()
        self.statusbar_label = QLabel()
        self.statusbar_label.setStyleSheet("QLabel {font-family: Source Code Pro, monospace; margin-left: 10px; }")
        self.statusbar.addWidget(self.statusbar_label)

        self.prog_path = os.path.split(__file__)[0]
        self.icon_path = self.prog_path + "/icons/"
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setWindowTitle("YGT")
        self.toolbar = self.addToolBar("Tools")
        self.toolbar.setIconSize(QSize(32,32))
        self.progress_bar = None
        self.progress_bar_action = None
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.spacer_action = self.toolbar.addWidget(self.spacer)
        self.preview_container = QVBoxLayout()
        self.qs = QSplitter(self)
        self.glyph_pane = None
        self.yg_font = None
        self.source_editor = None
        self.preview_scroller = None
        self.yg_preview = None
        self.app = app

        # Stuff that's stored in the preference file
        self.preferences = None
        self.points_as_coords = None
        self.zoom_factor = None
        self.show_off_curve_points = None
        self.show_point_numbers = None
        self.current_axis = None
        if prefs == None:
            self.get_preferences(ygPreferences())
        else:
            self.get_preferences(prefs)

        self.recents_display = []
        self.recents_actions = []
        self.instance_actions = []
        self.window_list = []
        self.thread = None
        self.preview_maker = None
        self.font_generator = None
        self.auto_preview_update = True

        self.menu = self.menuBar()

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

        self.file_menu.aboutToShow.connect(self.file_menu_about_to_show)

        self.edit_menu = self.menu.addMenu("&Edit")

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

        self.preview_menu = self.menu.addMenu("&Preview")

        self.save_current_glyph_action = self.preview_menu.addAction("Update Preview")
        self.save_current_glyph_action.setShortcut(QKeySequence("Ctrl+u"))
        self.save_current_glyph_action.setEnabled(False)

        self.toggle_auto_preview_action = self.preview_menu.addAction("Auto update")
        self.toggle_auto_preview_action.setCheckable(True)
        self.toggle_auto_preview_action.setChecked(True)

        self.preview_menu.addSeparator()

        self.pv_bigger_one_action = self.preview_menu.addAction("Grow by One")
        self.pv_bigger_one_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousLine)
        self.pv_bigger_one_action.setEnabled(False)

        self.pv_bigger_ten_action = self.preview_menu.addAction("Grow by Ten")
        self.pv_bigger_ten_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Up))
        self.pv_bigger_ten_action.setEnabled(False)

        self.pv_smaller_one_action = self.preview_menu.addAction("Shrink by One")
        self.pv_smaller_one_action.setShortcut(QKeySequence.StandardKey.MoveToNextLine)
        self.pv_smaller_one_action.setEnabled(False)

        self.pv_smaller_ten_action = self.preview_menu.addAction("Shrink by Ten")
        self.pv_smaller_ten_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Down))
        self.pv_smaller_ten_action.setEnabled(False)

        self.pv_show_hints_action = self.preview_menu.addAction("Show hinting")
        self.pv_show_hints_action.setShortcut(QKeySequence("Ctrl+t"))
        self.pv_show_hints_action.setCheckable(True)
        self.pv_show_hints_action.setChecked(True)
        self.pv_show_hints_action.setEnabled(False)

        self.pv_show_grid_action = self.preview_menu.addAction("Show grid")
        self.pv_show_grid_action.setShortcut(QKeySequence("Ctrl+t"))
        self.pv_show_grid_action.setCheckable(True)
        self.pv_show_grid_action.setChecked(True)
        self.pv_show_grid_action.setEnabled(False)

        self.instance_menu = None

        self.preview_menu.addSeparator()

        self.pv_set_size_action = self.preview_menu.addAction("Pixels per Em...")
        self.pv_set_size_action.setShortcut(QKeySequence("Ctrl+p"))
        self.pv_set_size_action.setEnabled(False)

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

        self.preview_menu.aboutToShow.connect(self.preview_menu_about_to_show)

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
        self.previous_glyph_action.setShortcut(QKeySequence.StandardKey.MoveToPreviousChar)

        self.view_menu.addSeparator()

        self.font_view_action = self.view_menu.addAction("Show Font Viewer")

        self.view_menu.aboutToShow.connect(self.view_menu_about_to_show)

        axis_action_group = QActionGroup(self.toolbar)
        axis_action_group.setExclusive(True)

        self.view_menu.setEnabled(False)

        self.vertical_action = self.toolbar.addAction("Vertical hinting")
        self.vertical_action.setIcon(QIcon(QPixmap(self.icon_path + "vertical.png")))
        self.vertical_action.setCheckable(True)

        self.horizontal_action = self.toolbar.addAction("Horizontal hinting")
        self.horizontal_action.setIcon(QIcon(QPixmap(self.icon_path + "horizontal.png")))
        self.horizontal_action.setCheckable(True)

        axis_action_group.addAction(self.vertical_action)
        axis_action_group.addAction(self.horizontal_action)
        # self.vertical_action.setChecked(True)

        cursor_action_group = QActionGroup(self.toolbar)
        cursor_action_group.setExclusive(True)

        self.cursor_action = self.toolbar.addAction("Cursor (Edit hints)")
        cursor_icon = QIcon()
        cursor_icon.addPixmap(QPixmap(self.icon_path + "cursor-icon-on.png"), state=QIcon.State.On)
        cursor_icon.addPixmap(QPixmap(self.icon_path + "cursor-icon-off.png"), state=QIcon.State.Off)
        self.cursor_action.setIcon(cursor_icon)
        self.cursor_action.setCheckable(True)

        self.toolbar.insertSeparator(self.cursor_action)

        self.hand_action = self.toolbar.addAction("Hand (Pan the canvas)")
        hand_icon = QIcon()
        hand_icon.addPixmap(QPixmap(self.icon_path + "hand-icon-on.png"), state=QIcon.State.On)
        hand_icon.addPixmap(QPixmap(self.icon_path + "hand-icon-off.png"), state=QIcon.State.Off)
        self.hand_action.setIcon(hand_icon)
        self.hand_action.setCheckable(True)

        cursor_action_group.addAction(self.cursor_action)
        cursor_action_group.addAction(self.hand_action)
        self.cursor_action.setChecked(True)
        self.cursor_action.setEnabled(False)
        self.hand_action.setEnabled(False)

        self.black_action = self.toolbar.addAction("Black Distance (B)")
        self.black_action.setIcon(QIcon(QPixmap(self.icon_path + "black_distance.png")))
        self.black_action.setShortcuts([QKeySequence(Qt.Key.Key_B),
                                        QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_B),
                                        QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_B),
                                        QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_B)])
        self.black_action.setEnabled(False)

        self.toolbar.insertSeparator(self.black_action)

        self.white_action = self.toolbar.addAction("White Distance (W)")
        self.white_action.setIcon(QIcon(QPixmap(self.icon_path + "white_distance.png")))
        self.white_action.setShortcuts([QKeySequence(Qt.Key.Key_W),
                                        QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_W),
                                        QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_W),
                                        QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_W)])
        self.white_action.setEnabled(False)

        self.gray_action = self.toolbar.addAction("Gray Distance (G)")
        self.gray_action.setIcon(QIcon(QPixmap(self.icon_path + "gray_distance.png")))
        self.gray_action.setShortcuts([QKeySequence(Qt.Key.Key_G),
                                       QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_G),
                                       QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_G),
                                       QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_G)])
        self.gray_action.setEnabled(False)

        self.shift_action = self.toolbar.addAction("Shift (S)")
        self.shift_action.setIcon(QIcon(QPixmap(self.icon_path + "shift.png")))
        self.shift_action.setShortcuts([QKeySequence(Qt.Key.Key_S), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_S)])
        self.shift_action.setEnabled(False)

        self.align_action = self.toolbar.addAction("Align (L)")
        self.align_action.setIcon(QIcon(QPixmap(self.icon_path + "align.png")))
        self.align_action.setShortcuts([QKeySequence(Qt.Key.Key_L), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_L)])
        self.align_action.setEnabled(False)

        self.interpolate_action = self.toolbar.addAction("Interpolate (I)")
        self.interpolate_action.setIcon(QIcon(QPixmap(self.icon_path + "interpolate.png")))
        self.interpolate_action.setShortcuts([QKeySequence(Qt.Key.Key_I), QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_I)])
        self.interpolate_action.setEnabled(False)

        self.anchor_action = self.toolbar.addAction("Anchor (A)")
        self.anchor_action.setIcon(QIcon(QPixmap(self.icon_path + "anchor.png")))
        self.anchor_action.setShortcuts([QKeySequence(Qt.Key.Key_A),
                                         QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_A),
                                         QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_A),
                                         QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_A)])
        self.anchor_action.setEnabled(False)

        self.make_set_action = self.toolbar.addAction("Make Set (K)")
        self.make_set_action.setIcon(QIcon(QPixmap(self.icon_path + "make_set.png")))
        self.make_set_action.setShortcut(QKeySequence(Qt.Key.Key_K))
        self.make_set_action.setEnabled(False)

        self.make_cv_guess_action = self.toolbar.addAction("Guess Control Value (?)")
        self.make_cv_guess_action.setIcon(QIcon(QPixmap(self.icon_path + "cv_guess.png")))
        self.make_cv_guess_action.setShortcut(QKeySequence(Qt.Key.Key_Question))
        self.make_cv_guess_action.setEnabled(False)

        self.make_cv_action = self.toolbar.addAction("Make Control Value (C)")
        self.make_cv_action.setIcon(QIcon(QPixmap(self.icon_path + "cv.png")))
        self.make_cv_action.setShortcut(QKeySequence(Qt.Key.Key_C))
        self.make_cv_action.setEnabled(False)

        self.code_menu = self.menu.addMenu("&Code")

        self.compile_action = self.code_menu.addAction("Compile")
        self.compile_action.setShortcut(QKeySequence("Ctrl+r"))

        self.cleanup_action = self.code_menu.addAction("Clean up")

        self.to_coords_action = self.code_menu.addAction("Indices to Coords")

        self.to_indices_action = self.code_menu.addAction("Coords to Indices")

        self.code_menu.setEnabled(False)

        self.window_menu = self.menu.addMenu("&Window")

        self.edit_cvt_action = self.window_menu.addAction("Edit cvt...")

        self.edit_names_action = self.window_menu.addAction("Edit point names...")

        self.edit_properties_action = self.window_menu.addAction("Edit glyph properties...")

        self.edit_prep_action = self.window_menu.addAction("Edit prep...")

        self.edit_cvar_action = self.window_menu.addAction("Edit cvar...")

        self.edit_functions_action = self.window_menu.addAction("Edit Functions...")

        self.edit_macros_action = self.window_menu.addAction("Edit Macros...")

        self.edit_defaults_action = self.window_menu.addAction("Edit Defaults...")

        # self.open_win_menu = self.window_menu.addMenu(" Files...")

        # self.window_menu.aboutToShow.connect(self.window_menu_about_to_show)

        # ***

        self.central_widget = self.qs
        self.setCentralWidget(self.central_widget)

        self.setup_file_connections()

        self.setup_edit_connections()

        # self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # print("focus policy: " + str(self.focusPolicy()))
        self.mwe = mainWinEventFilter(self)
        self.installEventFilter(self.mwe)

    @pyqtSlot(bool)
    def set_mouse_panning(self, panning_on):
        if self.glyph_pane:
            if panning_on:
                self.glyph_pane.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    @pyqtSlot(bool)
    def set_mouse_editing(self, editing_on):
        if self.glyph_pane:
            if editing_on:
                self.glyph_pane.setDragMode(QGraphicsView.DragMode.NoDrag)

    @pyqtSlot()
    def preview_error(self):
        emsg =  "Error compiling YAML or Xgridfit code. "
        emsg += "Check the correctness of your code (including any "
        emsg += "functions or macros and the prep program) and try again."
        self.show_error_message(["Error", "Error", emsg])

    @pyqtSlot(object)
    def preview_ready(self, args):
        self.yg_preview.fetch_glyph(args["font"], args["gindex"])
        self.yg_preview.update()

    @pyqtSlot()
    def toggle_auto_preview(self):
        self.auto_preview_update = not self.auto_preview_update
        try:
            self.glyph_pane.viewer.yg_glyph.set_auto_preview_connection()
        except Exception as e:
            # print(e)
            pass

    @pyqtSlot()
    def preview_current_glyph(self):
        try:
            if self.preview_maker != None and self.preview_maker.isRunning():
                # print("Thread is still running!")
                return
        except RuntimeError as e:
            # We get this RuntimeError when self.thread has been garbage collected.
            # It means that it's safe to run the rest of this function.
            # print(e)
            pass
        self.glyph_pane.viewer.yg_glyph.save_source()
        source = self.yg_font.source
        font = self.yg_font.preview_font
        glyph = self.glyph_pane.viewer.yg_glyph.gname
        self.preview_maker = ygPreviewFontMaker(font, source, glyph)
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
        if self.instance_menu != None:
            self.prev_instance_action.setEnabled(True)
            self.next_instance_action.setEnabled(True)
            self.instance_menu.setEnabled(True)

    @pyqtSlot()
    def string_preview_text(self):
        pass

    def update_string_preview(self, s):
        if s != None:
            pass
        else:
            self.yg_string_preview.update()

    @pyqtSlot()
    def show_font_view(self):
        """ Display the modeless dialog in fontViewDialog.py.
        """
        if not self.font_viewer:
            font_name = self.yg_font.font_files.in_font()
            glyph_list = self.yg_font.glyph_list
            self.font_viewer = fontViewDialog(font_name, self.yg_font, glyph_list, self)
        self.font_viewer.show()
        self.font_viewer.activateWindow()

    @pyqtSlot()
    def index_labels(self):
        self.points_as_coords = False
        self.glyph_pane.viewer.set_point_display("index")

    @pyqtSlot()
    def coord_labels(self):
        self.points_as_coords = True
        self.glyph_pane.viewer.set_point_display("coord")

    @pyqtSlot()
    def view_menu_about_to_show(self):
        if self.points_as_coords:
            self.index_label_action.setEnabled(True)
            self.coord_label_action.setEnabled(False)
        else:
            self.index_label_action.setEnabled(False)
            self.coord_label_action.setEnabled(True)

    @pyqtSlot()
    def window_menu_about_to_show(self):
        if len(self.win_list) > 0:
            wins = []
            for w in self.win_list:
                wins.append(w.filename)
            # ***

    @pyqtSlot()
    def file_menu_about_to_show(self):
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
    def preview_menu_about_to_show(self):
        if self.yg_preview != None:
            if self.yg_preview.face != None:
                self.pv_render_mode_menu.setEnabled(True)
            self.pv_show_hints_action.setChecked(self.yg_preview.hinting_on)
            self.pv_show_grid_action.setChecked(self.yg_preview.show_grid)
        self.toggle_auto_preview_action.setChecked(self.auto_preview_update)

    #
    # Connection setup
    #

    # In the hierarchy of major objects, MainWindow and MyView are always present, while
    # ygGlyph and ygGlyphViewer are destroyed whenever we move from one glyph to another.
    # To avoid complications, avoid connecting signals to ygGlyph and ygGlyphView; otherwise,
    # we've got to kill one connection and create another whenever we switch from one glyph
    # to another.
    #
    # These connect menus and toolbar buttons; ygGlyph and ygGlyphViewer have their own
    # signals.

    def setup_editor_connections(self):
        self.compile_action.triggered.connect(self.source_editor.yaml_source)

    def setup_file_connections(self):
        self.save_action.triggered.connect(self.save_yaml_file)
        self.quit_action.triggered.connect(self.quit, type=Qt.ConnectionType.QueuedConnection)
        self.open_action.triggered.connect(self.open_file)
        self.save_font_action.triggered.connect(self.export_font)

    def setup_recents_connections(self):
        for a in self.recents_actions:
            a.triggered.connect(self.open_recent)

    def disconnect_recents_connections(self):
        for a in self.recents_actions:
            a.triggered.disconnect(self.open_recent)

    def setup_hint_connections(self):
        # The "viewer" connections get destroyed whenever we switch glyphs. Wouldn't it be
        # better to move the slots to glyph_pane (QGraphicsView)?
        self.black_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.white_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.gray_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.anchor_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.interpolate_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.shift_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.align_action.triggered.connect(self.glyph_pane.make_hint_from_selection)
        self.make_set_action.triggered.connect(self.glyph_pane.make_set)
        self.make_cv_action.triggered.connect(self.glyph_pane.make_control_value)
        self.make_cv_guess_action.triggered.connect(self.glyph_pane.guess_cv)
        # These two connections don't get destroyed when we switch glyphs.
        # Make sure they're not created over and over.
        self.vertical_action.triggered.connect(self.glyph_pane.switch_to_y)
        self.horizontal_action.triggered.connect(self.glyph_pane.switch_to_x)

    def setup_edit_connections(self):
        self.edit_cvt_action.triggered.connect(self.edit_cvt)
        self.edit_prep_action.triggered.connect(self.edit_prep)
        self.edit_cvar_action.triggered.connect(self.edit_cvar)
        self.edit_functions_action.triggered.connect(self.edit_functions)
        self.edit_macros_action.triggered.connect(self.edit_macros)
        self.edit_defaults_action.triggered.connect(self.edit_defaults)
        self.edit_names_action.triggered.connect(self.edit_names)
        self.edit_properties_action.triggered.connect(self.edit_properties)
        self.to_coords_action.triggered.connect(self.indices_to_coords)
        self.to_indices_action.triggered.connect(self.coords_to_indices)

    def setup_preview_connections(self):
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
        self.pv_show_hints_action.triggered.connect(self.yg_preview.toggle_show_hints)
        self.pv_show_grid_action.triggered.connect(self.yg_preview.toggle_grid)

    def setup_preview_instance_connections(self):
        if self.yg_font.is_variable_font and self.instance_actions != None:
            self.prev_instance_action.triggered.connect(self.yg_preview.next_instance)
            self.next_instance_action.triggered.connect(self.yg_preview.prev_instance)
            for i in self.instance_actions:
                i.triggered.connect(self.yg_preview.set_instance)

    def setup_zoom_connections(self):
        self.zoom_in_action.triggered.connect(self.glyph_pane.zoom)
        self.zoom_out_action.triggered.connect(self.glyph_pane.zoom)
        self.original_size_action.triggered.connect(self.glyph_pane.zoom)

    def setup_point_label_connections(self):
        self.index_label_action.triggered.connect(self.index_labels)
        self.coord_label_action.triggered.connect(self.coord_labels)

    def setup_nav_connections(self):
        self.next_glyph_action.triggered.connect(self.glyph_pane.next_glyph)
        self.previous_glyph_action.triggered.connect(self.glyph_pane.previous_glyph)
        self.goto_action.triggered.connect(self.show_goto_dialog)
        self.glyph_pane.setup_goto_signal(self.show_goto_dialog)
        self.font_view_action.triggered.connect(self.show_font_view)

    def setup_cursor_connections(self):
        self.hand_action.toggled.connect(self.set_mouse_panning)
        self.cursor_action.toggled.connect(self.set_mouse_editing)

    def setup_glyph_pane_connections(self):
        self.setup_nav_connections()
        self.setup_zoom_connections()
        self.source_editor.setup_editor_signals(self.glyph_pane.viewer.yg_glyph.save_editor_source)
        self.source_editor.setup_status_indicator(self.set_status_validity_msg)
        self.setup_cursor_connections()

    def connect_editor_signals(self):
        self.source_editor.setup_editor_signals(self.glyph_pane.viewer.yg_glyph.save_editor_source)

    def disconnect_editor_signals(self):
        self.source_editor.disconnect_editor_signals(self.glyph_pane.viewer.yg_glyph.save_editor_source)

    #
    # GUI setup
    #

    def add_preview(self, previewer):
        self.yg_preview = previewer
        self.yg_string_preview = ygStringPreview(self.yg_preview, self)
        self.preview_scroller = QScrollArea()
        self.preview_scroller.setWidget(self.yg_preview)
        ygpc = ygPreviewContainer(self.preview_scroller, self.yg_string_preview)
        self.qs.addWidget(ygpc)
        self.setup_preview_connections()

    def add_editor(self, editor):
        self.source_editor = editor
        self.qs.addWidget(self.source_editor)

    def add_glyph_pane(self, g):
        # Must be a MyView(QGraphicsView) object.
        self.glyph_pane = g
        self.qs.addWidget(self.glyph_pane)
        self.setup_glyph_pane_connections()
        self.setup_hint_connections()
        self.cleanup_action.triggered.connect(self.glyph_pane.cleanup_yaml_code)

    def set_axis_buttons(self):
        """ To be run right after preferences are loaded and before a file is
            loaded.

        """
        if self.current_axis == "y":
            self.vertical_action.setChecked(True)
        else:
            self.horizontal_action.setChecked(True)
        self.vertical_action.setEnabled(False)
        self.horizontal_action.setEnabled(False)

    def set_up_instance_list(self):
        if self.yg_font.is_variable_font and hasattr(self.yg_font, "instances"):
            self.preview_menu.addSeparator()
            self.prev_instance_action = self.preview_menu.addAction("Previous instance")
            # self.prev_instance_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Left))
            self.prev_instance_action.setShortcut(QKeySequence(Qt.Key.Key_Less))
            self.next_instance_action = self.preview_menu.addAction("Next instance")
            # self.next_instance_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Right))
            self.next_instance_action.setShortcut(QKeySequence(Qt.Key.Key_Greater))
            self.instance_menu = self.preview_menu.addMenu("&Instances")
            self.instance_actions = []
            instance_names = []
            for k in self.yg_font.instances.keys():
                self.instance_actions.append(self.instance_menu.addAction(k))
                instance_names.append(k)
            self.yg_preview.add_instances(self.yg_font.instances)
            self.yg_preview.instance = self.yg_font.default_instance()
            self.prev_instance_action.setEnabled(False)
            self.next_instance_action.setEnabled(False)
            self.instance_menu.setEnabled(False)

    #
    # File operations
    #

    @pyqtSlot()
    def save_yaml_file(self):
        self._save_yaml_file()

    def _save_yaml_file(self):
        if self.yg_font and (not self.yg_font.clean()):
            self.glyph_pane.viewer.yg_glyph.save_source()
            self.yg_font.source_file.save_source()
            self.yg_font.set_clean()

    @pyqtSlot()
    def export_font(self):
        try:
            if self.font_generator != None and self.font_generator.isRunning():
                # print("Thread is still running!")
                return
        except RuntimeError as e:
            # We get this RuntimeError when self.thread has been garbage collected.
            # It means that it's safe to run the rest of this function.
            # print(e)
            pass
        self.glyph_pane.viewer.yg_glyph.save_source()
        source = self.yg_font.source
        new_file_name = self.yg_font.font_files.out_font()
        in_file_name = self.yg_font.font_files.in_font()
        if new_file_name == None or in_file_name == None:
            return
        source = self.yg_font.source
        font = self.yg_font.preview_font
        msg_box = QMessageBox(self)
        msg_box.setText("Ready to export " + new_file_name + "?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel |
                                   QMessageBox.StandardButton.Save)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msg_box.exec()
        if ret == QMessageBox.StandardButton.Cancel:
            return
        self.font_generator = ygFontGenerator(font, source, new_file_name)
        self.font_generator.finished.connect(self.font_generator.deleteLater)
        self.font_generator.sig_font_gen_done.connect(self.font_gen_finished)
        self.font_generator.sig_font_gen_error.connect(self.font_gen_error)
        self.font_generator.start()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar_action = self.toolbar.insertWidget(self.spacer_action, self.progress_bar)

    @pyqtSlot(object)
    def font_gen_finished(self, failed_list):
        self.toolbar.removeAction(self.progress_bar_action)
        self.progress_bar = None
        self.progress_bar_action = None
        if len(failed_list) > 0:
            emsg = "Failed to compile one or more glyphs: "
            for f in failed_list:
                emsg += (f + " ")
            self.show_error_message(["Error", "Error", emsg])

    @pyqtSlot()
    def font_gen_error(self):
        self.toolbar.removeAction(self.progress_bar_action)
        self.progress_bar = None
        self.progress_bar_action = None
        emsg =  "Failed to generate the font. This most likely due to an error "
        emsg += "in function, macro, or prep code or in your cvt or cvar "
        emsg += "entries."
        self.show_error_message(["Error", "Error", emsg])
        return

    @pyqtSlot()
    def open_recent(self):
        f = self.sender().text()
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
    def open_file(self):
        f = QFileDialog.getOpenFileName(self, "Open TrueType font or YAML file",
                                               "",
                                               "Files (*.ttf *.yaml)")
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
            self.show_error_message(["Error", "Error", emsg])
        if result == 1:
            self.set_preferences()
            w = MainWindow(self.app, win_list=self.win_list, prefs=self.preferences)
            result = w._open(f)
            if result == 0:
                w.show()
                self.win_list.append(w)

    def _open(self, f):
        """ Returns 0 if file opened in this window
            Returns 1 if this window already has a file open
            Returns 2 if the file is already open (the window is activated and brought to top)

        """
        if self.glyph_pane:
            return 1
        if type(f) is str:
            filename = f
        else:
            filename = f[0]
        for w in self.win_list:
            if filename == w.filename:
                w.activateWindow()
                w.raise_()
                return 2
        self.filename = filename
        # self.open_action.setEnabled(False)
        # self.recent_menu.setEnabled(False)
        self.save_action.setEnabled(True)
        self.save_font_action.setEnabled(True)
        self.goto_action.setEnabled(True)
        self.black_action.setEnabled(True)
        self.white_action.setEnabled(True)
        self.gray_action.setEnabled(True)
        self.shift_action.setEnabled(True)
        self.align_action.setEnabled(True)
        self.interpolate_action.setEnabled(True)
        self.anchor_action.setEnabled(True)
        self.make_cv_action.setEnabled(True)
        self.make_cv_guess_action.setEnabled(True)
        self.make_set_action.setEnabled(True)
        self.vertical_action.setEnabled(True)
        self.horizontal_action.setEnabled(True)
        self.cursor_action.setEnabled(True)
        self.hand_action.setEnabled(True)
        self.save_current_glyph_action.setEnabled(True)
        self.code_menu.setEnabled(True)
        self.view_menu.setEnabled(True)

        if filename and len(filename) > 0:
            self.preferences.add_recent(filename)
            split_fn = os.path.splitext(filename)
            fn_base = split_fn[0]
            extension = split_fn[1]
            yaml_source = None
            if extension == ".ttf":
                yaml_filename = fn_base + ".yaml"
                self.preferences.add_recent(yaml_filename)
                yaml_source = {}
                yaml_source["font"] = {}
                yaml_source["font"]["in"] = copy.copy(filename)
                yaml_source["font"]["out"] = fn_base + "-hinted" + extension
                yaml_source["defaults"] = {}
                yaml_source["cvt"] = {}
                yaml_source["prep"] = {}
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
                yaml_source["prep"] = {"code": prep_code}
                yaml_source["functions"] = {}
                yaml_source["macros"] = {}
                yaml_source["glyphs"] = {}
                filename = yaml_filename
            # Wrong. We should use familyname + stylename to index here.
            # current_font appears not to be used!
            self.preferences["current_font"] = filename

            self.yg_preview = ygPreview()
            self.add_preview(self.yg_preview)
            self.yg_preview.set_up_signal(self.update_string_preview)
            self.source_editor = ygYAMLEditor(self.preferences)
            self.add_editor(self.source_editor)
            if yaml_source != None:
                self.yg_font = ygFont(self, yaml_source, yaml_filename=filename)
            else:
                self.yg_font = ygFont(self, filename)
            if ("current_glyph" in self.preferences and
                self.yg_font.full_name() in self.preferences["current_glyph"]):
                initGlyph = self.preferences["current_glyph"][self.yg_font.full_name()]
            else:
                initGlyph = "A"
            modelGlyph = ygGlyph(self.preferences, self.yg_font, initGlyph)
            modelGlyph.set_yaml_editor(self.source_editor)
            viewer = ygGlyphViewer(self.preferences, modelGlyph)
            view = MyView(self.preferences, viewer, self.yg_font)
            self.add_glyph_pane(view)
            view.centerOn(view.viewer.center_x, view.sceneRect().center().y())
            # self.set_background()
            self.set_window_title()
            self.set_up_instance_list()
            self.setup_editor_connections()
            self.setup_preview_instance_connections()
            self.setup_point_label_connections()
        return 0

    #
    # GUI management
    #

    def set_window_title(self):
        """ And also the status bar
        """
        base = "YGT"
        if self.yg_font:
            base += " -- " + str(self.yg_font.family_name()) + "-" + str(self.yg_font.style_name())
            if not self.yg_font.clean():
                base += "*"
        self.setWindowTitle(base)
        self.set_statusbar_text(None)

    def set_statusbar_text(self, valid):
        status_text =  self.glyph_pane.viewer.yg_glyph.gname
        status_text += " - " + unicode_cat_names[self.glyph_pane.viewer.yg_glyph.get_category()]
        status_text += " (" + self.glyph_pane.viewer.yg_glyph.current_axis() + ")"
        if valid != None:
            status_text += " ("
            if valid:
                status_text += "Valid)"
            else:
                status_text += "Invalid)"
        self.statusbar_label.setText(status_text)

    def set_status_validity_msg(self, t):

        self.set_statusbar_text(bool(t))

    def show_error_message(self, msg_list):
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
    def indices_to_coords(self):
        try:
            self.glyph_pane.viewer.yg_glyph.indices_to_coords()
        except Exception as e:
            print(e)

    @pyqtSlot()
    def coords_to_indices(self):
        try:
            self.glyph_pane.viewer.yg_glyph.coords_to_indices()
        except Exception as e:
            print(e)

    @pyqtSlot()
    def edit_cvt(self):
        self.cvt_editor = editorDialog(self.preferences,
                                        self.yg_font.cvt,
                                        "cvt",
                                        is_cvt_valid)
        self.cvt_editor.show()
        # self.cvt_editor.raise()
        self.cvt_editor.activateWindow()

    @pyqtSlot()
    def edit_prep(self):
        self.cvt_editor = editorDialog(self.preferences,
                                                self.yg_font.prep,
                                                "prep",
                                                is_prep_valid)
        self.cvt_editor.show()
        # self.cvt_editor.raise()
        self.cvt_editor.activateWindow()

    @pyqtSlot()
    def edit_cvar(self):
        self.cvar_editor = editorDialog(self.preferences,
                                                 self.yg_font.cvar,
                                                 "cvar",
                                                 is_cvar_valid,
                                                 top_structure="list")
        self.cvar_editor.show()
        # self.cvar_editor.raise()
        self.cvar_editor.activateWindow()

    @pyqtSlot()
    def edit_functions(self):
        self.function_editor = editorDialog(self.preferences,
                                                     self.yg_font.functions_func,
                                                     "functions",
                                                     are_functions_valid)
        self.function_editor.show()
        # self.function_editor.raise()
        self.function_editor.activateWindow()

    @pyqtSlot()
    def edit_macros(self):
        self.macro_editor = editorDialog(self.preferences,
                                                  self.yg_font.macros_func,
                                                  "macros",
                                                  are_macros_valid)
        self.macro_editor.show()
        # self.macro_editor.raise()
        self.macro_editor.activateWindow()

    @pyqtSlot()
    def edit_defaults(self):
        self.default_editor = editorDialog(self.preferences,
                                                    self.yg_font.defaults,
                                                    "defaults",
                                                    are_defaults_valid)
        self.default_editor.show()
        # self.default_editor.raise()
        self.default_editor.activateWindow()

    @pyqtSlot()
    def edit_names(self):
        self.names_editor = editorDialog(self.preferences,
                                         self.glyph_pane.viewer.yg_glyph.names,
                                         "names",
                                         are_names_valid)
        self.names_editor.show()
        self.names_editor.activateWindow()

    @pyqtSlot()
    def edit_properties(self):
        self.properties_editor = editorDialog(self.preferences,
                                              self.glyph_pane.viewer.yg_glyph.props,
                                              "properties",
                                              are_properties_valid)
        self.properties_editor.show()
        self.properties_editor.activateWindow()

    #
    # Miscellaneous dialogs
    #

    @pyqtSlot()
    def show_goto_dialog(self):
        text, ok = QInputDialog().getText(self, "Go to glyph", "Glyph name:",
                                          QLineEdit.EchoMode.Normal)
        if ok and text:
            self.glyph_pane.go_to_glyph(text)

    @pyqtSlot()
    def show_ppem_dialog(self):
        text, ok = QInputDialog().getText(self, "Set Points per Em", "Points per em:",
                                          QLineEdit.EchoMode.Normal)
        if ok and text:
            self.yg_preview.set_size(text)

    #
    # Program exit
    #

    def save_query(self):
        msg_box = QMessageBox()
        msg_box.setText("The YAML source has been modified.")
        msg_box.setInformativeText("Do you want to save it?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Discard |
                                   QMessageBox.StandardButton.Cancel |
                                   QMessageBox.StandardButton.Save)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
        ret = msg_box.exec()
        if ret == QMessageBox.StandardButton.Cancel:
            return 1
        if ret == QMessageBox.StandardButton.Save:
            self._save_yaml_file()
            return 0
        return 2

    def del_from_win_list(self, w):
        try:
            self.win_list.remove(w)
        except ValueError:
            pass

    def closeEvent(self, event):
        if self.yg_font == None:
            self.del_from_win_list(self)
            event.accept()
        elif self.yg_font.clean():
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

    def all_clean(self):
        for w in self.win_list:
            if not w.yg_font.clean():
                return False
        return True

    def quit(self):
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
                if not w.yg_font.clean():
                    r = w.save_query()
                    if r != 2:
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

    def get_preferences(self, prefs):
        self.preferences = prefs
        self.points_as_coords = self.preferences.points_as_coords()
        self.zoom_factor = self.preferences.zoom_factor()
        self.show_off_curve_points = self.preferences.show_off_curve_points()
        self.show_point_numbers = self.preferences.show_point_numbers()
        self.current_axis = self.preferences.current_axis()

    def set_preferences(self):
        self.preferences.set_points_as_coords(self.points_as_coords)
        self.preferences.set_zoom_factor(self.zoom_factor)
        self.preferences.set_show_off_curve_points(self.show_off_curve_points)
        self.preferences.set_show_point_numbers(self.show_point_numbers)
        self.preferences.set_current_axis(self.current_axis)



class mainWinEventFilter(QObject):
    def __init__(self, top_win):
        super().__init__()
        self.top_window = top_win

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ActivationChange:
            if self.top_window.isActiveWindow():
                self.top_window.preferences["top_window"] = self.top_window
        return super().eventFilter(source, event)




# if __name__ == "__main__":
def main():

    # print(dir(Qt.Key))

    app = QApplication([])
    top_window = MainWindow(app)
    top_window.get_preferences(open_config(top_window))
    app.setWindowIcon(QIcon(top_window.icon_path + "program.png"))
    qg = top_window.screen().availableGeometry()
    x = qg.x() + 20
    y = qg.y() + 20
    width = qg.width() * 0.66
    height = qg.height() * 0.75
    top_window.setGeometry(int(x), int(y), int(width), int(height))
    top_window.show()
    sys.exit(app.exec())
