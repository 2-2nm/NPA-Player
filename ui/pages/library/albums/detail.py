from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from domain.album import Album
from ui import theme
from ui.components.smooth_scroll import SmoothScrollArea
from ui.components.common import Card, CoverLabel, ElidedLabel
from ui.components.tint import TintFade, cover_tint
from ui.shell.header import CapsuleButton

COVER = 128
ROW_H = 44


class TrackRow(QWidget):
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
        if self.current:
            p.setPen(Qt.NoPen)
            p.setBrush(theme.accent_color(56))
            p.drawRoundedRect(r, 12, 12)
        elif self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 14))
            p.drawRoundedRect(r, 12, 12)
        accent = QColor(theme.ACCENT)
        num = QRectF(14, 0, 30, r.height())
        if self.current:  # three little equalizer bars
            p.setPen(Qt.NoPen)
            p.setBrush(accent)
            for i, h in enumerate((8, 14, 10)):
                p.drawRoundedRect(QRectF(num.left() + 2 + i * 6, (r.height() - h) / 2, 3, h), 1.5, 1.5)
        else:
            p.setPen(QColor(theme.MUTED))
            p.setFont(theme.font(15))
            p.drawText(num, Qt.AlignLeft | Qt.AlignVCenter, str(self.index + 1))
        p.setPen(accent if self.current else QColor(theme.TEXT))
        p.setFont(theme.font(16, QFont.Weight.Medium if self.current else QFont.Weight.Normal))
        title_r = QRectF(58, 0, r.width() - 58 - 76, r.height())
        p.drawText(title_r, Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(self.track.title, Qt.ElideRight, int(title_r.width())))
        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.font(15))
        p.drawText(QRectF(r.width() - 76, 0, 62, r.height()), Qt.AlignRight | Qt.AlignVCenter,
                   theme.fmt_time(self.track.duration * 1000))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit(self.index)


class AlbumDetail(Card):
    """Right-hand panel of the Albums tab: cover, info, Play / Shuffle / Add to queue and the track list."""
    radius = 28
    playRequested = Signal(int)   # start playing the album from this track
    shuffleClicked = Signal()
    queueClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tint = TintFade(self)  # the card follows the colour of the album cover
        self._tint.changed.connect(self.update)
        self._rows: list[TrackRow] = []
        self.album: Album | None = None
        self._current_id = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 16)
        lay.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(20)
        self.cover = CoverLabel(COVER, 20)
        head.addWidget(self.cover, 0, Qt.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(0)
        kicker = QLabel("ALBUM")
        kicker.setFont(theme.font(12, QFont.Weight.Medium, 1.8))
        kicker.setStyleSheet(f"color:{theme.MUTED};")
        self.title = ElidedLabel("", 28, QFont.Weight.Bold)
        self.title.setFixedHeight(44)
        self.artist = ElidedLabel("", 17, color="#c9d3ff")
        self.meta = ElidedLabel("", 14, color=theme.MUTED)
        self.badges = QHBoxLayout()
        self.badges.setSpacing(8)
        self.badges.setContentsMargins(0, 0, 0, 0)
        info.addWidget(kicker)
        info.addWidget(self.title)
        info.addWidget(self.artist)
        info.addSpacing(6)
        info.addWidget(self.meta)
        info.addSpacing(10)
        info.addLayout(self.badges)
        info.addStretch(1)
        head.addLayout(info, 1)
        lay.addLayout(head)
        lay.addSpacing(22)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.play_btn = CapsuleButton("Play", "primary")
        self.shuffle_btn = CapsuleButton("Shuffle", "secondary")
        self.queue_btn = CapsuleButton("Add to queue", "secondary")
        self.play_btn.clicked.connect(lambda: self.playRequested.emit(0))
        self.shuffle_btn.clicked.connect(lambda: self.shuffleClicked.emit())
        self.queue_btn.clicked.connect(lambda: self.queueClicked.emit())
        for b in (self.play_btn, self.shuffle_btn, self.queue_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        lay.addLayout(btns)
        lay.addSpacing(18)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:rgba(255,255,255,0.10);border:none;")
        lay.addWidget(line)
        lay.addSpacing(10)

        self.scroll = SmoothScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        body = QWidget()
        self._rows_lay = QVBoxLayout(body)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(2)
        self._rows_lay.addStretch(1)
        self.scroll.setWidget(body)
        body.setAutoFillBackground(False)
        self.scroll.viewport().setAutoFillBackground(False)
        lay.addWidget(self.scroll, 1)
        self.set_album(None)

    def paint_background(self, p: QPainter, r: QRectF):
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        c = self._tint.color
        top, mid, edge = QColor(c), QColor(c), QColor(c.lighter(135))
        top.setAlpha(100)
        mid.setAlpha(28)
        edge.setAlpha(80)
        g.setColorAt(0.0, top)
        g.setColorAt(0.55, mid)
        g.setColorAt(1.0, QColor(255, 255, 255, 10))
        p.setBrush(g)
        p.setPen(edge)
        p.drawRoundedRect(r, self.radius, self.radius)

    def set_album(self, album: Album | None):
        self.album = album
        while self._rows_lay.count() > 1:
            w = self._rows_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        while self.badges.count():
            w = self.badges.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._rows = []
        for b in (self.play_btn, self.shuffle_btn, self.queue_btn):
            b.setEnabled(album is not None)
        if album is None:
            self.cover.set_track(None)
            self.title.setText("")
            self.artist.setText("")
            self.meta.setText("")
            return
        self.cover.set_track(album.tracks[0])
        self._tint.set_target(cover_tint(album.tracks[0]))
        self.title.setText(album.title)
        self.artist.setText(album.artist)
        mins = max(1, round(album.duration / 60))
        n = len(album.tracks)
        parts = ([str(album.year)] if album.year else []) + [f"{n} song" + ("" if n == 1 else "s"), f"{mins} min"]
        self.meta.setText(" \u00b7 ".join(parts))
        for f in album.formats:
            tag = QLabel(f)
            tag.setFont(theme.font(13, QFont.Weight.Medium))
            tag.setStyleSheet("color:#c9d3ff;background:rgba(255,255,255,0.10);border-radius:10px;padding:3px 12px;")
            self.badges.addWidget(tag)
        self.badges.addStretch(1)
        for i, t in enumerate(album.tracks):
            row = TrackRow(i, t)
            row.clicked.connect(self.playRequested)
            row.set_current(t.id == self._current_id)
            self._rows_lay.insertWidget(i, row)
            self._rows.append(row)

    def set_current(self, track_id):
        self._current_id = track_id
        for r in self._rows:
            r.set_current(r.track.id == track_id)
