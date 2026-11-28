from datetime import datetime

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

BG = "#070810"
TEXT = "#f3f5ff"
MUTED = "#9aa0b8"
DIM = "#6b7190"
DEFAULT_ACCENT = "#7c9cff"
CHOSEN = DEFAULT_ACCENT   # the colour picked in Settings (ACCENT below is that colour made readable on the dark UI)
ACCENT = "#7c9cff"        # text, rings, highlights, switches
ACCENT_B = "#a07cff"      # second colour of the waveform: the accent turned 40 degrees round the colour wheel
GRAD_A = "#4f7bff"        # logo / gradients
GRAD_B = "#a77bff"


def set_accent(value: str) -> str:
    """Make `value` (#rrggbb) the accent colour of the whole app; returns the colour that was picked.
    Widgets read theme.ACCENT / ACCENT_B / GRAD_A / GRAD_B while painting, so they follow after a repaint; call
    app.setStyleSheet(theme.style()) too for the colours that live in style sheets."""
    global CHOSEN, ACCENT, ACCENT_B, GRAD_A, GRAD_B
    c = QColor(str(value))
    if not c.isValid():
        c = QColor(DEFAULT_ACCENT)
    CHOSEN = c.name()
    if CHOSEN == DEFAULT_ACCENT:  # the original blue / purple look, exactly
        ACCENT, ACCENT_B, GRAD_A, GRAD_B = "#7c9cff", "#a07cff", "#4f7bff", "#a77bff"
        return CHOSEN
    h, s, l, _ = c.getHslF()
    h = max(h, 0.0)  # grey has no hue
    turn = 40 / 360
    hsl = lambda hh, ss, ll: QColor.fromHslF(hh % 1.0, min(1.0, max(0.0, ss)), min(1.0, max(0.0, ll))).name()
    ACCENT = hsl(h, s, max(l, 0.62))                       # readable on the dark background
    ACCENT_B = hsl(h + turn, s, max(l, 0.62))
    GRAD_A = hsl(h, s, min(max(l, 0.50), 0.62))
    GRAD_B = hsl(h + turn, s, min(max(l, 0.50), 0.66))
    return CHOSEN


def accent_color(alpha: int = 255) -> QColor:
    """The accent as a QColor with the given alpha (0-255): for highlights painted by hand."""
    c = QColor(ACCENT)
    c.setAlpha(alpha)
    return c


def accentize(qss: str) -> str:
    """A style sheet written with the default accent, turned into one with the current accent."""
    r, g, b, _ = QColor(ACCENT).getRgb()
    return qss.replace("124,156,255", f"{r},{g},{b}").replace("#4f7bff", GRAD_A)


FAMILY = "Poppins"
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def load_fonts() -> None:
    """Register the bundled fonts; call once after QApplication is created, before any widget."""
    for f in sorted(FONT_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


def font(px: int, weight=QFont.Weight.Normal, spacing: float = 0.0) -> QFont:
    f = QFont()
    f.setFamilies([FAMILY, "Inter", "Segoe UI", "Arial"])
    f.setPixelSize(px)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def fmt_time(ms: float) -> str:
    s = max(0, int(ms // 1000))
    return f"{s // 60}:{s % 60:02d}"


def fmt_added(ts: float) -> str:
    d = datetime.fromtimestamp(ts)
    return f"{d.day} {d:%b}"


STYLE = """
QToolTip{background:#14172a;color:#e8ebff;border:1px solid #2a2f4a;padding:4px 8px;}
QLabel{background:transparent;}
QPushButton#pill{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.10);border-radius:18px;padding:0 18px;color:#e8ebff;font-size:13px;}
QPushButton#pill:hover{background:rgba(255,255,255,0.10);}
QPushButton#pill:checked{background:rgba(124,156,255,0.25);border-color:rgba(124,156,255,0.5);}
QPushButton#pill::menu-indicator{image:none;width:0;}
QFrame#segFrame{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.10);border-radius:21px;}
QPushButton#seg{background:transparent;border:none;border-radius:17px;padding:0 20px;color:#aab0c8;font-size:15px;font-weight:600;}
QPushButton#seg:checked{background:rgba(255,255,255,0.14);color:#ffffff;}
QPushButton#seg:hover:!checked{color:#ffffff;}
QLineEdit#search{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.10);border-radius:21px;padding:0 22px 0 46px;color:#f3f5ff;font-size:15px;selection-background-color:#4f7bff;}
QLineEdit#search:focus{border-color:rgba(124,156,255,0.6);}
QPushButton#primary{background:#ffffff;color:#0a0b14;border:none;border-radius:22px;padding:0 26px;font-size:15px;font-weight:600;}
QPushButton#primary:hover{background:#e6e9ff;}
QPushButton#secondary{background:rgba(255,255,255,0.12);color:#f3f5ff;border:none;border-radius:22px;padding:0 26px;font-size:15px;font-weight:600;}
QPushButton#secondary:hover{background:rgba(255,255,255,0.20);}
QListView{background:transparent;border:none;outline:none;}
QMenu{background:#12152a;border:1px solid #262b48;border-radius:10px;padding:6px;color:#e8ebff;}
QMenu::item{padding:7px 22px;border-radius:6px;}
QMenu::item:selected{background:rgba(124,156,255,0.25);}
"""


def style() -> str:
    """The application style sheet with the current accent colour."""
    return accentize(STYLE)
