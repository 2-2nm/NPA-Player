from PySide6.QtCore import QAbstractListModel, QModelIndex, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QStackedWidget, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from ui.rendering.cover_renderer import CoverRenderer
from ui import theme
from ui.pages.now_playing import audio_info
from ui.pages.now_playing.lyrics import LyricsView
from ui.components.smooth_scroll import SmoothListView
from ui.components.common import Card
from ui.components.fade_stack import FadeStack
from ui.components.segmented import SegmentedTabs

_SCROLL_STYLE = """
QListView{background:transparent;border:none;outline:none;}
QScrollBar:vertical{background:transparent;width:8px;margin:0;}
QScrollBar::handle:vertical{background:rgba(255,255,255,0.18);border-radius:4px;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}
"""


def _caps(text: str, color: str = theme.DIM) -> QLabel:
    lab = QLabel(text)
    lab.setFont(theme.font(11, QFont.Weight.Medium, 1.6))
    lab.setStyleSheet(f"color:{color};")
    return lab


ROW_H = 62  # 60 px row + 2 px gap


class QueueModel(QAbstractListModel):
    """The whole queue as a list model, so thousands of tracks cost nothing (rows are only painted when visible)."""
    TrackRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._tracks)

    def data(self, index, role=Qt.DisplayRole):
        if role == self.TrackRole and index.isValid():
            return self._tracks[index.row()]
        return None

    def set_tracks(self, tracks):
        self.beginResetModel()
        self._tracks = list(tracks)
        self.endResetModel()


class QueueDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_row = -1

    def sizeHint(self, opt, index):
        return QSize(opt.rect.width(), ROW_H)

    def paint(self, p, opt, index):
        track = index.data(QueueModel.TrackRole)
        current = index.row() == self.current_row
        r = opt.rect.adjusted(0, 1, 0, -1)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        if current or (opt.state & QStyle.StateFlag.State_MouseOver):
            p.setPen(Qt.NoPen)
            p.setBrush(theme.accent_color(40) if current else QColor(255, 255, 255, 16))
            p.drawRoundedRect(QRectF(r), 14, 14)
        p.drawPixmap(r.x() + 8, r.y() + 8, CoverRenderer.pixmap(track, 44, 10))
        right = r.right() - 14
        p.setFont(theme.font(12))
        p.setPen(QColor(theme.DIM))
        dur = theme.fmt_time(track.duration * 1000)
        dw = p.fontMetrics().horizontalAdvance(dur)
        p.drawText(QRectF(right - dw, r.y(), dw, r.height()), Qt.AlignRight | Qt.AlignVCenter, dur)
        tw = int(right - dw - 12 - 64)
        p.setFont(theme.font(14, QFont.Weight.DemiBold if current else QFont.Weight.Medium))
        p.setPen(QColor(theme.ACCENT if current else theme.TEXT))
        p.drawText(QRectF(r.x() + 64, r.y() + 9, tw, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(track.title, Qt.ElideRight, tw))
        p.setFont(theme.font(12))
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(r.x() + 64, r.y() + 31, tw, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(track.artist, Qt.ElideRight, tw))
        p.restore()


class QueueView(QWidget):
    """Every track in the queue (already played ones included), scrollable, with the current one highlighted."""
    playIndex = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.head = _caps("TRACKS")
        lay.addWidget(self.head)

        self._ids: tuple = ()
        self._index = -1
        self.model = QueueModel(self)
        self.view = SmoothListView()  # same wheel glide as the Library song list
        self.view.setModel(self.model)
        self.delegate = QueueDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        self.view.setUniformItemSizes(True)
        self.view.setMouseTracking(True)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setStyleSheet(_SCROLL_STYLE)
        self.view.clicked.connect(lambda i: self.playIndex.emit(i.row()))
        lay.addWidget(self.view, 1)

    def set_queue(self, queue, index: int):
        self._index = index
        self.delegate.current_row = index
        if index < 0 or not queue:
            self.head.setText("QUEUE IS EMPTY")
        else:
            self.head.setText(f"TRACKS · {len(queue)} SONGS")
        ids = tuple(t.id for t in queue)
        if ids != self._ids:  # a different queue (new list, shuffle): rebuild and show the current track
            self._ids = ids
            self.model.set_tracks(queue)
            QTimer.singleShot(0, lambda: self._center_current(animate=False))
        else:  # same queue, another track: follow it only when it has scrolled out of view
            self.view.viewport().update()
            if not self._current_visible():
                self._center_current(animate=self.isVisible())

    def _current_visible(self) -> bool:
        top = self._index * ROW_H - self.view.verticalScrollBar().value()
        return self._index < 0 or (0 <= top and top + ROW_H <= self.view.viewport().height())

    def _center_current(self, animate: bool):
        if self._index < 0:
            return
        self.view.doItemsLayout()  # make sure the scroll range is up to date
        bar = self.view.verticalScrollBar()
        target = self._index * ROW_H - (self.view.viewport().height() - ROW_H) // 2
        if animate:
            self.view.scroll_to(target)
        else:
            self.view._glide.stop()
            bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, lambda: self._center_current(animate=False))  # sizes are final once shown


class InfoView(QWidget):
    FIELDS = ("TITLE", "ARTIST", "ALBUM", "FORMAT", "LENGTH", "YEAR", "FILE")

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(2)
        self._values: dict[str, QLabel] = {}
        for name in self.FIELDS:
            lay.addWidget(_caps(name))
            val = QLabel("–")
            val.setFont(theme.font(14))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setStyleSheet(f"color:{theme.TEXT};padding-bottom:10px;")
            self._values[name] = val
            lay.addWidget(val)
        lay.addStretch(1)

    def set_track(self, t):
        vals = {"TITLE": t.title, "ARTIST": t.artist, "ALBUM": t.album, "FORMAT": audio_info.quality(t),
                "LENGTH": theme.fmt_time(t.duration * 1000), "YEAR": str(t.year) if t.year else "", "FILE": t.path}
        for k, v in vals.items():
            self._values[k].setText(v if k == "YEAR" else (v or "–"))  # no release year: left empty


class SidePanel(Card):
    """Right panel: Tracks / Lyrics / Info."""
    seekMs = Signal(int)
    playIndex = Signal(int)
    tabChanged = Signal(int)  # only when the user picks a tab, not when it is set from code
    TAB_QUEUE, TAB_LYRICS, TAB_INFO = 0, 1, 2
    radius = 26

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(14)

        self.seg = SegmentedTabs(("Tracks", "Lyrics", "Info"))  # same look as the Library tabs, the highlight glides
        lay.addWidget(self.seg)

        self.queue, self.lyrics, self.info = QueueView(), LyricsView(), InfoView()
        self.stack = FadeStack()
        for w in (self.queue, self.lyrics, self.info):
            self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)

        self.seg.idClicked.connect(self.stack.fade_to)  # tabs cross-fade
        self.seg.idClicked.connect(self.tabChanged)
        self.queue.playIndex.connect(self.playIndex)
        self.lyrics.seekRequested.connect(self.seekMs)
        self.set_tab(self.TAB_QUEUE)  # default tab: Tracks

    def set_tab(self, i: int):
        self.seg.set_current(i)  # from code: the highlight jumps, it only glides when the user clicks
        self.stack.setCurrentIndex(i)

    def set_track(self, t):
        self._lyrics_track = t
        self.lyrics.set_lines(audio_info.load_lyrics(t.path, t.title, t.artist))
        self.info.set_track(t)

    def reload_lyrics(self):
        """The lyrics folders changed: look again for the lyrics of the song on screen."""
        t = getattr(self, "_lyrics_track", None)
        if t is not None:
            self.lyrics.set_lines(audio_info.load_lyrics(t.path, t.title, t.artist))

    def set_queue(self, queue, index: int):
        self.queue.set_queue(queue, index)

    def set_position(self, ms: int):
        self.lyrics.set_position(ms)