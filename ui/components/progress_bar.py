from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from ui import theme


class ProgressBar(QWidget):
    seekRequested = Signal(float)

    def __init__(self, c1=None, c2=None, parent=None):  # None: the accent colours (read while painting)
        super().__init__(parent)
        self._v = 0.0
        self._c1, self._c2 = (QColor(c1) if c1 else None), (QColor(c2) if c2 else None)
        self._drag = False
        self.setFixedHeight(18)
        self.setCursor(Qt.PointingHandCursor)

    def set_value(self, v: float):
        if self._drag:
            return
        self._v = min(1.0, max(0.0, v))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QRectF(0, (self.height() - 4) / 2, self.width(), 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 36))
        p.drawRoundedRect(g, 2, 2)
        if self._v > 0:
            f = QRectF(g.x(), g.y(), max(4.0, g.width() * self._v), 4)
            grad = QLinearGradient(f.left(), 0, f.right(), 0)
            grad.setColorAt(0, self._c1 or QColor(theme.GRAD_A))
            grad.setColorAt(1, self._c2 or QColor(theme.GRAD_B))
            p.setBrush(grad)
            p.drawRoundedRect(f, 2, 2)

    def _emit(self, x: float):
        self._v = min(1.0, max(0.0, x / max(1, self.width())))
        self.update()
        self.seekRequested.emit(self._v)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = True
            self._emit(e.position().x())

    def mouseMoveEvent(self, e):
        if self._drag:
            self._emit(e.position().x())

    def mouseReleaseEvent(self, e):
        self._drag = False
