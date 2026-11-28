import time

from PySide6.QtCore import QVariantAnimation, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui import theme
from ui.pages.now_playing import audio_info
from ui.pages.now_playing.controls import BigPlayButton, ModeButton
from ui.pages.now_playing.side_panel import SidePanel
from ui.pages.now_playing.stage import Stage, dominant_color
from ui.pages.now_playing.waveform import WaveformSeek
from ui.components.common import ElidedLabel, IconButton


class NowPlayingPage(QWidget):
    """The 'Now playing' screen. Self-contained: it only needs the PlayerService and keeps itself in sync.

    accentChanged is emitted (animated) when the track changes, so the main window can tint its backdrop."""
    TAB_QUEUE, TAB_LYRICS, TAB_INFO = SidePanel.TAB_QUEUE, SidePanel.TAB_LYRICS, SidePanel.TAB_INFO
    accentChanged = Signal(QColor)
    tabChanged = Signal(int)  # the user picked Tracks / Lyrics / Info

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self._accent = QColor(theme.ACCENT)
        self._anim = QVariantAnimation(self, duration=500)
        self._anim.valueChanged.connect(self._set_accent)
        self._build()
        self._wire()
        self._on_modes()
        self.play_btn.set_playing(player.is_playing())
        if player.current:
            self._on_track(player.current)

    @property
    def accent(self) -> QColor:
        return QColor(self._accent)

    # ---------- ui ----------
    def _build(self):
        col = self._col = QWidget()
        col.setMaximumWidth(720)
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.stage = Stage()
        lay.addWidget(self.stage, 1)
        lay.addSpacing(16)
        self.title = ElidedLabel("Nothing playing", 32, QFont.Weight.Bold)
        self.sub = ElidedLabel("", 15, color=theme.MUTED)
        lay.addWidget(self.title)
        lay.addWidget(self.sub)
        lay.addSpacing(14)
        self.wave = WaveformSeek()
        lay.addWidget(self.wave)
        lay.addSpacing(4)

        times = QHBoxLayout()
        self.t_cur, self.t_rem = QLabel("0:00"), QLabel("-0:00")
        for l in (self.t_cur, self.t_rem):
            l.setFont(theme.font(13))
            l.setStyleSheet(f"color:{theme.MUTED};")
        self.badge = QLabel("")
        self.badge.setFont(theme.font(12))
        self.badge.setStyleSheet("background:rgba(255,255,255,0.10);color:#e8ebff;border-radius:7px;padding:2px 10px;")
        self.badge.hide()
        times.addWidget(self.t_cur)
        times.addStretch(1)
        times.addWidget(self.badge)
        times.addStretch(1)
        times.addWidget(self.t_rem)
        lay.addLayout(times)

        row = QHBoxLayout()
        self.shuffle_btn, self.repeat_btn = ModeButton("shuffle"), ModeButton("repeat")
        self.prev_btn, self.next_btn = IconButton("prev", 52, 28), IconButton("next", 52, 28)
        self.play_btn = BigPlayButton()
        row.addStretch(1)
        for i, w in enumerate((self.shuffle_btn, self.prev_btn, self.play_btn, self.next_btn, self.repeat_btn)):
            if i:
                row.addSpacing(10)
            row.addWidget(w)
        row.addStretch(1)
        lay.addLayout(row)

        self.panel = SidePanel()
        self.panel.setFixedWidth(440)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addStretch(1)  # equal stretches keep the left column centred when the window is wide
        root.addWidget(col, 100)
        root.addStretch(1)
        root.addSpacing(28)
        root.addWidget(self.panel)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # In fullscreen the left column and the panel get wider too (normal window: 720 and 440, unchanged; panel up to 640)
        w = self.width()
        self._col.setMaximumWidth(max(720, int(w * 0.55)))
        self.panel.setFixedWidth(max(440, min(640, int(w * 0.34))))

    def _wire(self):
        p = self.player
        p.trackChanged.connect(self._on_track)
        p.positionChanged.connect(self._on_position)
        p.durationChanged.connect(lambda _: self._on_position(p.position()))
        p.playingChanged.connect(self._on_playing)
        p.modesChanged.connect(self._on_modes)
        self.play_btn.clicked.connect(p.toggle)
        self.prev_btn.clicked.connect(p.prev)
        self.next_btn.clicked.connect(p.next)
        self.shuffle_btn.clicked.connect(lambda: p.set_shuffle(not p.shuffle))
        self.repeat_btn.clicked.connect(p.cycle_repeat)
        self.wave.seekRequested.connect(p.seek_ratio)
        self.panel.seekMs.connect(p.seek_ms)
        self.panel.playIndex.connect(p.play_index)
        self.panel.tabChanged.connect(self.tabChanged)
        self.stage.scrubStarted.connect(self._scrub_start)
        self.stage.scrubbed.connect(self._scrub)
        self.stage.scrubFinished.connect(self._scrub_end)

    # ---------- public ----------
    def show_tab(self, i: int):
        self.panel.set_tab(i)

    # ---------- turning the record ----------
    def _scrub_start(self):
        self._scrub_base = self.player.position()
        self._scrub_target = self._scrub_base
        self._scrub_sent = 0.0

    def _scrub(self, seconds: float):
        cur = self.player.current
        dur = self.player.duration() or (int(cur.duration * 1000) if cur else 0)
        # never quite to the end: that would skip to the next song while the user is still turning
        self._scrub_target = int(min(max(self._scrub_base + seconds * 1000, 0), max(0, dur - 300)))
        now = time.monotonic()
        if now - self._scrub_sent >= 0.05:  # the song is heard while turning, but not re-seeked on every pixel
            self._scrub_sent = now
            self.player.seek_ms(self._scrub_target)

    def _scrub_end(self):
        self.player.seek_ms(self._scrub_target)

    # ---------- reactions ----------
    def _on_track(self, t):
        self.title.setText(t.title)
        self.sub.setText(" · ".join(x for x in (t.artist, t.album, str(t.year) if t.year else "") if x))
        self.stage.set_track(t)
        self.wave.set_track(t)
        q = audio_info.quality(t)
        self.badge.setText(q)
        self.badge.setVisible(bool(q))
        self.panel.set_track(t)
        self.panel.set_queue(self.player.queue, self.player.index)
        self._retint(dominant_color(t))
        self._on_position(self.player.position())

    def _on_position(self, pos: int):
        cur = self.player.current
        dur = self.player.duration() or (int(cur.duration * 1000) if cur else 0)
        self.t_cur.setText(theme.fmt_time(pos))
        self.t_rem.setText("-" + theme.fmt_time(max(0, dur - pos)))
        self.wave.set_value(pos / dur if dur else 0)
        self.panel.set_position(pos)

    def _on_playing(self, playing: bool):
        self.play_btn.set_playing(playing)
        self.stage.set_playing(playing)

    def _on_modes(self):
        self.shuffle_btn.set_state(self.player.shuffle)
        mode = self.player.repeat
        self.repeat_btn.set_state(mode != "off", mode == "one")
        self.panel.set_queue(self.player.queue, self.player.index)

    def _retint(self, color: QColor):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._accent))
        self._anim.setEndValue(QColor(color))
        self._anim.start()

    def _set_accent(self, c):
        self._accent = QColor(c)
        self.stage.set_accent(self._accent)
        self.play_btn.set_accent(self._accent)
        self.accentChanged.emit(self._accent)