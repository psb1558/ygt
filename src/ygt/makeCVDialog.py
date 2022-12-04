from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QComboBox,
                             QLineEdit,
                             QLabel)
from .ygModel import unicode_categories, unicode_cat_names

class makeCVDialog(QDialog):
    def __init__(self, p1, p2, cvt, preferences):
        self.top_window = preferences["top_window"]
        self.cvt = cvt
        self.axis = preferences["current_axis"]
        super(makeCVDialog,self).__init__(self.top_window)
        self.setWindowTitle("Make Control Value")
        self.layout = QVBoxLayout()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
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

        self.widgets = []

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("name"))
        self.widgets[-1].addWidget(cv_name)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("val"))
        self.widgets[-1].addWidget(cv_val)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("type"))
        self.widgets[-1].addWidget(cv_type)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("axis"))
        self.widgets[-1].addWidget(cv_axis)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("cat"))
        self.widgets[-1].addWidget(cv_cat)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("suffix"))
        self.widgets[-1].addWidget(cv_suffix)

        self.widgets.append(QHBoxLayout())
        self.widgets[-1].addWidget(QLabel("color"))
        self.widgets[-1].addWidget(cv_color)

        for w in self.widgets:
            self.layout.addLayout(w)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def accept(self):
        new_cv_vals = {}
        cv_name = None
        for w in self.widgets:
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
