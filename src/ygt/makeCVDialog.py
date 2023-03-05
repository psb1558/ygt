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
                             QPushButton)
from PyQt6.QtCore import Qt
from .ygModel import unicode_categories, unicode_cat_names, reverse_unicode_cat_names
from .ygYAMLEditor import editorPane
from .ygSchema import is_cvt_valid

NEW_CV_NAME = "New_Control_Value"

# The problem in this file is keeping model and view in sync when individual widgets
# have got their own pointers to CVs. Instead, give them a pointer to an ancestor
# object that has access functions for the things they need (chiefly the current CV).
#
# Here is the structure of the CVT edit window (that for mastersWidget is projected):
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
    def __init__(self, yg_font, preferences):
        super().__init__()
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
        # self.layout.addWidget(self.cv_list)
        self.layout.addLayout(self.cv_list_layout)
        self.layout.addWidget(self.edit_pane)
        self.setLayout(self.layout)

    def add_cv(self):
        self._current_cv_name = NEW_CV_NAME
        self._cvt.add_cv(self._current_cv_name, {"val": 0, "axis": "y", "type": "pos"})
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
        self._current_cv = self._cvt.get_cv(self._current_cv_name)
        self.cv_list.clear()
        print(list(self._cvt.keys()))
        self.cv_list.addItems(self._cvt.keys())
        matches = self.cv_list.findItems(self._current_cv_name, Qt.MatchFlag.MatchExactly)
        if len(matches) > 0:
            self.cv_list.setCurrentItem(matches[0])
        else:
            current_item = self.cv_list.item(0)
            self.cv_list.setCurrentItem(current_item)
            self._current_cv_name = current_item.text()
            self._current_cv = self._cvt.get_cv(self._current_cv_name)
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
                self._current_cv[k] = fallback
            else:
                if k in self._current_cv:
                    del self._current_cv[k]
        else:
            self._current_cv[k] = s

    def has_key(self, k: str) -> bool:
        return k in self._current_cv

    def del_key(self, k: str):
        try:
            del self._current_cv[k]
        except KeyError:
            pass

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
        self.cv_tab = cvEditPane(self.yg_font, self.preferences)
        self.source_tab = editorPane(self, self.cvt, is_cvt_valid, save_on_focus_out=True)
        self.masters_tab = mastersWidget(self.yg_font)
        self.tabs.addTab(self.cv_tab, "Control Values")
        self.tabs.addTab(self.source_tab, "Source")
        if self.yg_font.is_variable_font:
            self.tabs.addTab(self.masters_tab, "Masters")
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        self.window().setWindowTitle("Control Values")

    def closeEvent(self, event):
        self.hide()



class mastersWidget(QWidget):
    def __init__(self, yg_font):
        super().__init__()
        self.masters = yg_font.masters
        self.master_source = []
        m_keys = self.masters.keys()
        for m in m_keys:
            self.master_source.append((m, self.masters.master(m)))

        self.master_widgets = []

        for mm in self.master_source:
            self.master_widgets.append(QHBoxLayout())
            self.master_widgets[-1].addWidget(QLabel(mm[0]))
            self.master_widgets[-1].addWidget(QLabel(mm[1]["name"]))
            self.master_widgets[-1].addWidget(QLabel(str(mm[1]["val"])))

        self.layout = QVBoxLayout()
        for mmm in self.master_widgets:
            self.layout.addLayout(mmm)

        self.setLayout(self.layout)



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

    def __init__(self, cv_source: cvSource, yg_font, owner, parent=None):
        super().__init__(parent=parent)
        self.yg_font = yg_font
        self.owner = owner
        self.cv_source = cv_source
        self.layout = QVBoxLayout()

        # Set up tabs

        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.link_tab = QWidget()
        self.variants_tab = None
        self.masters = None
        if self.yg_font.is_variable_font:
            self.variants_tab = QWidget()
            self.masters = self.yg_font.masters
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.link_tab, "Same As")
        if self.masters:
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
        self.gen_widgets[-1].addWidget(QLabel("color"))
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

        # Set up variants tab

        self.variants_tab_layout = None
        if self.masters:
            self.variants_tab_layout = QVBoxLayout()
            self.var_widgets = []
            self.var_layouts = []
            master_keys = self.masters.keys()
            for k in master_keys:
                self.var_layouts.append(QHBoxLayout())
                master = self.masters.master(k)
                self.var_layouts[-1].addWidget(QLabel(master["name"]))
                self.var_widgets.append(cvVarWidget(k, self.cv_source))
                self.var_layouts[-1].addWidget(self.var_widgets[-1])

        for w in self.gen_widgets:
            self.general_tab_layout.addLayout(w)
        for w in self.link_widgets:
            self.link_tab_layout.addLayout(w)
        if self.masters:
            for w in self.var_layouts:
                self.variants_tab_layout.addLayout(w)

        self.general_tab.setLayout(self.general_tab_layout)
        self.link_tab.setLayout(self.link_tab_layout)
        if self.masters:
            self.variants_tab.setLayout(self.variants_tab_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

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
    def __init__(self, p1, p2, yg_font, preferences):
        super().__init__()
        self.top_window = preferences.top_window()
        self.yg_font = yg_font
        self._cvt = self.yg_font.cvt
        self.cv = {}
        self.cv_name = ""
        self.axis = preferences.top_window().current_axis
        self.cv["axis"] = self.axis
        if p2 != None:
            init_type = "dist"
        else:
            init_type = "pos"
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

        self.layout = QVBoxLayout()

        self.pane = cvWidget(self, self.yg_font)

        # Set up buttons

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout.addWidget(self.pane)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

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
        if self.cv_name and len(self.cv) > 0:
            self._cvt.add_cv(name=self.cv_name, props=self.cv)
        super().accept()


class cvNameWidget(QLineEdit):
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

    def _text(self):
        return self.text()
    
    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        if self.isEnabled() and self.dirty:
            # If the cv name changes, the original cv in the source tree
            # has to be deleted and a new cv entered under the new name.
            # We can either do that (at some risk of bugginess) or disable
            # the cv name widget when the cv is being edited (as opposed
            # to created).
            new_name = self.text()
            old_name = self.cv_source.current_cv_name()
            self.cv_source.set_cv_name(new_name)
            if self.owner != None:
                self.owner.change_name_in_list(new_name)
                self.owner.rename_cv(old_name, new_name)
            self.set_clean()

    def text_changed(self):
        if self.dirty:
            self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.isEnabled():
            self.setText(self.cv_source.current_cv_name())
            self.set_clean()



class cvTypeWidget(QComboBox):
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.addItem("pos")
        self.addItem("dist")
        t = self.cv_source.from_current_cv("type")
        self.setCurrentText((lambda : "y" if not t else t)())
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        self.cv_source.set_in_current_cv("type", self.currentText())

    def text_changed(self, event):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        self.setCurrentText(self.cv_source.from_current_cv("type"))



class cvColorWidget(QComboBox):
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

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if self.cv_source.current_cv():
            if new_text != "None":
                self.cv_source.set_in_current_cv("col", new_text)
            else:
                self.cv_source.del_key("col")

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("col"):
            self.setCurrentText(self.cv_source.from_current_cv("col"))
        else:
            self.setCurrentText("None")



class cvAxisWidget(QComboBox):
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.addItem("y")
        self.addItem("x")
        axis = self.cv_source.from_current_cv("axis")
        self.setCurrentText((lambda : "None" if not axis else axis)())
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        self.cv_source.set_in_current_cv("axis", self.currentText())

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("axis"):
            self.setCurrentText(self.cv_source.from_current_cv("axis"))
        else:
            self.setCurrentText("None")



class cvUCatWidget(QComboBox):
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

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if not new_text or new_text == "None":
            self.cv_source.del_key("cat")
        else:
            self.cv_source.set_in_current_cv("cat", reverse_unicode_cat_names[new_text])

    def text_changed(self, s):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        if self.cv_source.has_key("cat"):
            self.setCurrentText(unicode_cat_names[self.cv_source.from_current_cv("cat")])
        else:
            self.setCurrentText("None")



class cvSuffixWidget(QLineEdit):
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda : "None" if not suff else suff)())
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)

    def _text(self):
        return self.text()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        if self.dirty:
            self.cv_source.set_in_current_cv("suffix", self.text())
            self.set_clean()

    def text_changed(self):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        suff = self.cv_source.from_current_cv("suffix")
        self.setText((lambda : "None" if not suff else suff)())
        self.set_clean()



class cvVarWidget(QLineEdit):
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
        self.setInputMask("9000")
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)

    def _text(self):
        return self.text()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        if self.dirty:
            new_text = self.text()
            current_vars = self.cv_source.from_current_cv("var")
            if not current_vars:
                current_vars = {}
            if new_text:
                current_vars[self.var_id] = int(new_text)
                self.cv_source.set_in_current_cv("var", current_vars)
            else:
                if len(current_vars) == 0:
                    self.cv_source.del_key("var")
            self.set_clean()

    def text_changed(self):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        v = self.cv_source.from_current_cv("var")
        k = "None"
        if v and self.var_id in v:
            k = v[self.var_id]
        self.setText(str(k))
        self.set_clean()



class cvValueWidget(QLineEdit):
    def __init__(self, cv_source: cvSource):
        super().__init__()
        self.cv_source = cv_source
        self.dirty = False
        self.setText(str(self.cv_source.from_current_cv("val")))
        self.setInputMask("9000")
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)

    def _text(self):
        return self.text()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        try:
            i = int(self.text())
        except ValueError:
            i = 0
        self.cv_source.set_in_current_cv("val", i, fallback = 0)
        self.set_clean()
    
    def text_changed(self):
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        i = self.cv_source.from_current_cv("val")
        self.setText((lambda : "0" if not i else str(i))())
        self.set_clean()



class cvPPEMWidget(QLineEdit):
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
        self.setInputMask("9000")
        self.editingFinished.connect(self.text_changed)
        self.textChanged.connect(self.set_dirty)

    def _text(self):
        return self.text()

    def set_dirty(self):
        self.dirty = True

    def set_clean(self):
        self.dirty = False

    def fixup(self):
        new_name = self.name_widget._text()
        name_valid = new_name != "None"
        try:
            new_val = int(self.text())
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
        self.fixup()

    def refresh(self, cv_source):
        self.cv_source = cv_source
        p = "40"
        s = self.cv_source.from_current_cv("same-as")
        if s and self.above_below in s:
            p = str(s[self.above_below]["ppem"])
        self.setText(p)
        self.set_clean()



class cvNamesWidget(QComboBox):
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


#class cvOverUnderWidget(QComboBox):
#    def __init__(self):
#        super().__init__()
#        self.addItem("below")
#        self.addItem("above")
#        self.setCurrentText("below")
#
#    def _text(self):
#        return self.currentText()
