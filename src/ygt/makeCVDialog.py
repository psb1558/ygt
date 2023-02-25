import copy
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QComboBox,
                             QLineEdit,
                             QLabel,
                             QWidget,
                             QTabWidget)
from PyQt6.QtCore import pyqtSignal
from .ygModel import unicode_categories, unicode_cat_names

class cvtWindow(QDialog):
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
    def __init__(self):
        pass

class cvWidget(QWidget):
    """ Superclass for CV making and editing dialogs. The "accept" method
        will take care of inserting the new or edited cv into the cvt.

        params:

        cv_name (str): The current name (if any) of the cv

        cv (dict): The kind of dict ygt stores cv info in. Can contain
        initial values or values of the cv being edited.

        cvt (dict): This font's cvt.

        preferences (ygPreferences): provides reference to this font's
        top_window.

        title (str): Title for this dialog box.
    """

    def __init__(self, cv_name, cv, cvt, preferences, parent=None):
        super().__init__(parent=parent)
        self.top_window = preferences.top_window()
        self.cv = cv
        self.original_cv_name = self.cv_name = cv_name
        self.cvt = cvt
        self.layout = QVBoxLayout()

        # Set up tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.link_tab = QWidget()
        self.variants_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.link_tab, "Same As")
        # self.tabs.addTab(self.variants_tab, "Variants")

        # set up general tab
        self.general_tab_layout = QVBoxLayout()
        cv_type_widget = cvTypeWidget(self.cv["type"])
        col = "None"
        if "col" in self.cv:
            col = self.cv["col"]
        cv_color_widget = cvColorWidget(col, cv=self.cv)
        cv_axis_widget = cvAxisWidget(self.cv["axis"], cv=self.cv)
        cv_val_widget = cvValueWidget(self.cv["val"], cv=self.cv)
        cv_name_widget = cvNameWidget(cv_name=self.cv_name, owner=self)
        cat = "None"
        if "cat" in self.cv:
            cat = self.cv["cat"]
        cv_cat_widget = cvUCatWidget(cat = cat, cv = self.cv)
        suff = "None"
        if "suffix" in self.cv:
            suff = self.cv["suffix"]
        cv_suffix_widget = cvSuffixWidget(suffix = suff, cv=self.cv)

        self.gen_widgets = []

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("name"))
        self.gen_widgets[-1].addWidget(cv_name_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("val"))
        self.gen_widgets[-1].addWidget(cv_val_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("type"))
        self.gen_widgets[-1].addWidget(cv_type_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("axis"))
        self.gen_widgets[-1].addWidget(cv_axis_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("cat"))
        self.gen_widgets[-1].addWidget(cv_cat_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("suffix"))
        self.gen_widgets[-1].addWidget(cv_suffix_widget)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("color"))
        self.gen_widgets[-1].addWidget(cv_color_widget)

        # Set up link tab

        self.link_tab_layout = QVBoxLayout()

        same_as_above_cv = same_as_below_cv = "None" 
        same_as_above_ppem = same_as_below_ppem = 40
        if "same-as" in self.cv:
            if "above" in self.cv["same-as"]:
                same_as_above_cv = self.cv["same-as"]["above"]["cv"]
                same_as_above_ppem = self.cv["same-as"]["above"]["ppem"]
            if "below" in self.cv["same-as"]:
                same_as_below_cv = self.cv["same-as"]["below"]["cv"]
                same_as_below_ppem = self.cv["same-as"]["below"]["ppem"]

        self.cv_below_ppem_widget = cvPPEMWidget(same_as_below_ppem, "below", cv=self.cv)
        self.cv_above_ppem_widget = cvPPEMWidget(same_as_above_ppem, "above", cv=self.cv)
        cv_below_names_widget = cvNamesWidget(self.cvt,
                                                   init_name = same_as_below_cv,
                                                   ppem_widget=self.cv_below_ppem_widget,
                                                   cv=self.cv)
        cv_above_names_widget = cvNamesWidget(self.cvt,
                                                   init_name = same_as_above_cv,
                                                   ppem_widget=self.cv_above_ppem_widget,
                                                   cv=self.cv)
        self.cv_below_ppem_widget.name_widget = cv_below_names_widget
        self.cv_above_ppem_widget.name_widget = cv_above_names_widget

        self.link_widgets = []

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(cv_below_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("below"))
        self.link_widgets[-1].addWidget(self.cv_below_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("and"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(cv_above_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("above"))
        self.link_widgets[-1].addWidget(self.cv_above_ppem_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        for w in self.gen_widgets:
            self.general_tab_layout.addLayout(w)
        for w in self.link_widgets:
            self.link_tab_layout.addLayout(w)

        self.general_tab.setLayout(self.general_tab_layout)
        self.link_tab.setLayout(self.link_tab_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.setWindowTitle("Make Control Value")



class makeCVDialog(QDialog):
    def __init__(self, p1, p2, cvt, preferences):
        super().__init__()
        self.top_window = preferences.top_window()
        self.cvt = cvt
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

        self.pane = cvWidget("", self.cv, self.cvt, preferences)

        # Set up buttons
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout.addWidget(self.pane)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def accept(self):
        if self.pane.cv_name and len(self.cv) > 0:
            self.cvt.add_cv(name=self.pane.cv_name, props=self.cv)
        super().accept()



class cvNameWidget(QLineEdit):
    def __init__(self, cv_name: str = "", owner=None):
        super().__init__()
        self.owner = owner
        self.cv_name = cv_name
        if len(self.cv_name) > 0:
            self.setText(self.cv_name)
            self.setEnabled(False)
        else:
            self.editingFinished.connect(self.text_changed)

    def _text(self):
        return self.text()

    def fixup(self):
        if self.owner:
            # If the cv name changes, the original cv in the source tree
            # has to be deleted and a new cv entered under the new name.
            # We can either do that (at some risk of bugginess) or disable
            # the cv name widget when the cv is being edited (as opposed
            # to created).
            self.owner.cv_name = self.text()

    def text_changed(self):
        self.fixup()



class cvTypeWidget(QComboBox):
    def __init__(self, init_type, cv=None):
        super().__init__()
        self.type = init_type
        self.addItem("pos")
        self.addItem("dist")
        self.setCurrentText(init_type)
        self.cv = cv
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        if self.cv:
            self.cv["type"] = self.currentText()

    def text_changed(self, event):
        self.fixup()



class cvColorWidget(QComboBox):
    def __init__(self, init_color, cv=None):
        super().__init__()
        self.cv = cv
        self.addItem("None")
        self.addItem("black")
        self.addItem("white")
        self.addItem("gray")
        self.setCurrentText(init_color)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if self.cv:
            if new_text != "None":
                self.cv["col"] = new_text
            else:
                if "col" in self.cv:
                    del self.cv["col"]

    def text_changed(self, s):
        self.fixup()



class cvAxisWidget(QComboBox):
    def __init__(self, init_axis, cv=None):
        super().__init__()
        self.cv = cv
        self.addItem("y")
        self.addItem("x")
        self.setCurrentText(init_axis)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        if self.cv:
            self.cv["axis"] = self.currentText()

    def text_changed(self, s):
        self.fixup()



class cvUCatWidget(QComboBox):
    def __init__(self, cat: str = "None", cv=None) -> None:
        super().__init__()
        self.cv = cv
        self.cats = unicode_cat_names.values()
        self.addItem(cat)
        for c in self.cats:
            self.addItem(c)
        self.setCurrentText(cat)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        new_text = self.currentText()
        if self.cv:
            if new_text != "None":
                rev_unic_dict = {v: k for k, v in unicode_cat_names.items()}
                try:
                    self.cv["cat"] = rev_unic_dict[new_text]
                except KeyError:
                    if "cat" in self.cv:
                        del self.cv["cat"]
            else:
                if "cat" in self.cv:
                    del self.cv["cat"]

    def text_changed(self, s):
        self.fixup()



class cvSuffixWidget(QLineEdit):
    def __init__(self, suffix: str = "None", cv=None):
        super().__init__()
        self.cv = cv
        self.setText(suffix)
        self.editingFinished.connect(self.text_changed)

    def _text(self):
        return self.text()

    def fixup(self):
        if self.cv:
            new_text = self.text()
            if new_text != "None":
                self.cv["suffix"] = new_text
            else:
                if "suffix" in self.cv:
                    del self.cv["suffix"]

    def text_changed(self):
        self.fixup()



class cvValueWidget(QLineEdit):
    def __init__(self, init_value, cv=None):
        super().__init__()
        self.cv = cv
        self.setText(str(init_value))
        self.editingFinished.connect(self.text_changed)

    def _text(self):
        return self.text()

    def fixup(self):
        if self.cv:
            new_text = self.text()
            if len(new_text) > 0:
                try:
                    self.cv["val"] = int(new_text)
                except Exception:
                    self.cv["val"] = 0
            else:
                self.cv["val"] = 0
    
    def text_changed(self):
        self.fixup()



class cvPPEMWidget(QLineEdit):
    def __init__(self, init_value, above_below, cv=None):
        super().__init__()
        self.cv = cv
        self.setText(str(init_value))
        self.name_widget = None
        self.above_below = above_below
        self.editingFinished.connect(self.text_changed)

    def _text(self):
        return self.text()

    def fixup(self):
        new_name = self.name_widget._text()
        name_valid = new_name != "None"
        try:
            new_val = int(self.text())
        except Exception:
            new_val = 40
            self.setText(str(new_val))
        if name_valid:
            if not "same-as" in self.cv:
                self.cv["same-as"] = {}
            if not self.above_below in self.cv["same-as"]:
                self.cv["same-as"][self.above_below] = {}
            self.cv["same-as"][self.above_below]["ppem"] = new_val
            self.cv["same-as"][self.above_below]["cv"] = new_name
        else:
            if "same-as" in self.cv:
                if self.above_below in self.cv["same-as"]:
                    del self.cv["same-as"][self.above_below]
                if len(self.cv["same-as"]) == 0:
                    del self.cv["same-as"]

    def text_changed(self):
        self.fixup()



class cvNamesWidget(QComboBox):
    def __init__(self, cvt, init_name: str = "None", ppem_widget=None, cv=None):
        super().__init__()
        self.cv = cv
        self.ppem_widget = ppem_widget
        cv_list = cvt.get_list(None)
        self.addItem("None")
        for c in cv_list:
            self.addItem(c)
        self.setCurrentText(init_name)
        self.currentTextChanged.connect(self.text_changed)

    def _text(self):
        return self.currentText()

    def fixup(self):
        self.ppem_widget.fixup()

    def text_changed(self, s):
        self.fixup()



#class cvOverUnderWidget(QComboBox):
#    def __init__(self):
#        super().__init__()
#        self.addItem("below")
#        self.addItem("above")
#        self.setCurrentText("below")
#
#    def _text(self):
#        return self.currentText()
