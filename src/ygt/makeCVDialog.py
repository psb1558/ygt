import copy
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QComboBox,
                             QLineEdit,
                             QLabel,
                             QWidget,
                             QTabWidget,
                             QListWidget,
                             QPushButton,
                             QTableView)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import (QIntValidator,
                         QDoubleValidator,
                         QUndoCommand,
                         QUndoStack)
from .ygModel import (unicode_categories,
                      unicode_cat_names,
                      reverse_unicode_cat_names,
                      ygMasters,
                      random_id)
from .ygYAMLEditor import editorPane
from .ygSchema import is_cvt_valid

NEW_CV_NAME    = "New_Control_Value"
NEW_CV_CONTENT = {"val": 0, "axis": "y", "type": "pos"}

# The problem in this file is keeping model and view in sync when individual widgets
# have got their own pointers to CVs. Instead, give them a pointer to an ancestor
# object that has access functions for the things they need (chiefly the current CV).
#
# Here is the structure of the CVT edit window:
#
# cvtWindow ---|
#              |--- cvEditPane ---|
#              |                  | --- QListWidget
#              |                  | --- cvWidget ---|
#              |                                    | --- general_tab
#              |                                    | --- link tab
#              |                                    | --- variants tab
#              |--- editorPane (cvt source)
#              |--- mastersWidget ---|
#                                    |--- QListWidget
#                                    |--- masterWidget

class cvSource:

    def send_error_message(self, d: dict): ...

    def cvt(self): ...

    def current_cv(self): ...

    def current_cv_name(self): ...

    def set_cv_name(self, s: str): ...

    def from_current_cv(self, s: str): ...

    def set_in_current_cv(self, k: str, s, fallback: None): ...

    def has_key(self, k: str): ...

    def del_key(self, k: str): ...



class cvEditPane(QWidget, cvSource):
    """ A widget with a list of CVs and a cvWidget. Click in the
        list to display and edit that CV.
    """
    def __init__(self, owner, yg_font, preferences):
        super().__init__()
        self.owner = owner
        self.yg_font = yg_font
        self._cvt = self.yg_font.cvt
        self.preferences = preferences
        self.layout = QHBoxLayout()

        # Set up CV list.

        self.cv_list_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.cv_list = QListWidget()
        self.cv_list.addItems(self._cvt.keys())
        self.current_list_item = self.cv_list.item(0)
        self.cv_list.setCurrentItem(self.current_list_item)
        self._current_cv_name = self.current_list_item.text()
        self.cv_list.itemActivated.connect(self.new_item)

        # And the edit pane.

        self._current_cv = self._cvt.get_cv(self._current_cv_name)
        self.edit_pane = cvWidget(self, self.yg_font, self)

        # Put them together

        self.cv_list_layout.addWidget(self.cv_list)
        add_button = QPushButton("Add")
        del_button = QPushButton("Delete")
        self.button_layout.addWidget(add_button)
        self.button_layout.addWidget(del_button)
        add_button.clicked.connect(self.add_cv)
        del_button.clicked.connect(self.del_cv)
        self.cv_list_layout.addLayout(self.button_layout)
        self.layout.addLayout(self.cv_list_layout)
        self.layout.addWidget(self.edit_pane)
        self.setLayout(self.layout)

    def send_error_message(self, d: dict):
        self.yg_font.send_error_message(d)

    def add_cv(self):
        self._current_cv_name = NEW_CV_NAME
        self._cvt.add_cv(self._current_cv_name, NEW_CV_CONTENT)
        self.cv_list.addItem(self._current_cv_name)
        matches = self.cv_list.findItems(self._current_cv_name, Qt.MatchFlag.MatchExactly)
        if len(matches) > 0:
            self.current_list_item = matches[0]
            self.cv_list.setCurrentItem(self.current_list_item)
            self.new_item(self.current_list_item, forced=True)

    def change_name_in_list(self, n):
        self.current_list_item.setText(n)

    def del_cv(self):
        self._cvt.del_cv(self._current_cv_name)
        self.cv_list.clear()
        try:
            self._current_cv_name = list(self._cvt.keys())[0]
        except IndexError:
            return
        self.refresh()

    def refresh(self):
        """ This is the place to figure out whether the source
            or masters have been changed: if not, we don't have to
            go through all this.
        """
        if not len(self._cvt):
            self.add_cv()
        self._current_cv = self._cvt.get_cv(self._current_cv_name)
        self.cv_list.clear()
        self.cv_list.addItems(self._cvt.keys())
        matches = self.cv_list.findItems(self._current_cv_name, Qt.MatchFlag.MatchExactly)
        if len(matches) > 0:
            self.cv_list.setCurrentItem(matches[0])
        else:
            try:
                current_item = self.cv_list.item(0)
                self.cv_list.setCurrentItem(current_item)
                self._current_cv_name = current_item.text()
                self._current_cv = self._cvt.get_cv(self._current_cv_name)
            except Exception:
                pass
        self.edit_pane.refresh(self)

    def fixup(self):
        self.edit_pane.fixup()

    def new_item(self, list_item, forced=False):
        """ Switch the view to another cv. Simply delete the
            old cv editing pane and create a new one to put
            in its place.
        """
        new_cv_name = list_item.text()
        if forced or new_cv_name != self._current_cv_name:
            old_pane = self.layout.itemAt(1)
            self.layout.removeItem(old_pane)
            old_pane.widget().deleteLater()
            self._current_cv_name = new_cv_name
            self._current_cv = self._cvt.get_cv(self._current_cv_name)
            self.edit_pane = cvWidget(self, self.yg_font, self)
            self.layout.addWidget(self.edit_pane)

    def cvt(self):
        return self._cvt

    def current_cv(self):
        return self._current_cv
    
    def current_cv_name(self):
        return self._current_cv_name

    def set_cv_name(self, s: str):
        self._current_cv_name = s
    
    def from_current_cv(self, s: str):
        try:
            return self._current_cv[s]
        except KeyError:
            return None

    def set_in_current_cv(self, k: str, s, fallback = None):
        if s == "None" or s == "" or s == None:
            if fallback != None:
                self._cvt.set_cv_property(self.current_cv_name(), k, fallback)
            else:
                if k in self._current_cv:
                    self._cvt.del_cv(k)
        else:
            self._cvt.set_cv_property(self.current_cv_name(), k, s)

    def has_key(self, k: str) -> bool:
        return k in self._current_cv

    def del_key(self, k: str):
        self._cvt.del_cv_property(self.current_cv_name(), k)

    def rename_cv(self, old_name, new_name):
        self._cvt.rename(old_name, new_name)

    def showEvent(self, event):
        self.refresh()

    def hideEvent(self, event):
        self.fixup()



class cvtWindow(QWidget):
    """ A one-stop shop for everything having to do with CVs.

        Three tabs: 1.) for GUI editing of Control Values, 2.) for editing
        CVT source, 3.) only with variable fonts, "Masters."
    
        On the CV tab, 2 sections: on left, a QListWidget displaying the
        names of the CVs; on right, a QTabWidget for editing a single CV.
        The tabs are 1.) General tab, 2.) "Same-As" tab, 3.) for variable
        fonts only, a "Variants" tab. There should also be buttons for
        adding and deleting CVs.

        On the "Masters" tab, 1.) a list of masters (or regions) on the
        left, and 2.) a pane for editing axes/values on the right.
    """
    def __init__(self, yg_font, preferences):
        super().__init__()
        self.yg_font = yg_font
        self.cvt = self.yg_font.cvt
        self.preferences = preferences
        self.layout = QVBoxLayout()

        # Set up tabs

        self.tabs = QTabWidget()
        self.cv_tab = cvEditPane(self, self.yg_font, self.preferences)
        self._empty_string = "{}\n"
        self.source_tab = editorPane(self, self.cvt, is_cvt_valid, save_on_focus_out=True)
        self.source_tab.setup_error_signal(self.yg_font.send_error_message)
        self.masters_tab = None
        if self.yg_font.is_variable_font:
            self.masters_tab = mastersWidget(self, self.yg_font)
        self.tabs.addTab(self.cv_tab, "Control Values")
        self.tabs.addTab(self.source_tab, "Source")
        if self.yg_font.is_variable_font:
            self.tabs.addTab(self.masters_tab, "Masters")
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        self.window().setWindowTitle("Control Values")

    def undo_state_active(self):
        if not self.cvt.undo_stack.active():
            self.cvt.undo_stack.setActive(True)

    def closeEvent(self, event):
        self.hide()

    @pyqtSlot()
    def refresh(self):
        self.cv_tab.refresh()
        self.source_tab.refresh()
        if self.masters_tab:
            self.masters_tab.refresh()

    def event(self, event):
        if event.type() == event.Type.WindowActivate:
            self.cvt.undo_stack.setActive(True)
        return super().event(event)



class mastersWidget(QWidget):
    """ A pane for editing masters.
    """
    def __init__(self, owner, yg_font):
        super().__init__()
        self.owner = owner
        self.yg_font = yg_font
        self.masters = self.yg_font.masters

        self.layout = QHBoxLayout()
        self.master_list_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.master_list = QListWidget()
        self.master_list.addItems(self.masters.names())
        self.current_list_item = self.master_list.item(0)
        self.master_list.setCurrentItem(self.current_list_item)
        self.master_list.itemActivated.connect(self.new_item)

        self._current_master = self.masters.master_by_name(self.current_list_item.text())

        # And the edit pane.

        self.edit_pane = masterWidget(self.masters, self._current_master[0], self.yg_font)

        self.master_list_layout.addWidget(self.master_list)
        add_button = QPushButton("Add")
        del_button = QPushButton("Delete")
        self.button_layout.addWidget(add_button)
        self.button_layout.addWidget(del_button)
        add_button.clicked.connect(self.add_master)
        del_button.clicked.connect(self.del_master)
        self.master_list_layout.addLayout(self.button_layout)
        self.refresh_variants_button = QPushButton("Generate Variant Control Values")
        self.refresh_variants_button.clicked.connect(self.yg_font.refresh_variant_cvs)
        self.master_list_layout.addWidget(self.refresh_variants_button)
        self.layout.addLayout(self.master_list_layout)
        self.layout.addWidget(self.edit_pane)
        #self.edit_pane_layout = QVBoxLayout()
        #self.edit_pane_layout.addWidget(self.edit_pane)
        #self.layout.addLayout(self.edit_pane_layout)
        self.setLayout(self.layout)

    def current_master_name(self):
        return self._current_master[1]["name"]

    def current_master_id(self):
        return self._current_master[0]

    def new_item(self, list_item, forced=False):
        new_master_name = list_item.text()
        new_master = self.masters.master_by_name(new_master_name)
        if forced or new_master_name != self.current_master_name():
            old_pane = self.layout.itemAt(1)
            self.layout.removeItem(old_pane)
            old_pane.widget().deleteLater()
            self._current_master = new_master
            self.edit_pane = masterWidget(self.masters, self.current_master_id(), self.yg_font)
            self.layout.addWidget(self.edit_pane)

    def add_master(self):
        master_dict = {}
        axis_tags = self.yg_font.axis_tags()
        for a in axis_tags:
            master_dict[a] = 0.0
        master_id = random_id("master")
        master_vals = {"name": master_id, "vals": master_dict}
        self.yg_font.masters.add_master(master_id, master_vals)
        self.refresh()

    def del_master(self):
        self.yg_font.masters.del_by_name(self.current_master_name())
        self.master_list.clear()
        try:
            self._current_master = self.masters.master_by_name(self.yg_font.masters.names()[0])
        except IndexError:
            return
        self.refresh()

    def refresh(self):
        if not len(self.yg_font.masters):
            return
        self.master_list.clear()
        self.master_list.addItems(self.yg_font.masters.names())
        matches = self.master_list.findItems(self.current_master_name(), Qt.MatchFlag.MatchExactly)
        if len(matches) > 0:
            self.master_list.setCurrentItem(matches[0])
        else:
            try:
                current_item = self.master_list.item(0)
                self.master_list.setCurrentItem(current_item)
                self._current_master = self.yg_font.masters.master_by_name(current_item.text())
            except Exception:
                pass
        self.edit_pane.refresh(self._current_master)



class masterWidget(QWidget):
    """ A pane for editing a master
    """
    def __init__(self, masters, m_id, yg_font):
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        self.master_layout = QVBoxLayout()
        self.name_layout = QHBoxLayout()
        self.name_layout.addWidget(QLabel("Name"))
        self.master_name_widget = masterNameWidget(self.masters, self.m_id)
        self.name_layout.addWidget(self.master_name_widget)
        self.master_layout.addLayout(self.name_layout)
        self.names = []
        axis_tags = yg_font.axis_tags()
        for axis_name in axis_tags:
            axis_val_layout = QHBoxLayout()
            axis_val_layout.addWidget(QLabel(axis_name))
            n = masterValWidget(self.masters, self.m_id, axis_name)
            self.names.append(n)
            axis_val_layout.addWidget(n)
            self.master_layout.addLayout(axis_val_layout)
        self.setLayout(self.master_layout)

    def refresh(self, m):
        """ Where m is a master tuple (id, dict of axis:val)
        """
        self.m_id = m[0]
        self.master_name_widget.refresh(m)
        for n in self.names:
            n.refresh(m)

    #def event(self, event):
    #    print(event)
    #    print(event.type())
    #    print(event.spontaneous())
    #    return super().event(event)



class cvDeltaWidget(QTableView):
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.delta_data = self.cv_source.cvt().get_deltas(self.cv_source.current_cv_name())
        self.setModel(self.delta_data)



class cvWidget(QWidget):
    """ A pane for making and editing CVs. This class keeps a reference
        to the CV being edited and updates it as the user works with the
        controls.

        params:

        cv_name (str): The current name (if any) of the cv. If this
        isn't initially an empty string, the QLineEdit for it is
        disabled.

        cv (dict): The kind of dict ygt stores cv info in. Can contain
        initial values or values of the cv being edited.

        cvt (dict): This font's cvt.

        preferences (ygPreferences): provides reference to this font's
        top_window.

        title (str): Title for this dialog box.
    """

    def __init__(self, cv_source: cvSource, yg_font, owner, parent=None, delta_pane=True, variant_pane=True):
        super().__init__(parent=parent)
        self.yg_font = yg_font
        self.owner = owner
        self.cv_source = cv_source
        self.layout = QVBoxLayout()

        # Set up tabs

        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.link_tab = QWidget()
        self.delta_tab = None
        self.variants_tab = None
        self.masters = None
        if self.yg_font.is_variable_font and variant_pane:
            self.variants_tab = QWidget()
            self.masters = self.yg_font.masters
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.link_tab, "Same As")
        if delta_pane:
            self.delta_tab = QWidget()
            self.tabs.addTab(self.delta_tab, "Deltas")
        if self.variants_tab:
            self.tabs.addTab(self.variants_tab, "Variants")

        # set up general tab

        self.general_tab_layout = QVBoxLayout()
        self.cv_type_widget = cvTypeWidget(self.cv_source)
        self.cv_color_widget = cvColorWidget(self.cv_source)
        self.cv_axis_widget = cvAxisWidget(self.cv_source)
        self.cv_val_widget = cvValueWidget(self.cv_source)
        self.cv_name_widget = cvNameWidget(self.cv_source, owner=self.owner)
        self.cv_cat_widget = cvUCatWidget(self.cv_source)
        self.cv_suffix_widget = cvSuffixWidget(self.cv_source)

        self.gen_widgets = []

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("name"))
        self.gen_widgets[-1].addWidget(self.cv_name_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("val"))
        self.gen_widgets[-1].addWidget(self.cv_val_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("type"))
        self.gen_widgets[-1].addWidget(self.cv_type_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("axis"))
        self.gen_widgets[-1].addWidget(self.cv_axis_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("cat"))
        self.gen_widgets[-1].addWidget(self.cv_cat_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("suffix"))
        self.gen_widgets[-1].addWidget(self.cv_suffix_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("distance type"))
        self.gen_widgets[-1].addWidget(self.cv_color_widget)

        # Set up link tab

        self.link_tab_layout = QVBoxLayout()

        self.cv_below_ppem_widget = cvPPEMWidget(self.cv_source, "below")
        self.cv_above_ppem_widget = cvPPEMWidget(self.cv_source, "above")
        self.cv_below_names_widget = cvNamesWidget(self.cv_source,
                                                   "below",
                                                   self.yg_font,
                                                   ppem_widget=self.cv_below_ppem_widget)
        self.cv_above_names_widget = cvNamesWidget(self.cv_source,
                                                   "above",
                                                   self.yg_font,
                                                   ppem_widget=self.cv_above_ppem_widget)
        self.cv_below_ppem_widget.name_widget = self.cv_below_names_widget
        self.cv_above_ppem_widget.name_widget = self.cv_above_names_widget

        self.link_widgets = []

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(self.cv_below_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("below"))
        self.link_widgets[-1].addWidget(self.cv_below_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("and"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(self.cv_above_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("above"))
        self.link_widgets[-1].addWidget(self.cv_above_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        # Set up deltas tab

        self.delta_tab_layout = None
        if self.delta_tab:
            self.delta_tab_layout = QVBoxLayout()
            self.delta_pane = cvDeltaWidget(self.cv_source)
            self.delta_button_layout = QHBoxLayout()
            add_delta_button = QPushButton("Add")
            del_delta_button = QPushButton("Delete")
            add_delta_button.clicked.connect(self.delta_pane.model().new_row)
            del_delta_button.clicked.connect(self.del_delta_row)
            self.delta_button_layout.addWidget(add_delta_button)
            self.delta_button_layout.addWidget(del_delta_button)
            self.delta_tab_layout.addWidget(self.delta_pane)
            self.delta_tab_layout.addLayout(self.delta_button_layout)

        # Set up variants tab

        self.variants_tab_layout = None
        if self.variants_tab:
            self.variants_tab_layout = QVBoxLayout()
            self.var_widgets = []
            self.var_layouts = []
            master_keys = self.masters.keys()
            for k in master_keys:
                self.var_layouts.append(QHBoxLayout())
                self.var_layouts[-1].addWidget(QLabel(self.masters.get_master_name(k)))
                self.var_widgets.append(cvVarWidget(k, self.cv_source))
                self.var_layouts[-1].addWidget(self.var_widgets[-1])

        for w in self.gen_widgets:
            self.general_tab_layout.addLayout(w)
        for w in self.link_widgets:
            self.link_tab_layout.addLayout(w)
        if self.variants_tab:
            for w in self.var_layouts:
                self.variants_tab_layout.addLayout(w)

        self.general_tab.setLayout(self.general_tab_layout)
        self.link_tab.setLayout(self.link_tab_layout)
        if self.delta_tab:
            self.delta_tab.setLayout(self.delta_tab_layout)
        if self.variants_tab:
            self.variants_tab.setLayout(self.variants_tab_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def del_delta_row(self):
        i = self.delta_pane.selectedIndexes()
        if len(i) > 0:
            self.delta_pane.model().deleteRows(i[0].row(), 1)

    def refresh(self, cv_source):
        """ If we're coming from the source pane, every cv in the
            cvt will have been replaced, so references to it have
            got to be refreshed and the widgets updated as needed.
            Think about whether there's a less awkward way to do
            this.
        """
        self.cv_source = cv_source
        self.cv_name_widget.refresh(self.cv_source)
        self.cv_type_widget.refresh(self.cv_source)
        self.cv_axis_widget.refresh(self.cv_source)
        self.cv_color_widget.refresh(self.cv_source)
        self.cv_val_widget.refresh(self.cv_source)
        self.cv_cat_widget.refresh(self.cv_source)
        self.cv_suffix_widget.refresh(self.cv_source)
        self.cv_below_ppem_widget.refresh(self.cv_source)
        self.cv_above_ppem_widget.refresh(self.cv_source)
        self.cv_below_names_widget.refresh(self.cv_source)
        self.cv_above_names_widget.refresh(self.cv_source)
        if self.masters:
            for w in self.var_widgets:
                w.refresh(self.cv_source)

    def fixup(self):
        self.cv_name_widget.fixup()
        self.cv_type_widget.fixup()
        self.cv_axis_widget.fixup()
        self.cv_color_widget.fixup()
        self.cv_val_widget.fixup()
        self.cv_cat_widget.fixup()
        self.cv_suffix_widget.fixup()
        self.cv_below_ppem_widget.fixup()
        self.cv_above_ppem_widget.fixup()
        self.cv_below_names_widget.fixup()
        self.cv_above_names_widget.fixup()
        if self.masters:
            for w in self.var_widgets:
                w.fixup()

    #def event(self, event):
    #    print(event)
    #    return super().event(event)



class makeCVDialog(QDialog, cvSource):
    """ A dialog for creating a cv. This doesn't edit the cvt source
        directly, but instead works on a fragment of cv code to be
        added when the accept() function is called.
    """
    def __init__(self, p1, p2, yg_glyph, preferences):
        super().__init__()
        self.top_window = preferences.top_window()
        self.yg_font = yg_glyph.yg_font
        self._cvt = self.yg_font.cvt
        self.cv = {}
        self.cv_name = ""
        self.axis = preferences.top_window().current_axis
        self.cv["axis"] = self.axis
        if p2 != None:
            init_type = "dist"
            origin_indices = [p1.index, p2.index]
        else:
            init_type = "pos"
            origin_indices = [p1.index]
        self.cv["type"] = init_type
        val = 0
        if self.axis == "y":
            if init_type == "pos":
                val = p1.font_y
            else:
                val = abs(p1.font_y - p2.font_y)
        else:
            if init_type == "pos":
                val = p1.font_x
            else:
                val = abs(p1.font_x - p2.font_x)
        self.cv["val"] = val
        self.cv["origin"] = {"glyph": yg_glyph.gname, "ptnum": origin_indices}

        self.layout = QVBoxLayout()

        self.pane = cvWidget(self, self.yg_font, None, delta_pane=False, variant_pane=False)

        # Set up buttons

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout.addWidget(self.pane)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        self.setWindowTitle("Make Control Value")

    def send_error_message(self, d: dict):
        self.yg_font.send_error_message(d)

    def cvt(self):
        return self._cvt
    
    def current_cv(self):
        return self.cv
    
    def current_cv_name(self):
        return self.cv_name

    def set_cv_name(self, s: str):
        self.cv_name = s

    def from_current_cv(self, s: str):
        try:
            return self.cv[s]
        except KeyError:
            return None

    def set_in_current_cv(self, k: str, s, fallback = None):
        if s == "None" or s == "" or s == None:
            if fallback != None:
                self.cv[k] = fallback
            else:
                if k in self._current_cv:
                    del self._current_cv[k]
        else:
            self.cv[k] = s

    def has_key(self, k: str):
        return k in self.cv

    def del_key(self, k: str):
        try:
            del self.cv[k]
        except KeyError:
            pass

    def accept(self):
        self.pane.fixup()
        if self.cv_name and len(self.cv) > 0:
            self._cvt.add_cv(self.cv_name, self.cv)
        super().accept()

    def showEvent(self, event):
        self._cvt.undo_stack.setActive(True)


class cvNameWidget(QLineEdit):
    """ A widget for editing the name of a cv. Disable when it shouldn't
        be edited.
    """
    def __init__(self, cv_source: cvSource, owner=None):
        super().__init__()
        self.owner = owner
        self.cv_source = cv_source
        self.cv_name = self.cv_source.current_cv_name()
        self.dirty = False
        if len(self.cv_name) > 0:
            self.setText(self.cv_name)
            if self.cv_name != NEW_CV_NAME:
                self.setEnabled(False)
        if self.isEnabled():
            self.editingFinished.connect(self.text_changed)
            self.textChanged.connect(self.set_dirty)
        self.last_val = self.cv_name

    def _text(self):
        return self.text().strip()
    
    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        t = self._text()
        if self.isEnabled() and self.dirty and t != self.last_val:
            # If the cv name changes, the original cv in the source tree
            # has to be deleted and a new cv entered under the new name.
            # We can either do that (at some risk of bugginess) or disable
            # the cv name widget when the cv is being edited (as opposed
            # to created).
            old_name = self.cv_source.current_cv_name()
            self.cv_source.set_cv_name(t)
            if self.owner != None:
                self.owner.change_name_in_list(t)
                self.owner.rename_cv(old_name, t)
            self.last_val = t
            self.set_clean()

    def text_changed(self):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        self.setText(self.cv_source.current_cv_name())
        self.set_clean()



class cvTypeWidget(QComboBox):
    """ Widget for choosing a CV type.
    """
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.addItem("pos")
        self.addItem("dist")
        t = self.cv_source.from_current_cv("type")
        self.setCurrentText((lambda : "y" if not t else t)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self):
        return self.currentText()

    def fixup(self):
        t = self.currentText()
        if t != self.last_val:
            self.cv_source.set_in_current_cv("type", self.currentText())
            self.last_val = t

    def text_changed(self, event):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        self.setCurrentText(self.cv_source.from_current_cv("type"))



class cvColorWidget(QComboBox):
    """ Widget for choosing a distance type.
    """
    def __init__(self, cv_source):
        super().__init__()
        self.cv_source = cv_source
        self.addItem("None")
        self.addItem("black")
        self.addItem("white")
        self.addItem("gray")
        col = self.cv_source.from_current_cv("col")
        self.setCurrentText((lambda : "None" if not col else col)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if new_text != self.last_val:
            if self.cv_source.current_cv():
                if new_text != "None":
                    self.cv_source.set_in_current_cv("col", new_text)
                else:
                    self.cv_source.del_key("col")
            self.last_val = new_text

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("col"):
            self.setCurrentText(self.cv_source.from_current_cv("col"))
        else:
            self.setCurrentText("None")



class cvAxisWidget(QComboBox):
    """ Widget for choosing an axis for a CV.
    """
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.addItem("y")
        self.addItem("x")
        axis = self.cv_source.from_current_cv("axis")
        self.setCurrentText((lambda : "y" if not axis else axis)())
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self):
        return self.currentText()

    def fixup(self):
        t = self.currentText()
        if t != self.last_val:
            self.cv_source.set_in_current_cv("axis", self.currentText())
            self.last_val = t

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("axis"):
            self.setCurrentText(self.cv_source.from_current_cv("axis"))
        else:
            self.setCurrentText("y")



class cvUCatWidget(QComboBox):
    """ Widget for choosing a category for a CV.
    """
    def __init__(self, cv_source: cvSource) -> None:
        super().__init__()
        self.cv_source = cv_source
        self.cats = unicode_cat_names.values()
        self.addItem("None")
        for c in self.cats:
            self.addItem(c)
        ct = "None"
        if self.cv_source.has_key("cat"):
            ct = unicode_cat_names[self.cv_source.from_current_cv("cat")]
        self.setCurrentText(ct)
        self.currentTextChanged.connect(self.text_changed)
        self.last_val = self.currentText()

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if new_text != self.last_val:
            if not new_text or new_text == "None":
                self.cv_source.del_key("cat")
            else:
                self.cv_source.set_in_current_cv("cat", reverse_unicode_cat_names[new_text])
            self.last_val = new_text

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("cat"):
            self.setCurrentText(unicode_cat_names[self.cv_source.from_current_cv("cat")])
        else:
            self.setCurrentText("None")



class cvSuffixWidget(QLineEdit):
    """ Widget for specifying a suffix (the CV is only available or glyphs with
        this suffix).
    """
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda : "None" if not suff else suff)())
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = self.text()

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        if self.dirty:
            self.cv_source.set_in_current_cv("suffix", self._text())
            self.set_clean()

    def text_changed(self):
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source):
        self.cv_source = cv_source
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda : "None" if not suff else suff)())
        self.set_clean()



class cvVarWidget(QLineEdit):
    """ Widget for editing variant CVs for the cvar table.
    """
    def __init__(self, var_id: str, cv_source: cvSource) -> None:
        super().__init__()
        self.var_id = var_id
        self.cv_source = cv_source
        self.dirty = False
        v = self.cv_source.from_current_cv("var")
        k = "None"
        if v and self.var_id in v:
            k = v[self.var_id]
        self.setText(str(k))
        self.setValidator(QIntValidator(-9999, 9999))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = str(k)

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        """ The behavior we want is this: if the widget is blank,
            delete the value for this master and display "None"
            in the widget. If widget has a valid integer, plug
            that in.
        """
        if self.dirty:
            new_text = self._text()
            current_vars = self.cv_source.from_current_cv("var")
            if not current_vars:
                current_vars = {}
            if new_text:
                current_vars[self.var_id] = int(new_text)
                self.cv_source.set_in_current_cv("var", current_vars)
            else:
                if len(current_vars) == 0:
                    self.cv_source.del_key("var")
                    self.refresh()
            self.set_clean()

    def text_changed(self):
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source):
        self.cv_source = cv_source
        v = self.cv_source.from_current_cv("var")
        k = "None"
        if v and self.var_id in v:
            k = v[self.var_id]
        self.setText(str(k))
        self.set_clean()



class cvValueWidget(QLineEdit):
    """ Widget for editing the value of a CV.
    """
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        self.setText(str(self.cv_source.from_current_cv("val")))
        self.setValidator(QIntValidator(-9999, 9999))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = self.text()

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        t = self._text()
        if t != self.last_val:
            try:
                i = int(t)
            except ValueError:
                i = 0
            self.cv_source.set_in_current_cv("val", i, fallback = 0)
            self.set_clean()
    
    def text_changed(self):
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source):
        self.cv_source = cv_source
        i = self.cv_source.from_current_cv("val")
        self.setText((lambda : "0" if not i else str(i))())
        self.set_clean()



class cvPPEMWidget(QLineEdit):
    """ Widget for editing a "ppem" value in the "same as" pane.
    """
    def __init__(self, cv_source: cvSource, above_below: str):
        super().__init__()
        self.cv_source = cv_source
        self.above_below = above_below
        self.name_widget = None
        self.dirty = False
        s = self.cv_source.from_current_cv("same-as")
        v = "40"
        if s:
            try:
                self.setText(s[self.above_below])
            except Exception:
                self.setText("40")
        self.setValidator(QIntValidator(0, 500))
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = "40"

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        new_name = self.name_widget._text()
        name_valid = new_name != "None"
        try:
            new_val = int(self._text())
        except Exception:
            new_val = 40
            self.setText(str(new_val))
        if name_valid:
            s = self.cv_source.from_current_cv("same-as")
            if not s:
                s = {self.above_below: {}}
            s[self.above_below]["cv"] = new_name
            s[self.above_below]["ppem"] = new_val
            self.cv_source.set_in_current_cv("same-as", s)
        else:
            if self.cv_source.has_key("same-as"):
                s = self.cv_source.from_current_cv("same-as")
                if self.above_below in s:
                    del s[self.above_below]
                if len(s) == 0:
                    self.cv_source.del_key("same-as")
        self.set_clean()

    def text_changed(self):
        t = self._text()
        if t != self.last_val:
            self.fixup()
            self.last_val = t

    def refresh(self, cv_source):
        self.cv_source = cv_source
        p = "40"
        s = self.cv_source.from_current_cv("same-as")
        if s and self.above_below in s:
            p = str(s[self.above_below]["ppem"])
        self.setText(p)
        self.set_clean()



class cvNamesWidget(QComboBox):
    """ Widget for choosing a CV name in the "same as" pane.
    """
    def __init__(self, cv_source: cvSource, above_below, yg_font, ppem_widget=None):
        super().__init__()
        self.cv_source = cv_source
        self.yg_font = yg_font
        self.cvt = yg_font.cvt
        self.above_below = above_below
        self.ppem_widget = ppem_widget
        cv_list = self.cvt.get_list(None)
        self.addItem("None")
        for c in cv_list:
            self.addItem(c)
        n = "None"
        cv = self.cv_source.from_current_cv("same-as")
        if cv and self.above_below in cv:
            n = cv[self.above_below]["cv"]
        self.setCurrentText(n)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        if self.ppem_widget:
            self.ppem_widget.fixup()

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        n = "None"
        if self.cv_source.has_key("same-as"):
            s = self.cv_source.from_current_cv("same-as")
            if self.above_below in s:
                n = s[self.above_below]["cv"]
        self.setCurrentText(n)



class masterNameWidget(QLineEdit):
    """ Widget for editing the name of a master. This name is for
        display only: the master is referenced by an immutable id.
    """
    def __init__(self, masters: ygMasters, m_id: str):
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        master_name = self.masters.get_master_name(self.m_id)
        self.setText(master_name)
        self.dirty = False
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = master_name

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def refresh(self, m):
        """ refresh is for updating editing widgets from the model.
        """
        self.m_id = m[0]
        self.setText(self.masters.get_master_name(self.m_id))
        self.set_clean()

    def fixup(self):
        """ fixup is for changing the model based on what's in the editing
            widgets.
        """
        self.masters.set_master_name(self.m_id, self._text())
        self.set_clean()

    def text_changed(self):
        t = self._text()
        if self.dirty and t != self.last_val:
            self.fixup()
            self.last_val = t



class masterValWidget(QLineEdit):
    """ Widget for editing the value of a master (-1.0 to 1.0)
    """
    def __init__(self, masters: ygMasters, m_id: str, axis):
        super().__init__()
        self.masters = masters
        self.m_id = m_id
        self.axis = axis
        self.init_val = self.masters.get_axis_value(self.m_id, self.axis)
        if self.init_val == None:
            self.init_val = 0.0
        self.setText(str(self.init_val))
        self.setValidator(QDoubleValidator(-1.0, 1.0, 4))
        self.dirty = False
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)
        self.last_val = str(self.init_val)

    def _text(self):
        return self.text().strip()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def refresh(self, m):
        """ refresh is for updating editing widgets from the model.
        """
        if m:
            self.m_id = m[0]
        self.setText(str(self.masters.get_axis_value(self.m_id, self.axis)))
        self.set_clean()

    def fixup(self):
        """ fixup is for changing the model based on what's in the editing
            widgets.
        """
        try:
            v = self._text()
            if v == "" or v == "0.0":
                self.masters.del_axis(self.m_id, self.axis)
            else:
                try:
                    self.masters.set_axis_value(self.m_id, self.axis, float(v))
                except Exception:
                    self.masters.set_axis_value(self.m_id, self.axis, 0.0)
                self.refresh(None)
            self.set_clean()
        except Exception as e:
            print(e)
            pass

    def text_changed(self):
        t = self._text()
        if self.dirty and t != self.last_val:
            self.fixup()
            self.last_val = t
