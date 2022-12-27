from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QComboBox,
                             QLineEdit,
                             QLabel,
                             QWidget,
                             QTabWidget)
from .ygModel import unicode_categories, unicode_cat_names

class makeCVDialog(QDialog):
    def __init__(self, p1, p2, cvt, preferences):
        self.top_window = preferences.top_window()
        self.cvt = cvt
        self.axis = preferences.top_window().current_axis
        super(makeCVDialog,self).__init__(self.top_window)
        self.setWindowTitle("Make Control Value")
        self.layout = QVBoxLayout()

        # Set up tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.link_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.link_tab, "Same As")

        # Set up buttons
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # set up general tab
        self.general_tab_layout = QVBoxLayout()
        if p2 != None:
            init_type = "dist"
        else:
            init_type = "pos"
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
        color = "None"
        cv_type = cvTypeWidget(init_type)
        cv_color = cvColorWidget(color)
        cv_axis = cvAxisWidget(self.axis)
        cv_val = cvValueWidget(val)
        cv_name = cvNameWidget()
        cv_cat = cvUCatWidget()
        cv_suffix = cvSuffixWidget()

        self.gen_widgets = []

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("name"))
        self.gen_widgets[-1].addWidget(cv_name)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("val"))
        self.gen_widgets[-1].addWidget(cv_val)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("type"))
        self.gen_widgets[-1].addWidget(cv_type)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("axis"))
        self.gen_widgets[-1].addWidget(cv_axis)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("cat"))
        self.gen_widgets[-1].addWidget(cv_cat)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("suffix"))
        self.gen_widgets[-1].addWidget(cv_suffix)

        self.gen_widgets.append(QHBoxLayout())
        self.gen_widgets[-1].addWidget(QLabel("color"))
        self.gen_widgets[-1].addWidget(cv_color)

        # Set up link tab

        self.link_tab_layout = QVBoxLayout()

        cv_below_names_widget = cvNamesWidget(cvt)
        cv_above_names_widget = cvNamesWidget(cvt)
        # cv_over_under_widget = cvOverUnderWidget()
        self.cv_below_val_widget = cvValueWidget(40)
        self.cv_above_val_widget = cvValueWidget(40)

        self.link_widgets = []

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(cv_below_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("below"))
        self.link_widgets[-1].addWidget(self.cv_below_val_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("and"))

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("same as"))
        self.link_widgets[-1].addWidget(cv_above_names_widget)

        self.link_widgets.append(QHBoxLayout())
        self.link_widgets[-1].addWidget(QLabel("above"))
        self.link_widgets[-1].addWidget(self.cv_above_val_widget)
        self.link_widgets[-1].addWidget(QLabel("ppem"))

        for w in self.gen_widgets:
            self.general_tab_layout.addLayout(w)
        for w in self.link_widgets:
            self.link_tab_layout.addLayout(w)

        self.general_tab.setLayout(self.general_tab_layout)
        self.link_tab.setLayout(self.link_tab_layout)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def accept(self):
        new_cv_vals = {}
        cv_name = None
        for w in self.gen_widgets:
            val_name = w.itemAt(0).widget().text()
            if val_name != "name":
                val = w.itemAt(1).widget()._text()
                if val_name == "val":
                    try:
                        val = int(val)
                    except Exception as e:
                        val = 0
                if val_name == "cat" and val != None:
                    rev_unic_dict = {v: k for k, v in unicode_cat_names.items()}
                    try:
                        val = rev_unic_dict[val]
                    except KeyError:
                        val = "None"
                if val != "None":
                    new_cv_vals[val_name] = val
            else:
                cv_name = w.itemAt(1).widget()._text()
                if cv_name == None or len(cv_name) == 0:
                    cv_name = "new-control-value"
        same_as = {}
        for i, w in enumerate(self.link_widgets):
            if i == 0:
                print(type(w.itemAt(1).widget()))
                cv_below_name = w.itemAt(1).widget()._text()
            elif i == 1:
                try:
                    cv_below_ppem = int(w.itemAt(1).widget()._text())
                except Exception:
                    cv_below_ppem = 40
            elif i == 3:
                cv_above_name = w.itemAt(1).widget()._text()
            elif i == 4:
                try:
                    cv_above_ppem = int(w.itemAt(1).widget()._text())
                except Exception:
                    cv_above_ppem = 40
        if cv_below_name != "None":
            same_as["below"] = {"cv": cv_below_name, "ppem": cv_below_ppem}
        if cv_above_name != "None":
            same_as["above"] = {"cv": cv_above_name, "ppem": cv_above_ppem}
        if len(same_as) > 0:
            new_cv_vals["same-as"] = same_as
        self.cvt.add_cv(cv_name, new_cv_vals)
        super().accept()



class cvNameWidget(QLineEdit):
    def __init__(self):
        super().__init__()

    def _text(self):
        return self.text()



class cvTypeWidget(QComboBox):
    def __init__(self, init_type):
        super().__init__()
        self.type = init_type
        self.addItem("pos")
        self.addItem("dist")
        self.setCurrentText(init_type)

    def _text(self):
        return self.currentText()



class cvColorWidget(QComboBox):
    def __init__(self, init_color):
        super().__init__()
        self.addItem("None")
        self.addItem("black")
        self.addItem("white")
        self.addItem("gray")
        self.setCurrentText(init_color)

    def _text(self):
        return self.currentText()



class cvAxisWidget(QComboBox):
    def __init__(self, init_axis):
        super().__init__()
        self.addItem("y")
        self.addItem("x")
        self.setCurrentText(init_axis)

    def _text(self):
        return self.currentText()



class cvUCatWidget(QComboBox):
    def __init__(self):
        super().__init__()
        self.cats = unicode_cat_names.values()
        self.addItem("None")
        for c in self.cats:
            self.addItem(c)
        self.setCurrentText("None")

    def _text(self):
        return self.currentText()



class cvSuffixWidget(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setText("None")

    def _text(self):
        return self.text()



class cvValueWidget(QLineEdit):
    def __init__(self, init_value):
        super().__init__()
        self.setText(str(init_value))

    def _text(self):
        return self.text()



class cvNamesWidget(QComboBox):
    def __init__(self, cvt):
        super().__init__()
        cv_list = cvt.get_list(None)
        self.addItem("None")
        for c in cv_list:
            self.addItem(c)
        self.setCurrentText("None")

    def _text(self):
        return self.currentText()



#class cvOverUnderWidget(QComboBox):
#    def __init__(self):
#        super().__init__()
#        self.addItem("below")
#        self.addItem("above")
#        self.setCurrentText("below")
#
#    def _text(self):
#        return self.currentText()
