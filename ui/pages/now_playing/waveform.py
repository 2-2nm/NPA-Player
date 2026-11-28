import random

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui import theme

N = 240  # resolution of the stored profile; it is resampled to the bars that fit


def _profile(seed: int) -> list[float]:
    """A stable, stylised waveform per track (same track -> same shape). It is not decoded from the audio."""
    rng = random.Random(seed)
    raw, cur = [], 0.5
    for _ in range(N):
        cur = min(1.0, max(0.12, cur + (rng.random() - 0.5) * 0.5))
        raw.append(cur)
    out = []
    for i in range(N):
        smooth = (raw[max(0, i - 1)] + 2 * raw[i] + raw[min(N - 1, i + 1)]) / 4
        edge = 0.35 + 0.65 * min(1.0, min(i, N - 1 - i) / 14)  # softer at the start and end
        out.append(max(0.1, smooth * edge))
    return out


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


class WaveformSeek(QWidget):
    seekRequested = Signal(float)

    def __init__(self, height: int = 56, parent=None):
        super().__init__(parent)
        self._v = 0.0
        self._hover = -1.0
        self._drag = False
        self._peaks = _profile(0)
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_track(self, track):
        self._peaks = _profile(track.id if track else 0)
        self.update()

    def set_value(self, v: float):
        if self._drag:
            return
        self._v = min(1.0, max(0.0, v))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar = 4.0
        n = max(8, int(w // 9))
        cy = h / 2
        base, hover = QColor(255, 255, 255, 54), QColor(255, 255, 255, 96)
        c1, c2 = QColor(theme.ACCENT), QColor(theme.ACCENT_B)  # the accent colour chosen in Settings
        for i in range(n):
            frac = i / (n - 1)
            x = bar / 2 + frac * (w - bar)
            bh = max(4.0, self._peaks[int(frac * (N - 1))] * (h - 4))
            if frac <= self._v:
                color = _mix(c1, c2, frac)
            elif 0 <= self._hover and frac <= self._hover:
                color = hover
            else:
                color = base
            p.setPen(QPen(color, bar, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x, cy - bh / 2), QPointF(x, cy + bh / 2))
        if self._v > 0:
            p.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap))
            x = self._v * w
            p.drawLine(QPointF(x, 2), QPointF(x, h - 2))

    def _emit(self, x: float):
        self._v = min(1.0, max(0.0, x / max(1, self.width())))
        self.update()
        self.seekRequested.emit(self._v)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = True
            self._emit(e.position().x())

    def mouseMoveEvent(self, e):
        self._hover = min(1.0, max(0.0, e.position().x() / max(1, self.width())))
        if self._drag:
            self._emit(e.position().x())
        else:
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = False

    def leaveEvent(self, e):
        self._hover = -1.0
        self.update()