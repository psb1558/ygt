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
from schema import SchemaError
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
        self.setStyleSheet("ygYAMLEditor {font-family: Source Code Pro, monospace; background-color: white; }")
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
        tags = r'\b(ptid|ref|rel|macro|function|pos|dist|points|round|min)\:'
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



class editorPane(QPlainTextEdit):

    def __init__(self, owner, sourceable, validator, save_on_focus_out=False):
        super().__init__()
        self.save_on_focus_out = save_on_focus_out
        self.owner = owner
        self.textChanged.connect(self.text_changed)
        self.error_state = False
        self.set_style()
        self.watching_for_changes = False
        self.is_valid = validator
        self.sourceable = sourceable
        self.install_yaml(copy.copy(self.sourceable.source()))
        self.dirty = False

    def install_text(self, text):
        self.setPlainText(text)
        self.watching_for_changes = True

    def install_yaml(self, y):
        try:
            t = yaml.dump(y, sort_keys=False, Dumper=Dumper)
        except Exception as e:
            print(e)
            t = self._empty_string
        self.install_text(t)

    def set_style(self):
        if self.error_state:
            self.setStyleSheet("QPlainTextEdit {font-family: Source Code Pro, monospace; background-color: rgb(252,227,242);  }")
        else:
            self.setStyleSheet("QPlainTextEdit {font-family: Source Code Pro, monospace; background-color: white;  }")

    def set_error_state(self, b):
        if self.error_state != b:
            self.error_state = b
            self.set_style()

    def yaml_source(self):
        try:
            t = yaml.safe_load(self.toPlainText())
            self.set_error_state(False)
            return t
        except Exception as e:
            self.set_error_state(True)
            self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])

    def text_changed(self):
        if not self.watching_for_changes:
            return
        self.sourceable.set_clean(False)
        if len(self.toPlainText()) == 0:
            self.setPlainText(self._empty_string)
        v = False
        try:
            v = self.is_valid(yaml.safe_load(self.toPlainText()))
            # self.set_error_state(False)
        except Exception as e:
            # self.set_error_state(True)
            print("Error on load:")
            print(e)
        self.set_error_state(not v)
        self.dirty = True

    def focusOutEvent(self, event):
        if self.save_on_focus_out and self.dirty:
            c = self.yaml_source()
            if c != None:
                if self.is_valid(c):
                    self.sourceable.save(c)
                    self.set_error_state(False)
                else:
                    self.set_error_state(True)
            else:
                self.set_error_state(True)
            if self.error_state:
                self.preferences.top_window().show_error_message(["Warning", "Warning", "YAML source code is invalid."])

    def showEvent(self, event):
        self.install_yaml(copy.copy(self.sourceable.source()))





class editorDialog(QDialog):
    def __init__(self, preferences, sourceable, title, validator, top_structure="dict"):
        super().__init__()
        self.title = title
        self.set_dialog_title(True)
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
        self.edit_pane = editorPane(self, sourceable, validator)
        self.layout.addWidget(self.edit_pane)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def set_dialog_title(self, is_valid):
        v  = " (Invalid)"
        if is_valid:
            v = " (Valid)"
        self.setWindowTitle(self.title + v)

    def reject(self):
        self.done(QDialog.DialogCode.Rejected)

    def accept(self):
        err = False
        c = self.edit_pane.yaml_source()
        if c != None:
            if self.edit_pane.is_valid(c):
                self.sourceable.save(c)
            else:
                err = True
        else:
            err = True
        if err:
            self.reject()
            return
        self.done(QDialog.DialogCode.Accepted)



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
