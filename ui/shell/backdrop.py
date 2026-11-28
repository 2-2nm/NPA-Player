from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from ui import theme

# Where the cover-colour glow sits on each page. Every page has its own pattern, and paint_backdrop blends them
# with weights, so changing page glides from one pattern to the next.
#   main glow:   centre x, centre y (fractions of the window), radius x (fraction of w), radius y (fraction of h),
#                alpha; radius None = round, 0.55 * max(w, h)
#   second hue:  centre x, centre y, radius (fraction of max(w, h)), alpha
LIBRARY, PLAYER, PLAYLISTS, COLLECTION, FOLDERS, SETTINGS = 0, 1, 2, 3, 4, 5  # pattern indices (the page numbers of the main window)
PATTERNS = (
    ((0.38, 0.17, 0.62, 0.42, 140), (0.92, 0.12, 0.30, 80)),   # Library: wide, top, next to "Continue listening"
    ((0.30, 0.40, None, None, 150), (0.85, 0.95, 0.40, 90)),   # Player: round spotlight in the middle
    ((0.15, 0.85, 0.62, 0.42, 140), (0.92, 0.10, 0.26, 80)),   # Playlists: wide, bottom left
    ((0.18, 0.14, 0.50, 0.34, 150), (0.95, 0.35, 0.28, 80)),   # one playlist: behind the header, top left
    ((0.30, 0.22, 0.58, 0.38, 140), (0.90, 0.88, 0.30, 80)),   # Folders: top left, a second glow bottom right
    ((0.72, 0.16, 0.55, 0.36, 130), (0.08, 0.92, 0.30, 70)),   # Settings: top right, a second glow bottom left
)


def _mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _glow(p, cx, cy, rx, ry, color: QColor, alpha: float, w: int, h: int):
    """Elliptical radial glow: strongest in the centre, fully transparent at the edge."""
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    p.save()
    p.translate(cx, cy)
    p.scale(1.0, ry / rx)  # a circle squashed into an ellipse
    g = QRadialGradient(0, 0, rx)
    g.setColorAt(0, c)
    c.setAlpha(0)
    g.setColorAt(1, c)
    p.fillRect(QRectF(-cx, -cy * rx / ry, w, h * rx / ry), g)
    p.restore()


def _weights(mode) -> list:
    """`mode` is a list of one weight per pattern, or (older form) 0 = Library .. 1 = player."""
    if isinstance(mode, (int, float)):
        m = min(1.0, max(0.0, float(mode)))
        return [1.0 - m, m, 0.0, 0.0]
    return list(mode)


def _blend(weights, w: int, h: int):
    """Weighted mix of all patterns in pixels: (cx, cy, rx, ry, alpha), (cx2, cy2, r2, alpha2)."""
    total = sum(weights) or 1.0
    big = max(w, h) * 0.55
    a = [0.0] * 5
    b = [0.0] * 4
    for k, pat in zip(weights, PATTERNS):
        if k <= 0:
            continue
        k /= total
        (x, y, rx, ry, al), (x2, y2, r2, al2) = pat
        main = (x * w, y * h, big if rx is None else rx * w, big if ry is None else ry * h, al)
        sec = (x2 * w, y2 * h, r2 * max(w, h), al2)
        a = [u + k * v for u, v in zip(a, main)]
        b = [u + k * v for u, v in zip(b, sec)]
    return a, b


def paint_backdrop(p, w: int, h: int, tint=None, mode=1.0, strength: float = 1.0):
    """Window background. `tint` is the cover colour; `mode` is the glow pattern (a list of weights, one per entry
    of PATTERNS; weights in between blend two patterns, so changing page glides); `strength` fades the whole
    tint in or out."""
    p.fillRect(0, 0, w, h, QColor(theme.BG))
    # Mostly black: only a faint purple haze at the top and one in the bottom-left corner (the blue wash is gone).
    g = QRadialGradient(w * 0.62, 0, w * 0.45)
    g.setColorAt(0, QColor(74, 34, 130, 120))
    g.setColorAt(1, QColor(74, 34, 130, 0))
    p.fillRect(0, 0, w, h, g)
    g2 = QRadialGradient(0, h, w * 0.5)
    g2.setColorAt(0, QColor(96, 42, 150, 110))
    g2.setColorAt(1, QColor(96, 42, 150, 0))
    p.fillRect(0, 0, w, h, g2)
    if tint is None or strength <= 0:
        return
    (cx, cy, rx, ry, al), (cx2, cy2, r2, al2) = _blend(_weights(mode), w, h)
    _glow(p, cx, cy, rx, ry, QColor(tint), al * strength, w, h)
    c2 = QColor.fromHsv((tint.hue() + 40) % 360, tint.saturation(), tint.value())
    _glow(p, cx2, cy2, r2, r2, c2, al2 * strength, w, h)


class Backdrop(QWidget):
    """Central widget: paints the window background behind the floating cards.

    ClickFocus makes a click on any part that cannot take focus itself (labels, cards, the caption pill, the
    window buttons) land here, so the search box loses focus instead of staying in "searching" mode.

    The cover-colour glow has three animated parts: the pattern (one per page, see ui/backdrop.py), `strength`
    (tint on / off) and the colour itself when a page uses another colour than the one before it, so changing
    page or starting the first song glides instead of snapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tint = None
        self._tint_from = self._tint_goal = None
        self._strength = 0.0   # 0 = plain backdrop, 1 = full tint
        self._strength_goal = 0.0
        n = len(PATTERNS)
        self._weights = [1.0] + [0.0] * (n - 1)  # blend of the glow patterns, starts on the Library one
        self._w_from = list(self._weights)
        self._w_goal = list(self._weights)
        self._weights_anim = self._make_anim(self._set_weights)
        self._strength_anim = self._make_anim(self._set_strength)
        self._tint_anim = self._make_anim(self._set_tint_mix)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def _make_anim(self, setter):
        a = QVariantAnimation(self, duration=550)
        a.setEasingCurve(QEasingCurve.Type.InOutCubic)
        a.valueChanged.connect(setter)
        return a

    def _set_weights(self, t):
        t = float(t)
        self._weights = [a + (b - a) * t for a, b in zip(self._w_from, self._w_goal)]
        self.update()

    def _set_strength(self, v):
        self._strength = float(v)
        self.update()

    def _set_tint_mix(self, t):
        a, b, t = self._tint_from, self._tint_goal, float(t)
        dh = ((b.hsvHueF() - a.hsvHueF() + 0.5) % 1.0) - 0.5  # shortest way round the colour wheel
        hue = (a.hsvHueF() + dh * t) % 1.0 if a.hsvHue() >= 0 and b.hsvHue() >= 0 else b.hsvHueF()
        self._tint = QColor.fromHsvF(hue, _mixf(a.hsvSaturationF(), b.hsvSaturationF(), t),
                                     _mixf(a.valueF(), b.valueF(), t))
        self.update()

    @staticmethod
    def _glide(anim, current: float, goal: float):
        anim.stop()
        anim.setStartValue(float(current))
        anim.setEndValue(float(goal))
        anim.start()

    def set_tint(self, color, glide: bool = False):
        """Cover colour of the playing track. None fades the tint out (the last colour is kept while it does).
        glide=True slides from the colour on screen to `color`; without it the colour is set at once (used for the
        frames of the player page's own colour animation)."""
        if color is not None:
            c = QColor(color)
            running = self._tint_anim.state() == QVariantAnimation.State.Running
            if running and c == self._tint_goal:
                pass  # already on its way there
            elif glide and self._tint is not None and self._strength_goal == 1.0 and c != self._tint:
                self._tint_from, self._tint_goal = QColor(self._tint), c
                self._glide(self._tint_anim, 0.0, 1.0)
            else:
                self._tint_anim.stop()
                self._tint = self._tint_goal = c
            if self._strength_goal != 1.0:
                self._strength_goal = 1.0
                self._glide(self._strength_anim, self._strength, 1.0)
        elif self._strength_goal != 0.0:
            self._strength_goal = 0.0
            self._glide(self._strength_anim, self._strength, 0.0)
        self.update()

    def set_pattern(self, index: int):
        """Glow pattern of the page (ui/backdrop.py): the glow glides from where it is to the new place."""
        goal = [1.0 if i == index else 0.0 for i in range(len(PATTERNS))]
        if goal != self._w_goal:
            self._w_from = list(self._weights)  # from wherever the glow is now, also when a glide is interrupted
            self._w_goal = goal
            self._glide(self._weights_anim, 0.0, 1.0)

    def paint_into(self, painter):
        paint_backdrop(painter, self.width(), self.height(), self._tint, self._weights, self._strength)

    def paintEvent(self, e):
        p = QPainter(self)
        self.paint_into(p)


def _mixf(a: float, b: float, t: float) -> float:
    return a + (b - a) * t