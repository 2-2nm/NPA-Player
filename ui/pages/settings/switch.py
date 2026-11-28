from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from ui import theme


class Switch(QAbstractButton):
    """On / off switch; the knob glides. `toggled(bool)` fires when the user flips it, set_on() does not emit."""

    def __init__(self, on: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(50, 30)
        self._t = 1.0 if on else 0.0
        super().setChecked(on)
        self._anim = QVariantAnimation(self, duration=170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._step)
        self.toggled.connect(self._glide)

    def set_on(self, on: bool):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._anim.stop()
        self._t = 1.0 if on else 0.0
        self.update()

    def _glide(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _step(self, v):
        self._t = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._t
        off, on = QColor(255, 255, 255, 46), QColor(theme.ACCENT)
        mix = lambda a, b: a + (b - a) * t
        track = QColor(int(mix(off.red(), on.red())), int(mix(off.green(), on.green())),
                       int(mix(off.blue(), on.blue())), int(mix(off.alpha(), 255)))
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setOpacity(1.0 if self.isEnabled() else 0.4)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 8
        x = r.left() + 4 + (r.width() - d - 8) * t
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, r.top() + 4, d, d))
