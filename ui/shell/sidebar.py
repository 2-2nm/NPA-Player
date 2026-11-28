from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget

from ui import theme
from ui.icons import draw_icon
from ui.logo import paint_logo
from ui.components.common import Card, ElidedLabel
from ui.shell.navigation import Page

COLLAPSED_W = 72
LABELS_MIN_W = 150  # labels, counts and the app title only show above this panel width


class Logo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setProperty("dragRegion", True)

    def paintEvent(self, e):
        p = QPainter(self)
        paint_logo(p, QRectF(0, 0, 40, 40))


class NavItem(QAbstractButton):
    def __init__(self, icon: str, text: str, checkable=True, parent=None):
        super().__init__(parent)
        self.icon_name, self.label, self.count = icon, text, ""
        self.setFixedHeight(40)
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def set_count(self, n: int):
        self.count = f"{n:,}" if n else ""
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        active, hover = self.isChecked(), self.underMouse()
        if active or hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 34 if active else 16))
            p.drawRoundedRect(QRectF(self.rect()), 12, 12)
        color = "#ffffff" if (active or hover) else theme.MUTED
        draw_icon(p, self.icon_name, QRectF(12, (self.height() - 20) / 2, 20, 20), color)
        if self.width() <= 120:
            return  # collapsed: icon only
        right = self.width() - 14
        if self.count:
            p.setFont(theme.font(12))
            p.setPen(QColor(theme.DIM))
            cw = p.fontMetrics().horizontalAdvance(self.count)
            p.drawText(QRectF(right - cw, 0, cw, self.height()), Qt.AlignRight | Qt.AlignVCenter, self.count)
            right -= cw + 8
        p.setFont(theme.font(14, QFont.Weight.DemiBold if active else QFont.Weight.Medium))
        p.setPen(QColor(color))
        w = max(0, right - 46)
        p.drawText(QRectF(46, 0, w, self.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(self.label, Qt.ElideRight, int(w)))


class SectionLabel(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setFixedHeight(30)

    def paintEvent(self, e):
        p = QPainter(self)
        if self.width() > 120:
            p.setFont(theme.font(11, QFont.Weight.Medium, 1.6))
            p.setPen(QColor(theme.DIM))
            p.drawText(QRectF(14, 6, self.width() - 14, 20), Qt.AlignLeft | Qt.AlignVCenter, self._text)
        else:
            p.setPen(QColor(255, 255, 255, 30))
            p.drawLine(12, self.height() // 2, self.width() - 12, self.height() // 2)


class Sidebar(Card):
    pageSelected = Signal(int)
    radius = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(COLLAPSED_W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(4)

        # Logo + app name (this row doubles as a window drag area)
        head = QWidget()
        head.setProperty("dragRegion", True)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)
        hl.addWidget(Logo())
        self.title = ElidedLabel("MusicNook", 17, QFont.Weight.Bold)
        hl.addWidget(self.title, 1)
        lay.addWidget(head)

        lay.addSpacing(10)

        # Main navigation (exclusive)
        self._group = QButtonGroup(self)
        self.nav_library = NavItem("grid", "Library")
        self.nav_now = NavItem("wave", "Player")
        self.nav_playlists = NavItem("playlist", "Playlists")
        for i, item in enumerate((self.nav_library, self.nav_now, self.nav_playlists)):
            self._group.addButton(item, i)
            lay.addWidget(item)
        self.nav_library.setChecked(True)
        self._group.idClicked.connect(self.pageSelected)

        lay.addSpacing(10)
        lay.addWidget(SectionLabel("THIS PC"))
        self.nav_folders = NavItem("plus", "Folders")
        self._group.addButton(self.nav_folders, Page.FOLDERS)
        lay.addWidget(self.nav_folders)

        lay.addStretch(1)
        self.nav_settings = NavItem("gear", "Settings")
        self._group.addButton(self.nav_settings, Page.SETTINGS)
        lay.addWidget(self.nav_settings)
        self._sync_labels()

    def set_counts(self, library: int, playlists: int):
        self.nav_library.set_count(library)
        self.nav_playlists.set_count(playlists)

    def _sync_labels(self):
        self.title.setVisible(self.width() > LABELS_MIN_W)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._sync_labels()