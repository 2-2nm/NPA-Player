from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QColorDialog, QGridLayout, QVBoxLayout, QWidget

from ui import theme
from ui.shell.header import CapsuleButton

# (name, colour): the app's own blue first, then the Windows accent palette (as in NPI Gallery)
PRESETS = (
    ("Default", theme.DEFAULT_ACCENT),
    ("Gold", "#ffb900"), ("Orange", "#f7630c"), ("Brick red", "#e74856"), ("Crimson", "#c50f1f"),
    ("Pink", "#e3008c"), ("Orchid", "#b146c2"), ("Purple", "#8764b8"), ("Indigo", "#6b69d6"),
    ("Blue", "#0078d4"), ("Sky", "#4cc2ff"), ("Teal", "#00b7c3"), ("Sea green", "#00b294"),
    ("Green", "#10893e"), ("Lime", "#8cbd18"), ("Slate", "#68768a"), ("Light gray", "#c8c8c8"),
)
COLUMNS = 9
SIZE = 36


class Swatch(QAbstractButton):
    """Round colour sample; the chosen one has a white ring and a check mark."""

    def __init__(self, color: str, name: str = "", parent=None):
        super().__init__(parent)
        self.color = QColor(color).name()
        self.chosen = False
        self.setToolTip(name or self.color)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setFixedSize(SIZE, SIZE)

    def set_chosen(self, on: bool):
        if on != self.chosen:
            self.chosen = on
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        if self.chosen or self.underMouse():
            p.setPen(QPen(QColor(255, 255, 255, 235 if self.chosen else 110), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(r.adjusted(2, 2, -2, -2) if self.chosen else r)
        if self.chosen:
            c = QColor(self.color)
            ink = QColor("#141414" if c.lightnessF() > 0.6 else "#ffffff")
            pen = QPen(ink, 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            m = self.rect().center()
            p.drawPolyline([QPointF(m.x() - 5, m.y() + 0.5), QPointF(m.x() - 1.5, m.y() + 4), QPointF(m.x() + 5.5, m.y() - 3.5)])


class AccentPicker(QWidget):
    """The accent colour setting: the swatches of the palette, one more swatch for a custom colour, and a button
    that opens the system colour dialog."""
    accentPicked = Signal(str)   # "#rrggbb"

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 18)
        lay.setSpacing(16)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self._swatches: list[Swatch] = []
        for i, (name, color) in enumerate(PRESETS):
            s = Swatch(color, name)
            s.clicked.connect(lambda _=False, c=color: self.accentPicked.emit(c))
            grid.addWidget(s, i // COLUMNS, i % COLUMNS)
            self._swatches.append(s)
        self._custom = Swatch("#ffffff", "Custom colour")  # shown only while a colour from outside the palette is used
        self._custom.clicked.connect(lambda _=False: self.accentPicked.emit(self._custom.color))
        self._custom.hide()
        i = len(PRESETS)
        grid.addWidget(self._custom, i // COLUMNS, i % COLUMNS)
        grid.setColumnStretch(COLUMNS, 1)
        lay.addLayout(grid)
        pick = CapsuleButton("Custom colour\u2026", "secondary")
        pick.clicked.connect(self._choose)
        lay.addWidget(pick, 0, Qt.AlignLeft)
        self._current = theme.DEFAULT_ACCENT

    def set_accent(self, color: str):
        self._current = QColor(color).name()
        known = False
        for s in self._swatches:
            on = s.color == self._current
            s.set_chosen(on)
            known = known or on
        self._custom.setVisible(not known)
        if not known:
            self._custom.color = self._current
        self._custom.set_chosen(not known)
        self._custom.update()

    def _choose(self):
        c = QColorDialog.getColor(QColor(self._current), self.window(), "Accent colour")
        if c.isValid():
            self.accentPicked.emit(c.name())
