from PyQt6.QtWidgets import QDialog, QLineEdit, QCompleter, QVBoxLayout, QDialogButtonBox

class ygGlyphPicker(QDialog):
    def __init__(self, glyph_name_list, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Find Glyph")
        self.result = ""
        _layout = QVBoxLayout()
        completer = QCompleter(glyph_name_list)
        self.editor = QLineEdit()
        self.editor.setCompleter(completer)
        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        _layout.addWidget(self.editor)
        _layout.addWidget(buttonBox)
        self.setLayout(_layout)

    def reject(self) -> None:
        self.done(QDialog.DialogCode.Rejected)

    def accept(self) -> None:
        t = self.editor.text()
        if t:
            self.result = t
            self.done(QDialog.DialogCode.Accepted)
        else:
            self.reject()
