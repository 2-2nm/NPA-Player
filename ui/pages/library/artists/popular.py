from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui import theme

ROW_H = 52


class PopRow(QWidget):
    clicked = Signal(int)

    def __init__(self, index: int, track, parent=None):
        super().__init__(parent)
        self.index, self.track = index, track
        self.current = False
        self.setFixedHeight(ROW_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def set_current(self, on: bool):
        if on != self.current:
            self.current = on
            self.update()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        if self.current or self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(theme.accent_color(56) if self.current else QColor(255, 255, 255, 14))
            p.drawRoundedRect(r, 14, 14)
        accent = QColor(theme.ACCENT)
        num = QRectF(22, 0, 30, r.height())
        if self.current:  # three little equalizer bars
            p.setPen(Qt.NoPen)
            p.setBrush(accent)
            for i, h in enumerate((8, 14, 10)):
                p.drawRoundedRect(QRectF(num.left() + 2 + i * 6, (r.height() - h) / 2, 3, h), 1.5, 1.5)
        else:
            p.setPen(QColor(theme.MUTED))
            p.setFont(theme.font(15))
            p.drawText(num, Qt.AlignLeft | Qt.AlignVCenter, str(self.index + 1))
        w = r.width()
        title_w = int(w * 0.46) - 70
        p.setPen(accent if self.current else QColor(theme.TEXT))
        p.setFont(theme.font(17, QFont.Weight.Medium if self.current else QFont.Weight.Normal))
        p.drawText(QRectF(70, 0, title_w, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(self.track.title, Qt.ElideRight, title_w))
        ax = 70 + title_w + 16
        aw = int(w - ax - 90)
        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.font(15))
        p.drawText(QRectF(ax, 0, aw, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(self.track.album, Qt.ElideRight, aw))
        p.drawText(QRectF(w - 84, 0, 62, r.height()), Qt.AlignRight | Qt.AlignVCenter,
                   theme.fmt_time(self.track.duration * 1000))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit(self.index)


class PopularList(QWidget):
    """The artist's most played songs; clicking one plays the list from there."""
    rowClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[PopRow] = []
        self._current = None
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(2)
        self._lay.addStretch(1)

    def set_tracks(self, tracks: list):
        while self._lay.count() > 1:
            w = self._lay.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        self._rows = []
        for i, t in enumerate(tracks):
            row = PopRow(i, t)
            row.clicked.connect(self.rowClicked)
            row.set_current(t.id == self._current)
            self._lay.insertWidget(i, row)
            row.show()  # shown at once, so a picture taken right after (the cross-fade) already has the rows
            self._rows.append(row)

    def set_current(self, track_id):
        self._current = track_id
        for r in self._rows:
            r.set_current(r.track.id == track_id)
