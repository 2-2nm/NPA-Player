from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from domain.artist import Artist
from ui import theme
from ui.components.common import Card
from ui.components.smooth_scroll import SmoothScrollArea
from ui.rendering.cover_renderer import CoverRenderer

ROW_H = 72
AVATAR = 56


class _Pill(QWidget):
    """The highlight behind the selected artist; it glides from row to row (like the capsule of the header tabs)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.accent_color(56))
        p.drawRoundedRect(self.rect(), 18, 18)


class ArtistRow(QWidget):
    clicked = Signal(object)

    def __init__(self, artist: Artist, parent=None):
        super().__init__(parent)
        self.artist = artist
        self.selected = False
        self.setFixedHeight(ROW_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def set_selected(self, on: bool):
        if on != self.selected:
            self.selected = on
            self.update()

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            r = QRectF(self.rect())
            if self.underMouse() and not self.selected:  # the selected row's highlight is the gliding pill
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 14))
                p.drawRoundedRect(r, 18, 18)
            a = self.artist
            y = (r.height() - AVATAR) / 2
            pm = CoverRenderer.pixmap_async(a.albums[0].tracks[0], AVATAR, AVATAR // 2)  # newest album's cover, as a circle
            p.drawPixmap(int(18), int(y), pm)
            x = 18 + AVATAR + 16
            w = int(r.width() - x - 12)
            p.setPen(QColor(theme.ACCENT if self.selected else theme.TEXT))
            p.setFont(theme.font(17, QFont.Weight.DemiBold))
            p.drawText(QRectF(x, y, w, 28), Qt.AlignLeft | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(a.name, Qt.ElideRight, w))
            n = len(a.tracks)
            p.setPen(QColor(theme.MUTED))
            p.setFont(theme.font(14))
            p.drawText(QRectF(x, y + 28, w, 24), Qt.AlignLeft | Qt.AlignVCenter, f"{n} song" + ("" if n == 1 else "s"))
        finally:
            p.end()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit(self.artist)


class ArtistList(Card):
    """Left panel of the Artists tab: every artist A-Z with a round cover."""
    radius = 28
    selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[ArtistRow] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 22, 14, 14)
        lay.setSpacing(0)
        cap = QLabel("A \u2013 Z")
        cap.setFont(theme.font(13, QFont.Weight.Medium, 1.6))
        cap.setStyleSheet(f"color:{theme.MUTED};")
        cap.setContentsMargins(18, 0, 0, 0)
        lay.addWidget(cap)
        lay.addSpacing(10)
        self.scroll = SmoothScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        body = QWidget()
        self._body = body
        self._pill = _Pill(body)  # created before the rows, so it sits behind them
        self._pill.hide()
        self._key = None
        self._anim = QPropertyAnimation(self._pill, b"geometry", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        body.installEventFilter(self)
        self._lay = QVBoxLayout(body)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(4)
        self._lay.addStretch(1)
        self.scroll.setWidget(body)
        body.setAutoFillBackground(False)
        self.scroll.viewport().setAutoFillBackground(False)
        lay.addWidget(self.scroll, 1)
        # covers arrive from background threads in bursts: repaint once per burst
        self._repaint = QTimer(self, singleShot=True, interval=40)
        self._repaint.timeout.connect(self._update_rows)
        CoverRenderer.signals().ready.connect(self._repaint.start)

    def _update_rows(self):
        for r in self._rows:
            r.update()

    def rows(self) -> list:
        return self._rows

    def set_artists(self, artists: list, selected_key=None):
        old = {r.artist.key: r for r in self._rows}
        keep = {a.key for a in artists}
        for k, r in old.items():
            if k not in keep:
                r.hide()
                r.deleteLater()
        rows = []
        for a in artists:
            r = old.get(a.key)
            if r is None or r.artist != a:  # an artist that did not change keeps its row
                if r is not None:
                    r.hide()
                    r.deleteLater()
                r = ArtistRow(a)
                r.clicked.connect(self.selected)
            rows.append(r)
        while self._lay.count() > 1:
            self._lay.takeAt(0)
        for i, r in enumerate(rows):
            self._lay.insertWidget(i, r)
            r.show()
        self._rows = rows
        self.set_selected(selected_key)

    def eventFilter(self, obj, e):
        if obj is self._body and e.type() == QEvent.Type.Resize:
            self._move(False)  # the rows got another width: the pill follows
        return False

    def showEvent(self, e):
        super().showEvent(e)
        self._move(False)

    def set_selected(self, key, animate: bool = False):
        """animate=True (a click) glides the highlight to the new row; otherwise it jumps there."""
        self._key = key
        for r in self._rows:
            r.set_selected(r.artist.key == key)
        self._move(animate)

    def _target(self) -> QRect | None:
        r = next((r for r in self._rows if r.artist.key == self._key), None)
        return r.geometry() if r is not None else None

    def _move(self, animate: bool):
        self._body.layout().activate()  # row positions are only right after the layout ran
        target = self._target()
        self._anim.stop()
        if target is None:
            self._pill.hide()
            return
        if animate and self.isVisible() and self._pill.isVisible() and self._pill.geometry() != target:
            self._anim.setStartValue(self._pill.geometry())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._pill.setGeometry(target)
            self._pill.show()
        for r in self._rows:
            r.raise_()  # the pill never ends up above a row
