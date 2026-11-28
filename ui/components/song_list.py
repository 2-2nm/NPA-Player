import math
import time
import traceback

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QMenu, QPushButton,
                               QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from ui.components.animated_menu import AnimatedMenu
from ui.components.track_list_model import TrackListModel
from ui.rendering.cover_renderer import CoverRenderer
from ui import theme
from ui.shell.backdrop import paint_backdrop
from ui.components.smooth_scroll import SmoothListView

ROW_H = 46
COVER = 34
PAD = 12
FADE_H = 90  # height of the bottom fade in px
SORTS = {"added": "Date added", "title": "Title", "artist": "Artist", "album": "Album",
         "year": "Year", "genre": "Genre"}


def columns(w: int, extra: bool = False) -> dict:
    """Column x-positions (shared by header and rows). Without the extra column they are fractions of the row
    width. With it, QUALITY / PLAYS / TIME keep a fixed size at the right edge (so PLAYS stays next to the pill
    at any window size) and the other columns share the rest."""
    if extra:
        quality = w - 226
        return {"title": PAD + COVER + 12, "album": int(quality * 0.50), "genre": int(quality * 0.725),
                "year": int(quality * 0.89), "quality": quality, "extra_right": w - 12 - 62, "time_right": w - 12}
    return {"title": PAD + COVER + 12, "album": int(w * 0.43), "genre": int(w * 0.62), "year": int(w * 0.76),
            "quality": int(w * 0.83), "extra_right": w - 12 - 62, "time_right": w - 12}


class TrackDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_id = None
        self.playing = False    # the equalizer bars only move while music is playing
        self.cover_rect = None  # where the playing row's cover was last painted (viewport coords), for cheap repaints
        W = QFont.Weight
        self.f_title = theme.font(14, W.DemiBold)
        self.f_sub = theme.font(12)
        self.f_col = theme.font(13)
        self.f_pill = theme.font(11, W.DemiBold)

    def sizeHint(self, opt, index):
        return QSize(opt.rect.width(), ROW_H)

    def paint(self, p, opt, index):
        t = index.data(TrackListModel.TrackRole)
        r = opt.rect
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        playing = t.id == self.current_id
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        hover = bool(opt.state & QStyle.StateFlag.State_MouseOver)

        # Row background: accent tint for the playing row, subtle white for hover/selection
        if playing or selected or hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(90, 120, 255, 42) if playing else QColor(255, 255, 255, 28 if selected else 12))
            p.drawRoundedRect(QRectF(r).adjusted(0, 2, 0, -2), 14, 14)

        # Cover art
        cy = r.y() + (r.height() - COVER) // 2
        p.drawPixmap(r.x() + PAD, cy, CoverRenderer.pixmap(t, COVER, 8))

        # "Now playing" equalizer bars drawn over the cover
        if playing:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawRoundedRect(QRectF(r.x() + PAD, cy, COVER, COVER), 8, 8)
            p.setBrush(QColor("#ffffff"))
            self.cover_rect = QRect(r.x() + PAD, cy, COVER, COVER)
            now = time.monotonic()
            for i, still in enumerate((8, 15, 11)):
                if self.playing:  # each bar bounces at its own pace, so it never looks like a loop of one shape
                    wave = 0.5 + 0.5 * math.sin(now * (5.2 + 1.7 * i) + i * 2.1)
                    h = 4 + 12 * wave
                else:
                    h = still
                p.drawRoundedRect(QRectF(r.x() + PAD + 10 + i * 5, cy + (COVER + 15) / 2 - h, 3, h), 1.5, 1.5)

        extra = index.data(TrackListModel.ExtraRole)
        c = columns(r.width(), bool(index.model().extra_title))
        x0, y0 = r.x(), r.y()

        # Title + artist
        maxw = c["album"] - c["title"] - 16
        p.setFont(self.f_title)
        p.setPen(QColor(theme.ACCENT if playing else theme.TEXT))
        p.drawText(QRectF(x0 + c["title"], y0 + 6, maxw, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(t.title, Qt.ElideRight, maxw))
        p.setFont(self.f_sub)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(x0 + c["title"], y0 + 25, maxw, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(t.artist, Qt.ElideRight, maxw))

        # Album, genre, year, duration
        p.setFont(self.f_col)
        p.setPen(QColor("#c4c9de"))
        aw = c["genre"] - c["album"] - 16
        p.drawText(QRectF(x0 + c["album"], y0, aw, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(t.album, Qt.ElideRight, aw))
        gw = c["year"] - c["genre"] - 16
        p.drawText(QRectF(x0 + c["genre"], y0, gw, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(t.genre, Qt.ElideRight, gw))
        p.drawText(QRectF(x0 + c["year"], y0, 60, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   str(t.year) if t.year else "")
        p.drawText(QRectF(x0, y0, c["time_right"], r.height()), Qt.AlignRight | Qt.AlignVCenter,
                   theme.fmt_time(t.duration * 1000))
        if extra:  # play count / last played, right before TIME
            p.drawText(QRectF(x0, y0, c["extra_right"], r.height()), Qt.AlignRight | Qt.AlignVCenter, extra)

        # Quality pill (MP3 / FLAC / ...)
        p.setFont(self.f_pill)
        pw = p.fontMetrics().horizontalAdvance(t.fmt) + 20
        pill = QRectF(x0 + c["quality"], y0 + (r.height() - 24) / 2, pw, 24)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 24))
        p.drawRoundedRect(pill, 7, 7)
        p.setPen(QColor("#d6dbf2"))
        p.drawText(pill, Qt.AlignCenter, t.fmt)
        p.restore()


class ColumnHeader(QWidget):
    def __init__(self, model: TrackListModel, parent=None):
        super().__init__(parent)
        self._model = model
        self.setFixedHeight(34)
        model.extraChanged.connect(self.update)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setFont(theme.font(11, QFont.Weight.Medium, 1.6))
        p.setPen(QColor(theme.DIM))
        title = self._model.extra_title
        c = columns(self.width(), bool(title))
        h = self.height() - 4
        for key, text in (("title", "TITLE"), ("album", "ALBUM"), ("genre", "GENRE"), ("year", "YEAR"), ("quality", "QUALITY")):
            p.drawText(QRectF(c[key], 0, 120, h), Qt.AlignLeft | Qt.AlignVCenter, text)
        if title:
            p.drawText(QRectF(0, 0, c["extra_right"], h), Qt.AlignRight | Qt.AlignVCenter, title)
        p.drawText(QRectF(0, 0, c["time_right"], h), Qt.AlignRight | Qt.AlignVCenter, "TIME")
        # Bottom divider line
        p.setPen(QColor(255, 255, 255, 22))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class FadeOverlay(QWidget):
    """Repaints the real window backdrop with an alpha that grows downward,
    so the song rows dissolve into the background without a visible color band."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        w, h = self.width(), self.height()
        central = self.window().centralWidget() if hasattr(self.window(), "centralWidget") else None
        if central is None or w <= 0 or h <= 0:
            return
        dpr = self.devicePixelRatioF()

        # Render the matching slice of the backdrop into an offscreen image
        img = QImage(max(1, int(w * dpr)), max(1, int(h * dpr)), QImage.Format_ARGB32_Premultiplied)
        if img.isNull():
            return
        img.setDevicePixelRatio(dpr)
        img.fill(0)
        q = QPainter(img)
        try:
            off = self.mapTo(central, QPoint(0, 0))
            q.translate(-off.x(), -off.y())
            if hasattr(central, "paint_into"):
                central.paint_into(q)  # exactly what the window paints behind it, tint and pattern included
            else:
                paint_backdrop(q, central.width(), central.height())
            q.resetTransform()

            # Multiply by a vertical alpha ramp: transparent at the top, opaque at the bottom
            q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            g = QLinearGradient(0, 0, 0, h)
            g.setColorAt(0.0, QColor(0, 0, 0, 0))
            g.setColorAt(0.55, QColor(0, 0, 0, 150))
            g.setColorAt(1.0, QColor(0, 0, 0, 255))
            q.fillRect(QRectF(0, 0, w, h), g)
        except Exception:
            traceback.print_exc()
        finally:
            q.end()

        p = QPainter(self)
        try:
            p.drawImage(0, 0, img)
        finally:
            p.end()


class SongList(QWidget):
    rowActivated = Signal(int)
    sortPicked = Signal(str)  # the user chose a sort in the menu (not when it is set from code)

    def __init__(self, model: TrackListModel, sorts: dict | None = None, heading: str = "All songs", parent=None):
        super().__init__(parent)
        self.model = model
        self.sorts = sorts or SORTS
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Section title + Sort / Filter / Select buttons
        top = QHBoxLayout()
        title = QLabel(heading)
        title.setFont(theme.font(22, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{theme.TEXT};")
        top.addWidget(title)
        top.addStretch(1)
        self.sort_btn = QPushButton("Sort: " + next(iter(self.sorts.values())))
        self.filter_btn = QPushButton("Filter")
        self.select_btn = QPushButton("Select")
        self.select_btn.setCheckable(True)
        for b in (self.sort_btn, self.filter_btn, self.select_btn):
            b.setObjectName("pill")
            b.setFixedHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            top.addWidget(b)
        lay.addLayout(top)
        lay.addWidget(ColumnHeader(model))

        # List view (scrollbar hidden so row widths line up with the column header)
        # Wheel glides like NPI Gallery; the list scrolls FADE_H past its last row so the fade never hides it
        self.view = SmoothListView(bottom_padding=FADE_H)
        self.view.setModel(model)
        self.delegate = TrackDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        self._eq_timer = QTimer(self, interval=40)  # drives the equalizer bars on the playing row
        self._eq_timer.timeout.connect(self._tick_eq)
        self.view.setUniformItemSizes(True)
        self.view.setMouseTracking(True)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # One click plays a song. In Select mode a click selects the row instead, and a double click plays it.
        self.view.clicked.connect(self._on_clicked)
        self.view.doubleClicked.connect(self._on_double_clicked)
        lay.addWidget(self.view, 1)

        # Fade sits on top of the list's bottom edge
        self.fade = FadeOverlay(self)
        self.fade.raise_()

        # Sort menu and Filter menu: drop-downs in the style of NPI Gallery, opened centred under their button.
        # Both are rebuilt each time they open, so the check marks and the formats are always current.
        self.sort_menu = AnimatedMenu(self)
        self.sort_menu.centre_on(self.sort_btn)
        self.sort_menu.aboutToShow.connect(self._build_sort_menu)
        self.sort_btn.setMenu(self.sort_menu)
        self.filter_menu = AnimatedMenu(self)
        self.filter_menu.centre_on(self.filter_btn)
        self.filter_menu.aboutToShow.connect(self._build_filter_menu)
        self.filter_btn.setMenu(self.filter_menu)

        self.select_btn.toggled.connect(self._toggle_select)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Keep the fade pinned to the bottom of the list view
        v = self.view.geometry()
        self.fade.setGeometry(v.x(), v.bottom() - FADE_H + 1, v.width(), FADE_H)

    def reset(self, sort_key: str):
        """Back to a clean view: no filter, no selection, the given sort."""
        self.select_btn.setChecked(False)
        self.model.set_query("")
        self.model.set_formats(set())
        self.filter_btn.setText("Filter")
        self._set_sort(sort_key)

    def set_sort(self, key: str):
        """Sort from code (e.g. the one remembered from the last session); unknown keys are ignored."""
        if key in self.sorts:
            self._set_sort(key)

    def _pick_sort(self, key: str):
        self._set_sort(key)
        self.sortPicked.emit(key)

    def _set_sort(self, key: str):
        self._sort_key = key
        self.model.set_sort(key)
        self.sort_btn.setText(f"Sort: {self.sorts[key]}")

    def _build_sort_menu(self):
        self.sort_menu.clear()
        current = getattr(self, "_sort_key", next(iter(self.sorts)))
        for key, label in self.sorts.items():
            self.sort_menu.add_choice(label, key == current, lambda k=key: self._pick_sort(k))

    def _build_filter_menu(self):
        menu = self.filter_menu
        menu.clear()
        formats = self.model.available_formats()
        for fmt in formats:
            on = fmt in self.model.formats
            menu.add_choice(fmt, on, lambda f=fmt, on=on: self._toggle_format(f, not on))
        if not formats:
            menu.addAction("No songs yet").setEnabled(False)
        elif self.model.formats:
            menu.addSeparator()
            menu.addAction("Clear filter").triggered.connect(lambda _=False: self._clear_filter())

    def _clear_filter(self):
        self.model.set_formats(set())
        self.filter_btn.setText("Filter")

    def _toggle_format(self, fmt: str, on: bool):
        s = set(self.model.formats)
        s.add(fmt) if on else s.discard(fmt)
        self.model.set_formats(s)
        self.filter_btn.setText(f"Filter ({len(s)})" if s else "Filter")

    def _on_clicked(self, index):
        if not self.select_btn.isChecked():
            self.rowActivated.emit(index.row())

    def _on_double_clicked(self, index):
        if self.select_btn.isChecked():
            self.rowActivated.emit(index.row())

    def _toggle_select(self, on: bool):
        self.view.setSelectionMode(QAbstractItemView.MultiSelection if on else QAbstractItemView.NoSelection)
        if not on:
            self.view.clearSelection()

    def set_playing(self, playing: bool):
        """Equalizer bars on the current row move while music plays and freeze when it is paused."""
        self.delegate.playing = playing
        if playing:
            self._eq_timer.start()
        else:
            self._eq_timer.stop()
        self.view.viewport().update()

    def _tick_eq(self):
        # Repaint only the cover of the playing row. The delegate re-arms cover_rect whenever that row is painted,
        # so nothing is repainted (and the timer costs nothing) while the row is scrolled out of view.
        rect, self.delegate.cover_rect = self.delegate.cover_rect, None
        if rect is not None:
            self.view.viewport().update(rect)

    def set_current(self, track_id):
        """Highlight the row of the currently playing track."""
        self.delegate.current_id = track_id
        self.view.viewport().update()