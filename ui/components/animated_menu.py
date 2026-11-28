"""Drop-down menu in the style of NPI Gallery: frosted (blurred window content behind it), rounded, opening centred
under its button and unfolding downward with a soft landing. Ported from npigallery/gui/common/motion.py
(AnimatedMenu) and frost.py, trimmed to what this app needs.

Use it like a QMenu. For a list of choices, add_choice(text, checked, slot) gives every row the same grid, with a
check mark in front of the chosen ones (the other rows keep the blank space)."""
import time

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPointF, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QCursor, QGuiApplication, QIcon, QImage, QMouseEvent, QPainter, QPainterPath,
                           QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QMenu, QPushButton, QWidget

MENU_RADIUS = 14
MENU_DURATION = 200      # ms
MENU_SLIDE = 8           # px, how far the content eases in
MENU_EDGE = 8            # px kept free between the menu and the window edge
GAP = 6                  # px between the button and the menu
BLUR_RADIUS = 14         # logical px: "a little" blur, the content stays recognisable
EDGE_MARGIN = 20         # extra px grabbed around the menu so the blur does not darken its edges
_HOVER_CANCEL_PX = 4
_MODIFIERS = (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_AltGr)

MENU_STYLE = """
QMenu[acrylic="true"]{background:rgba(22,24,44,0.72);color:#f3f5ff;border:1px solid rgba(255,255,255,0.12);
  border-radius:14px;padding:6px;}
QMenu[acrylic="true"]::item{padding:8px 20px 8px 8px;border-radius:8px;margin:1px 2px;}
QMenu[acrylic="true"]::item:selected{background:rgba(255,255,255,0.11);}
QMenu[acrylic="true"]::item:disabled{color:#6b7190;}
QMenu[acrylic="true"]::icon{padding-left:10px;}
QMenu[acrylic="true"]::separator{height:1px;background:rgba(255,255,255,0.10);margin:5px 8px;}
QMenu[acrylic="true"]::indicator{width:0px;height:0px;image:none;}
"""


def _decelerate() -> QEasingCurve:
    """Fluent "decelerate": fast start, soft landing."""
    c = QEasingCurve(QEasingCurve.Type.BezierSpline)
    c.addCubicBezierSegment(QPointF(0.1, 0.9), QPointF(0.2, 1.0), QPointF(1.0, 1.0))
    return c


class _FrameAnimation(QObject):
    """Animation driven by a timer at the screen's refresh rate (smoother than QVariantAnimation on a popup)."""
    valueChanged = Signal(float)
    finished = Signal()

    def __init__(self, parent, duration: int):
        super().__init__(parent)
        self._duration = max(1, int(duration))
        self._curve = _decelerate()
        self._started = 0.0
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)

    def start(self):
        screen = QGuiApplication.primaryScreen()
        rate = float(screen.refreshRate()) if screen is not None else 60.0
        if rate < 30.0:
            rate = 60.0
        self._started = time.perf_counter()
        self._timer.start(max(4, int(round(1000.0 / min(rate, 240.0)))))

    def stop(self):
        self._timer.stop()

    def _tick(self):
        t = (time.perf_counter() - self._started) * 1000.0 / self._duration
        if t >= 1.0:
            self._timer.stop()
            self.valueChanged.emit(1.0)
            self.finished.emit()
            return
        self.valueChanged.emit(float(self._curve.valueForProgress(t)))


# ---------- frosted backdrop ----------
def _blur(image: QImage, radius: float) -> QImage:
    """Cheap, smooth blur: average the picture down a few steps, then scale it back up."""
    w, h = image.width(), image.height()
    step = max(2, round(radius / 2))
    smooth = Qt.TransformationMode.SmoothTransformation
    ignore = Qt.AspectRatioMode.IgnoreAspectRatio
    small = image.scaled(max(1, w // step), max(1, h // step), ignore, smooth)
    smaller = small.scaled(max(1, small.width() // 2), max(1, small.height() // 2), ignore, smooth)
    softer = smaller.scaled(small.size(), ignore, smooth)
    return softer.scaled(w, h, ignore, smooth)


def frosted_backdrop(window: QWidget, global_top_left: QPoint, size: QSize) -> QPixmap | None:
    """The blurred part of `window` under a popup of `size` at `global_top_left` (None when nothing is behind it)."""
    if window is None or not window.isVisible() or size.isEmpty():
        return None
    origin = window.mapFromGlobal(global_top_left)
    wanted = QRect(origin, size).adjusted(-EDGE_MARGIN, -EDGE_MARGIN, EDGE_MARGIN, EDGE_MARGIN)
    source = wanted.intersected(window.rect())
    if source.isEmpty():
        return None
    grabbed = window.grab(source)
    if grabbed.isNull():
        return None
    ratio = grabbed.devicePixelRatio()
    image = grabbed.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    blurred = _blur(image, BLUR_RADIUS * ratio)
    blurred.setDevicePixelRatio(ratio)
    result = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
    result.setDevicePixelRatio(ratio)
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    p.drawImage(QPointF(source.left() - origin.x(), source.top() - origin.y()), blurred)
    p.end()
    return result


def _top_level_window(widget: QWidget | None) -> QWidget | None:
    cur = widget
    while cur is not None:
        if cur.isWindow() and not (cur.windowFlags() & Qt.WindowType.Popup):
            return cur
        cur = cur.parentWidget()
    return None


def _check_icon(checked: bool) -> QIcon:
    """A white check mark, or the same space left blank, so chosen and other rows line up."""
    ratio = 2.0
    px = QPixmap(int(16 * ratio), int(16 * ratio))
    px.setDevicePixelRatio(ratio)
    px.fill(Qt.GlobalColor.transparent)
    if checked:
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"), 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([QPointF(3.2, 8.4), QPointF(6.6, 11.6), QPointF(12.8, 4.8)])
        p.end()
    return QIcon(px)


class AnimatedMenu(QMenu):
    """Popup menu that unfolds from its top edge (from the bottom edge when it had to open upward) without moving
    its native window, over a blurred picture of the app window."""

    def __init__(self, parent=None, duration: int = MENU_DURATION, slide: int = MENU_SLIDE):
        super().__init__(parent)
        self._duration, self._slide = max(0, int(duration)), max(0, int(slide))
        self.setProperty("acrylic", True)
        self.setStyleSheet(MENU_STYLE)
        # Frameless + translucent so the rounded corners are real
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._animation: _FrameAnimation | None = None
        self._animating = False
        self._upward = False
        self._progress = 1.0
        self._snapshot: QPixmap | None = None
        self._hidden_children: list[QWidget] = []
        self._open_cursor_pos: QPoint | None = None
        self._centre_widget: QWidget | None = None
        self._backdrop: QPixmap | None = None

    # ---------- content ----------
    def add_choice(self, text: str, checked: bool, slot) -> QAction:
        """A row with a check mark in front when `checked`; `slot()` runs when it is picked."""
        action = self.addAction(_check_icon(checked), text)
        action.triggered.connect(lambda _=False: slot())
        return action

    def centre_on(self, widget: QWidget | None):
        """Open the menu horizontally centred under `widget` (a button) instead of left aligned with it."""
        self._centre_widget = widget

    # ---------- showing ----------
    def setVisible(self, visible: bool):
        if not visible:
            self._stop_animation()
            super().setVisible(False)
            return
        self._stop_animation()
        self.ensurePolished()
        self.adjustSize()
        end, self._upward = self._resolve_placement(self.pos(), self.size(), QCursor.pos())
        self.move(end)
        self._backdrop = self._frosted(end)
        if self._duration <= 0:
            super().setVisible(True)
            return
        # Render the finished menu once, then reveal it stepwise: the native window never moves or changes alpha.
        self._snapshot = self.grab()
        self._hidden_children = [c for c in self.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
                                 if not c.isHidden()]
        for c in self._hidden_children:
            c.hide()
        self._progress = 0.0
        self._animating = True
        self._open_cursor_pos = QCursor.pos()
        super().setVisible(True)
        anim = _FrameAnimation(self, self._duration)
        anim.valueChanged.connect(self._on_step)
        anim.finished.connect(self._finish_animation)
        self._animation = anim
        anim.start()

    def _frosted(self, top_left: QPoint) -> QPixmap | None:
        anchor = self.parentWidget()
        while isinstance(anchor, QMenu):  # a submenu is blurred over the window, like its parent
            anchor = anchor.parentWidget()
        window = anchor.window() if anchor is not None else None
        try:
            return frosted_backdrop(window, top_left, self.size())
        except Exception:
            return None

    def _paint_backdrop(self):
        if self._backdrop is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        shape = QPainterPath()
        shape.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), MENU_RADIUS - 1, MENU_RADIUS - 1)
        p.setClipPath(shape)
        p.drawPixmap(0, 0, self._backdrop)

    def _on_step(self, value: float):
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    def _finish_animation(self):
        if not self._animating and self._animation is None:
            return
        self._stop_animation()
        self.update()

    def _stop_animation(self):
        anim, self._animation = self._animation, None
        if anim is not None:
            anim.stop()
            anim.deleteLater()
        self._animating = False
        self._progress = 1.0
        self._snapshot = None
        for c in self._hidden_children:
            c.show()
        self._hidden_children.clear()

    def paintEvent(self, event):
        if self._animating and self._snapshot is not None:
            p = QPainter(self)
            # Clear the translucent backing store, so earlier frames never leave a ghost
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            h, w = self.height(), self.width()
            visible = max(1, round(h * self._progress))
            drift = round(min(h * 0.3, self._slide * 4) * (1.0 - self._progress))
            if self._upward:
                p.setClipRect(0, h - visible, w, visible)
                p.drawPixmap(0, drift, self._snapshot)
            else:
                p.setClipRect(0, 0, w, visible)
                p.drawPixmap(0, -drift, self._snapshot)
            return
        self._paint_backdrop()  # under the menu's own translucent background
        super().paintEvent(event)

    def mouseMoveEvent(self, event):
        if self._animating:
            moved = (self._open_cursor_pos is not None and
                     (event.globalPosition().toPoint() - self._open_cursor_pos).manhattanLength() >= _HOVER_CANCEL_PX)
            if moved:
                self._finish_animation()
            else:
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if self._animating:  # a click while unfolding finishes it and goes to the row under the pointer
            gp = event.globalPosition().toPoint()
            self._finish_animation()
            target = self.childAt(self.mapFromGlobal(gp))
            if target is not None and target is not self:
                fwd = QMouseEvent(event.type(), QPointF(target.mapFromGlobal(gp)), event.globalPosition(),
                                  event.button(), event.buttons(), event.modifiers())
                QApplication.sendEvent(target, fwd)
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self._animating:
            self._finish_animation()
        super().keyPressEvent(event)

    def _resolve_placement(self, natural: QPoint, size: QSize, pointer: QPoint) -> tuple[QPoint, bool]:
        """Final top-left of the menu and whether it grows upward. Kept inside the app window and the screen."""
        menu_size = size if size is not None and size.isValid() else self.size()
        width, height = menu_size.width(), menu_size.height()
        x, y = natural.x(), natural.y()
        centre = self._centre_widget
        if centre is not None and centre.isVisible():
            x = centre.mapToGlobal(QPoint(centre.width() // 2, 0)).x() - width // 2
            below = centre.mapToGlobal(QPoint(0, centre.height())).y()
            if y >= below - 2:  # opened downward: leave a small gap under the button
                y = below + GAP
        window = _top_level_window(self.parentWidget())
        if window is not None and window.isVisible():
            b = window.frameGeometry().adjusted(MENU_EDGE, MENU_EDGE, -MENU_EDGE, -MENU_EDGE)
            if centre is not None and y + height - 1 > b.bottom():  # no room below the button: above it
                above = centre.mapToGlobal(QPoint(0, 0)).y() - GAP - height
                if above >= b.top():
                    y = above
            x = max(b.left(), min(x, b.right() - width + 1))
            y = max(b.top(), min(y, b.bottom() - height + 1))
        screen = QGuiApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        if screen is not None:
            a = screen.availableGeometry().adjusted(4, 4, -4, -4)
            x = max(a.left(), min(x, a.right() - width + 1))
            y = max(a.top(), min(y, a.bottom() - height + 1))
        upward = centre is not None and centre.isVisible() and y + height <= centre.mapToGlobal(QPoint(0, 0)).y() + 1
        return QPoint(x, y), upward

    def hideEvent(self, event):
        self._stop_animation()
        self._backdrop = None
        super().hideEvent(event)