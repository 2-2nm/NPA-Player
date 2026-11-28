from PySide6.QtCore import QEasingCurve, QObject, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QImage

from ui import theme
from ui.rendering.accent import pick_accent
from ui.rendering.cover_renderer import CoverRenderer

NEUTRAL = QColor(78, 86, 112)   # a cover without any colour (black, grey, white artwork): a calm slate
SAT_MIN, SAT_MAX = 0.50, 0.90   # the card colour is never washed out ...
VAL_MIN, VAL_MAX = 0.55, 0.80   # ... and never glaring
_cache: dict = {}


def cover_tint(track) -> QColor | None:
    """Card colour of a song's cover. Only the coloured pixels vote (white, grey and black are ignored), so a
    mostly white cover with a blue logo gives that blue, not white and not a muddy grey; the result is kept
    inside a saturation / brightness range so a gradient made of it is never too bright."""
    if track is None:
        return None
    key = CoverRenderer.cover_key(track)
    if key in _cache:
        return QColor(_cache[key])
    px = CoverRenderer.pixmap(track, 48, 0)
    img = px.scaled(48, 48, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).toImage().convertToFormat(QImage.Format_ARGB32)
    pixels = []
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() >= 128:
                pixels.append((c.hsvHue(), c.hsvSaturationF(), c.valueF()))
    picked = pick_accent(pixels) if pixels else None
    if picked is None:
        color = QColor(NEUTRAL)
    else:
        h, sat, val = picked
        color = QColor.fromHsvF(h / 360, min(SAT_MAX, max(SAT_MIN, sat)), min(VAL_MAX, max(VAL_MIN, val)))
    if len(_cache) > 256:
        _cache.clear()
    _cache[key] = color
    return QColor(color)


class TintFade(QObject):
    """A colour that glides to a new one (the shortest way round the colour wheel); `changed` fires on every step.
    Cards use it for a background that follows the cover colour."""
    changed = Signal()

    def __init__(self, parent, default: QColor | None = None, duration: int = 320):
        super().__init__(parent)
        self._fixed = QColor(default) if default is not None else None  # None: the accent colour
        self.color = self._default()
        self._a = self._b = QColor(self.color)
        self._anim = QVariantAnimation(self, duration=duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.valueChanged.connect(self._step)

    def _default(self) -> QColor:
        return QColor(self._fixed) if self._fixed is not None else QColor(theme.GRAD_A)

    def set_target(self, color: QColor | None, animate: bool = True):
        goal = QColor(color) if color is not None else self._default()
        if self._anim.state() == QVariantAnimation.State.Running and goal == self._b:
            return
        self._anim.stop()
        if not animate or goal == self.color:
            self.color = self._a = self._b = goal
            self.changed.emit()
            return
        self._a, self._b = QColor(self.color), goal
        self._anim.start()

    def _step(self, t):
        t, a, b = float(t), self._a, self._b
        if a.hsvHue() < 0 or b.hsvHue() < 0:  # grey has no hue: just move to the goal's
            hue = b.hsvHueF() if b.hsvHue() >= 0 else a.hsvHueF()
        else:
            dh = ((b.hsvHueF() - a.hsvHueF() + 0.5) % 1.0) - 0.5  # shortest way round
            hue = (a.hsvHueF() + dh * t) % 1.0
        mix = lambda x, y: x + (y - x) * t
        self.color = QColor.fromHsvF(max(0.0, hue), mix(a.hsvSaturationF(), b.hsvSaturationF()),
                                     mix(a.valueF(), b.valueF()))
        self.changed.emit()
