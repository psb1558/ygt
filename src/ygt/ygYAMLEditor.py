from PyQt6.QtCore import (pyqtSignal, Qt, pyqtSlot)
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QPlainTextEdit,
                             QDialogButtonBox)
from PyQt6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor)
import yaml
import re
from yaml import Dumper
import copy
from .ygSchema import is_valid, set_error_message, error_message

# From https://stackoverflow.com/questions/8640959/
# how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
# Presumed public domain, since it was posted in a public forum.
def str_presenter(dumper, data):
  if len(data.splitlines()) > 1:  # check for multiline string
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
  return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)

# to use with safe_dump:
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)

class ygYAMLEditor(QPlainTextEdit):

    sig_source_from_editor = pyqtSignal(object)
    sig_status = pyqtSignal(object)

    def __init__(self, preferences, parent=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setStyleSheet("ygYAMLEditor {font-family: Source Code Pro, monospace; }")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preferences = preferences
        self.textChanged.connect(self.text_changed)
        self._highlighter = ygGlyphHighlighter()
        self.setup_editor()

    @pyqtSlot(object)
    def install_source(self, text):
        self.setPlainText(text)

    @pyqtSlot()
    def yaml_source(self):
        err = False
        try:
            s = yaml.safe_load(self.toPlainText())
        except Exception as e:
            err = True
        if not err:
            try:
                err = not is_valid({"points": s})
            except SchemaError:
                err = True
        if err:
            self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])
        else:
            self.sig_source_from_editor.emit(s)

    def setup_status_indicator(self, o):
        self.sig_status.connect(o)

    def setup_editor_signals(self, f):
        self.sig_source_from_editor.connect(f)

    def disconnect_editor_signals(self, f):
        self.sig_source_from_editor.disconnect(f)

    @pyqtSlot()
    def text_changed(self):
        valid = True
        y = self.toPlainText()
        if len(y) == 0:
            self.setPlainText("[]\n")
        else:
            try:
                y = yaml.safe_load(y)
            except Exception as e:
                valid = False
            if valid:
                valid = is_valid({"points": y})
            if valid:
                set_error_message(None)
            else:
                if not error_message():
                    set_error_message("error")
        self.sig_status.emit(valid)

    def setup_editor(self):
        tags = r'\b(ptid|ref|rel|macro|function|pos|dist|points|round)\:'
        twospace =   r'(  |\- )'
        fourspace =  r'(    |  \- )'
        sixspace =   r'(      |    \- )'
        eightspace = r'(        |      \- )'
        tenspace =   r'(          |        \- )'

        keytwo_format = QTextCharFormat()
        keytwo_format.setForeground(QColor(122,6,70,255))
        pattern = twospace+tags
        self._highlighter.add_mapping(pattern, keytwo_format)

        keyfour_format = QTextCharFormat()
        keyfour_format.setForeground(QColor("blue"))
        pattern = fourspace+tags
        self._highlighter.add_mapping(pattern, keyfour_format)

        keysix_format = QTextCharFormat()
        keysix_format.setForeground(QColor(201,91,12,255))
        pattern = sixspace+tags
        self._highlighter.add_mapping(pattern, keysix_format)

        keyeight_format = QTextCharFormat()
        keyeight_format.setForeground(QColor("green"))
        pattern = eightspace+tags
        self._highlighter.add_mapping(pattern, keyeight_format)

        keyten_format = QTextCharFormat()
        keyten_format.setForeground(QColor("brown"))
        pattern = tenspace+tags
        self._highlighter.add_mapping(pattern, keyten_format)

        list_format = QTextCharFormat()
        list_format.setForeground(QColor("red"))
        pattern = r'^(\- |  \- |    \- |      \- |        \- |          \- )'
        self._highlighter.add_mapping(pattern, list_format)

        self._highlighter.setDocument(self.document())



class editorDialog(QDialog):
    def __init__(self, preferences, sourceable, title, validator, top_structure="dict"):
        super().__init__()
        self.title = title
        self.set_dialog_title(self.title, True)
        self.is_valid = validator
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.preferences = preferences
        self.sourceable = sourceable
        if top_structure == "dict":
            self._empty_string = "{}\n"
        else:
            self._empty_string = "[]\n"
        self.setMinimumSize(500, 500)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.edit_pane = QPlainTextEdit()
        self.edit_pane.textChanged.connect(self.text_changed)
        self.edit_pane.setStyleSheet("QPlainTextEdit {font-family: Source Code Pro, monospace; }")
        self.install_yaml(copy.copy(self.sourceable.source()))
        self.layout.addWidget(self.edit_pane)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        self.watching_for_changes = False

    def install_text(self, text):
        self.edit_pane.setPlainText(text)
        self.watching_for_changes = True

    def install_yaml(self, y):
        try:
            t = yaml.dump(y, sort_keys=False, Dumper=Dumper)
        except Exception as e:
            print(e)
            t = self._empty_string
        self.install_text(t)

    def yaml_source(self):
        try:
            return(yaml.safe_load(self.edit_pane.toPlainText()))
        except Exception as e:
            self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])

    def set_dialog_title(self, t, is_valid):
        v  = " (Invalid)"
        if is_valid:
            v = " (Valid)"
        self.setWindowTitle(t + v)

    def text_changed(self):
        self.sourceable.set_clean(False)
        if len(self.edit_pane.toPlainText()) == 0:
            self.edit_pane.setPlainText(self._empty_string)
        try:
            v = self.is_valid(yaml.safe_load(self.edit_pane.toPlainText()))
        except Exception as e:
            print("Error on load:")
            print(e)
            v = False
        self.set_dialog_title(self.title, v)

    def reject(self):
        self.done(QDialog.DialogCode.Rejected)

    def accept(self):
        err = False
        c = self.yaml_source()
        if c != None:
            if self.is_valid(c):
                self.sourceable.save(c)
            else:
                err = True
        else:
            err = True
        if err:
            print("Couldn't save the Sourceable")
            self.reject()
            return
        self.done(QDialog.DialogCode.Accepted)
        # super().accept()



class ygGlyphHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        QSyntaxHighlighter.__init__(self, parent)
        self._mappings = {}

    def add_mapping(self, pattern, format):
        self._mappings[pattern] = format

    def highlightBlock(self, text):
        for pattern, format in self._mappings.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                s = match.group(0)
                start = match.start()
                end = match.end()
                self.setFormat(start, end - start, format)
