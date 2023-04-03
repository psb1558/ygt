from PyQt6.QtCore import (pyqtSignal, Qt, QTimer, pyqtSlot)
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
from .ygSchema import is_valid, set_error_message, error_message, have_error_message

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
    """ An editor for source code for the current axis of the current glyph.

        Params:

        preferences (ygPreferences): The preferences object for the current file.
    """

    sig_source_from_editor = pyqtSignal(object)
    sig_status = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def __init__(self, preferences, parent=None):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        self.setStyleSheet("ygYAMLEditor {font-family: Source Code Pro, monospace; background-color: white; }")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preferences = preferences
        self.textChanged.connect(self.text_changed)
        self._highlighter = ygGlyphHighlighter()
        self._timer = QTimer()
        self._timer.timeout.connect(self.check_valid)
        self.code_valid = True
        self.setup_editor()

    def setup_error_signal(self, f):
        self.sig_error.connect(f)

    @pyqtSlot(object)
    def install_source(self, text):
        self.setPlainText(text)

    @pyqtSlot()
    def yaml_source(self):
        err = False
        msg = ""
        try:
            s = yaml.safe_load(self.toPlainText())
        except Exception as e:
            err = True
            set_error_message("Source can't be parsed.")
            msg = str(e)
        if not err:
            try:
                err = not is_valid({"points": s})
            except SchemaError as s:
                err = True
        if err:
            self.sig_error.emit({"msg": error_message(), "mode": "console"})
        else:
            self.sig_source_from_editor.emit(s)

    def setup_status_indicator(self, o):
        self.sig_status.connect(o)

    def setup_editor_signals(self, f):
        self.sig_source_from_editor.connect(f)

    def disconnect_editor_signals(self, f):
        self.sig_source_from_editor.disconnect(f)

    @pyqtSlot()
    def check_valid(self):
        if not self.code_valid:
            if not have_error_message():
                set_error_message("Source can't be parsed.")
            self.sig_error.emit({"msg": error_message(), "mode": "console"})
            self.sig_status.emit(self.code_valid)

    @pyqtSlot()
    def text_changed(self):
        self.code_valid = True
        y = self.toPlainText()
        if len(y) == 0:
            self.setPlainText("[]\n")
        else:
            try:
                y = yaml.safe_load(y)
            except Exception as e:
                self.code_valid = False
            if self.code_valid:
                self.code_valid = is_valid({"points": y})
        # If code is not valid, start timer. Any time user presses a key,
        # the timer will restart if code is not (yet) valid. The effect is
        # that user has two seconds after any keypress to achieve validity
        # before any message is displayed.
        if self.code_valid:
            try:
                self._timer.stop()
            except Exception:
                pass
            self.sig_status.emit(self.code_valid)
        else:
            self._timer.start(2000)
        

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
    """ An editor for any chunk of code from current file, e.g. functions.
        This validates as the user types, but it only emits an error two
        seconds after user has stopped typing. This cuts back on unnecessary
        messages when (for example) a user is typing "true"--which is not
        valid until the word is complete.

        Params:

        owner: The dialog or window that owns this pane.

        sourceable: Object of type Sourceable: the thing to edit.

        validator: function that will throw an exception if text is not valid.

        save_on_focus_out (bool): Whether to auto-save if user leaves this
        editor.


    """

    sig_error = pyqtSignal(object)

    def __init__(self, owner, sourceable, validator, save_on_focus_out=False):
        super().__init__()
        self.save_on_focus_out = save_on_focus_out
        self.owner = owner
        self.textChanged.connect(self.text_changed)
        # error_state is true if the code in this editor is invalid.
        self.error_state = False
        self.set_style()
        self.watching_for_changes = False
        self.is_valid = validator
        self.sourceable = sourceable
        self.install_yaml(copy.copy(self.sourceable.source()))
        self.dirty = False
        self._timer = QTimer()
        self._timer.timeout.connect(self.check_valid)

    def setup_error_signal(self, f):
        self.sig_error.connect(f)

    def install_text(self, text):
        self.setPlainText(text)
        self.watching_for_changes = True

    def install_yaml(self, y):
        try:
            t = yaml.dump(y, sort_keys=False, Dumper=Dumper)
        except Exception as e:
            print(e)
            t = self.owner._empty_string
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
            self.sig_error.emit({"msg": "Source can't be parsed.", "mode": "console"})

    @pyqtSlot()
    def check_valid(self):
        self.set_error_state(True)
        self.sig_error.emit({"msg": error_message(), "mode": "console"})

    @pyqtSlot()
    def text_changed(self):
        if not self.watching_for_changes:
            return
        self.sourceable.set_clean(False)
        if len(self.toPlainText()) == 0:
            self.setPlainText(self.owner._empty_string)
        v = False
        try:
            v = self.is_valid(yaml.safe_load(self.toPlainText()))
        except Exception as e:
            self.set_error_state(True)
            set_error_message("Source can't be parsed.")
            self.sig_error.emit({"msg": error_message(), "mode": "console"})
        if v:
            self._timer.stop()
            error_message()
            self.set_error_state(not v)
        else:
            self._timer.start(2000)
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
                set_error_message("Source can't be parsed.")
            if self.error_state:
                self.sig_error.emit({"msg": error_message(), "mode": "console"})

    def showEvent(self, event):
        self.install_yaml(copy.copy(self.sourceable.source()))

    def refresh(self):
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
        self.edit_pane.setup_error_signal(self.preferences.top_window().error_manager.new_message)
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
