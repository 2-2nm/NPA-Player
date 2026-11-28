from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ui import theme
from ui.components.common import Card, ElidedLabel
from ui.components.smooth_scroll import SmoothScrollArea
from ui.pages.settings.accent import AccentPicker
from ui.pages.settings.switch import Switch
from ui.shell.header import CapsuleButton

CONTENT_W = 780


class _Row(QWidget):
    """Title and a line of explanation on the left, the control on the right."""

    def __init__(self, title: str, desc: str, control: QWidget, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 14, 0, 14)
        lay.setSpacing(20)
        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel(title)
        t.setFont(theme.font(16, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color:{theme.TEXT};")
        self.desc = ElidedLabel(desc, 14, color=theme.MUTED)
        text.addWidget(t)
        text.addWidget(self.desc)
        lay.addLayout(text, 1)
        lay.addWidget(control, 0, Qt.AlignVCenter)


class _Section(Card):
    radius = 26

    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(30, 22, 30, 8)
        self._lay.setSpacing(0)
        cap = QLabel(caption.upper())
        cap.setFont(theme.font(12, QFont.Weight.Medium, 1.8))
        cap.setStyleSheet(f"color:{theme.DIM};")
        self._lay.addWidget(cap)
        self._rows = 0

    def add(self, row: QWidget):
        if self._rows:
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background:rgba(255,255,255,0.07);")
            self._lay.addWidget(line)
        self._lay.addWidget(row)
        self._rows += 1


class SettingsPage(QWidget):
    coverGlowChanged = Signal(bool)
    accentChanged = Signal(str)
    restoreChanged = Signal(bool)
    openFoldersRequested = Signal()
    openDataFolderRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = SmoothScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        body = QWidget()
        wrap = QHBoxLayout(body)  # content kept to a readable width, left aligned with the title
        wrap.setContentsMargins(0, 0, 0, 0)
        col_w = QWidget()
        col_w.setMaximumWidth(CONTENT_W)
        col = QVBoxLayout(col_w)
        col.setContentsMargins(0, 0, 0, 24)
        col.setSpacing(22)
        wrap.addWidget(col_w, 1)
        wrap.addStretch(0)

        # Appearance
        ap = _Section("Appearance")
        self.glow = Switch(True)
        self.glow.toggled.connect(self.coverGlowChanged)
        ap.add(_Row("Cover colour glow", "The background glow follows the colour of the cover that is playing.", self.glow))
        col.addWidget(ap)

        # Accent colour
        ac = _Section("Accent colour")
        hint = ElidedLabel("Used for the waveform, the selected album, artist and song, switches and highlights.",
                           14, color=theme.MUTED)
        hint.setContentsMargins(0, 10, 0, 12)
        ac.add(hint)
        self.accent = AccentPicker()
        self.accent.accentPicked.connect(self.accentChanged)
        ac.add(self.accent)
        col.addWidget(ac)

        # Playback
        pb = _Section("Playback")
        self.restore = Switch(True)
        self.restore.toggled.connect(self.restoreChanged)
        pb.add(_Row("Resume where you left off", "Start with the last queue and song ready, paused at the same spot.", self.restore))
        col.addWidget(pb)

        # Library
        lib = _Section("Library")
        open_folders = CapsuleButton("Open Folders", "secondary")
        open_folders.clicked.connect(self.openFoldersRequested)
        self._lib_row = _Row("Music and lyrics folders", "", open_folders)
        lib.add(self._lib_row)
        col.addWidget(lib)

        # About
        ab = _Section("About")
        open_data = CapsuleButton("Show in Explorer", "secondary")
        open_data.clicked.connect(self.openDataFolderRequested)
        self._data_row = _Row("Data folder", "", open_data)
        ab.add(self._data_row)
        col.addWidget(ab)
        col.addStretch(1)

        self.scroll.setWidget(body)
        body.setAutoFillBackground(False)
        self.scroll.viewport().setAutoFillBackground(False)
        outer.addWidget(self.scroll)

    def set_accent(self, color: str):
        self.accent.set_accent(color)

    def set_values(self, cover_glow: bool, restore: bool):
        self.glow.set_on(cover_glow)
        self.restore.set_on(restore)

    def set_library_info(self, songs: int, albums: int, artists: int):
        s = lambda n, w: f"{n:,} {w}" + ("" if n == 1 else "s")
        self._lib_row.desc.setText(f"{s(songs, 'song')} \u00b7 {s(albums, 'album')} \u00b7 {s(artists, 'artist')}")

    def set_data_dir(self, path: str):
        self._data_row.desc.setText(path)
