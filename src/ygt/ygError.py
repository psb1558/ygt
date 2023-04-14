from typing import Any, Optional
from collections import deque
from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSlot, pyqtSignal, QObject, QEvent


class ygErrorWindow(QPlainTextEdit):
    def __init__(self, init_text: list = []) -> None:
        super().__init__()
        self.setMaximumBlockCount(100)
        self.setReadOnly(True)
        if len(init_text) > 0:
            self.fill_in(init_text)
        self.window().setWindowTitle("Error Console")

    def fill_in(self, msg_list: list) -> None:
        self.clear()
        for m in msg_list:
            self.appendPlainText(m)
        self.centerCursor()

    def add_message(self, m: str) -> None:
        self.appendPlainText("")
        self.appendPlainText(m)
        self.centerCursor()

    def closeEvent(self, event) -> None:
        self.hide()


class ygErrorMessages:
    def __init__(self, top_window: Any) -> None:
        self.error_pane: Optional[ygErrorWindow] = None
        self.top_window = top_window
        self.last_message = ""

    # @pyqtSlot(object)
    def new_message(self, m: dict) -> None:
        msg = m["msg"]
        if msg and (msg != self.last_message):
            self.last_message = msg
            if m["mode"] == "console":
                if not self.error_pane:
                    self.error_pane = ygErrorWindow()
                    qg = self.top_window.screen().availableGeometry()
                    x = qg.x() + 100
                    y = qg.y() + 100
                    width = qg.width() * 0.35
                    height = qg.height() * 0.30
                    self.error_pane.setGeometry(int(x), int(y), int(width), int(height))
                    self.error_pane.show()
                else:
                    if not self.error_pane.isVisible():
                        self.error_pane.show()
                        self.error_pane.raise_()
                self.error_pane.add_message(msg)
            else:
                self.top_window.show_error_message(["Error", "Error", msg])
