from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from domain.artist import Artist
from ui import theme
from ui.components.common import Card, ElidedLabel
from ui.components.tint import TintFade, cover_tint
from ui.rendering.cover_renderer import CoverRenderer
from ui.shell.header import CapsuleButton

AVATAR = 150
HERO_H = 218


class ArtistHero(Card):
    """Top card of the selected artist: round cover, name, counts and Play all / Shuffle / Add to queue."""
    radius = 32
    playClicked = Signal()
    shuffleClicked = Signal()
    queueClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tint = TintFade(self)  # the card follows the colour of the artist's cover
        self._tint.changed.connect(self.update)
        self.artist: Artist | None = None
        self.setFixedHeight(HERO_H)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(34, 30, 34, 30)
        lay.setSpacing(34)
        self.avatar = QLabel()
        self.avatar.setFixedSize(AVATAR, AVATAR)
        lay.addWidget(self.avatar, 0, Qt.AlignVCenter)
        info = QVBoxLayout()
        info.setSpacing(0)
        kicker = QLabel("ARTIST")
        kicker.setFont(theme.font(13, QFont.Weight.Medium, 2.2))
        kicker.setStyleSheet("color:#aab6ee;")
        self.name = ElidedLabel("", 44, QFont.Weight.Bold)
        self.name.setFixedHeight(64)
        self.meta = ElidedLabel("", 17, color="#aab6ee")
        info.addStretch(1)
        info.addWidget(kicker)
        info.addWidget(self.name)
        info.addWidget(self.meta)
        info.addSpacing(16)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.play_btn = CapsuleButton("Play all", "primary")
        self.shuffle_btn = CapsuleButton("Shuffle", "secondary")
        self.queue_btn = CapsuleButton("Add to queue", "secondary")
        self.play_btn.clicked.connect(lambda: self.playClicked.emit())
        self.shuffle_btn.clicked.connect(lambda: self.shuffleClicked.emit())
        self.queue_btn.clicked.connect(lambda: self.queueClicked.emit())
        for b in (self.play_btn, self.shuffle_btn, self.queue_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        info.addLayout(btns)
        info.addStretch(1)
        lay.addLayout(info, 1)
        self.set_artist(None)

    def paint_background(self, p: QPainter, r: QRectF):
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        c = self._tint.color
        top, mid, edge = QColor(c), QColor(c), QColor(c.lighter(135))
        top.setAlpha(150)
        mid.setAlpha(55)
        edge.setAlpha(90)
        g.setColorAt(0.0, top)
        g.setColorAt(0.6, mid)
        g.setColorAt(1.0, QColor(255, 255, 255, 8))
        p.setBrush(g)
        p.setPen(edge)
        p.drawRoundedRect(r, self.radius, self.radius)

    def refresh_cover(self):
        if self.artist:
            self.avatar.setPixmap(CoverRenderer.pixmap(self.artist.albums[0].tracks[0], AVATAR, AVATAR // 2))
        else:
            self.avatar.setPixmap(CoverRenderer.placeholder(AVATAR, AVATAR // 2))

    def set_artist(self, artist: Artist | None):
        self.artist = artist
        for b in (self.play_btn, self.shuffle_btn, self.queue_btn):
            b.setEnabled(artist is not None)
        self.refresh_cover()
        # no glide here: the Artists view cross-fades the whole right side, which already carries the change
        self._tint.set_target(cover_tint(artist.albums[0].tracks[0]) if artist else None, animate=False)
        if artist is None:
            self.name.setText("")
            self.meta.setText("")
            return
        self.name.setText(artist.name)
        na, ns = len(artist.albums), len(artist.tracks)
        total = artist.duration
        h, m = int(total // 3600), int(total % 3600 // 60)
        self.meta.setText(f"{na} album{'' if na == 1 else 's'} \u00b7 {ns} song{'' if ns == 1 else 's'} \u00b7 {h} h {m} m")
