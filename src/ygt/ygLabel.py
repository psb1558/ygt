from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt

class ygLabel(QWidget):
    # In Qt one commonly adds a QPixmap to a QLabel to display images in a widget;
    # but the image is always antialiased. Since our glyph images are already
    # antialiased by Freetype, we don't want this. So we make our own QLabel clone.

    def __init__(self):
        super().__init__()
        self.pm = None

    def setPixmap(self, pm):
        self.pm = pm
        self.update()

    def paintEvent(self, event):
        if not self.pm:
            return
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing, on=False)
        self.style().drawItemPixmap(qp, self.rect(), Qt.AlignmentFlag.AlignCenter, self.pm)
        qp.end()
