"""Dialogs in the app's own look (replacing QInputDialog / QMessageBox): frameless dark card, capsule buttons,
the main window dimmed behind it. Use the two helpers at the bottom."""
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap, QTextCursor
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout,
                               QWidget)

from services.playlist_service import PlaylistService
from ui import theme
from ui.pages.playlists.cover import custom_pixmap, draw_cover, mosaic_tracks
from ui.shell.header import CapsuleButton

CARD_W = 420

FIELD_STYLE = (
    "QLineEdit{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:21px;"
    "padding:0 18px;color:#f3f5ff;font-size:15px;selection-background-color:#4f7bff;}"
    "QLineEdit:focus{border-color:rgba(124,156,255,0.7);}"
)


class _Dim(QWidget):
    """Dark veil over the main window while a dialog is open."""

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 120))


class ThemedDialog(QDialog):
    card_w = CARD_W

    def __init__(self, parent, title: str, message: str = ""):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(self.card_w)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(28, 26, 28, 24)
        self.body.setSpacing(0)

        head = QLabel(title)
        head.setFont(theme.font(22, QFont.Weight.Bold))
        head.setStyleSheet(f"color:{theme.TEXT};")
        self.body.addWidget(head)
        if message:
            msg = QLabel(message)
            msg.setWordWrap(True)
            msg.setFont(theme.font(15))
            msg.setStyleSheet(f"color:{theme.MUTED};")
            self.body.addSpacing(8)
            self.body.addWidget(msg)
        self.body.addSpacing(20)

    def add_buttons(self, ok_text: str, kind: str = "primary") -> CapsuleButton:
        self.body.addSpacing(24)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)
        cancel = CapsuleButton("Cancel", "secondary")
        self.ok_btn = CapsuleButton(ok_text, kind)
        cancel.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(self.ok_btn)
        self.body.addLayout(row)
        return self.ok_btn

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(16, 18, 32, 250))
        p.setPen(QColor(255, 255, 255, 40))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 24, 24)

    # drag the card by any empty part of it
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()
        super().mousePressEvent(e)

    def exec(self):
        win = self.parent().window() if self.parent() else None
        dim = None
        if win is not None:
            dim = _Dim(win)
            dim.setGeometry(win.rect())
            dim.show()
            dim.raise_()
            self.adjustSize()
            self.move(win.frameGeometry().center() - QPoint(self.width() // 2, self.height() // 2))
        try:
            return super().exec()
        finally:
            if dim is not None:
                dim.deleteLater()


class NameDialog(ThemedDialog):
    def __init__(self, parent, title: str, message: str, text: str, ok_text: str):
        super().__init__(parent, title, message)
        self.field = QLineEdit(text)
        self.field.setFixedHeight(42)
        self.field.setMaxLength(60)
        self.field.setPlaceholderText("Playlist name")
        self.field.setStyleSheet(theme.accentize(FIELD_STYLE))
        self.body.addWidget(self.field)
        ok = self.add_buttons(ok_text)
        self.field.textChanged.connect(lambda t: ok.setEnabled(bool(t.strip())))
        self.field.returnPressed.connect(lambda: self.accept() if self.field.text().strip() else None)
        ok.setEnabled(bool(text.strip()))
        self.field.setFocus()
        self.field.selectAll()

    def value(self) -> str:
        return self.field.text().strip()


def ask_name(parent, title: str, message: str = "", text: str = "", ok_text: str = "Save") -> str | None:
    """Name prompt. Returns the trimmed name, or None if cancelled."""
    d = NameDialog(parent, title, message, text, ok_text)
    return d.value() if d.exec() == QDialog.Accepted else None


def confirm(parent, title: str, message: str, ok_text: str = "OK", danger: bool = False) -> bool:
    d = ThemedDialog(parent, title, message)
    d.body.addSpacing(-20)  # no field under the message
    d.add_buttons(ok_text, "danger" if danger else "primary")
    return d.exec() == QDialog.Accepted


class CoverPreview(QWidget):
    """Square cover in the edit dialog. A click picks a new image."""
    clicked = Signal()
    SIZE = 160

    def __init__(self, covers: list, custom: QPixmap | None, parent=None):
        super().__init__(parent)
        self._covers, self._custom, self._hover = covers, custom, False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def set_custom(self, px: QPixmap | None):
        self._custom = px
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        e.accept()  # do not let the dialog start a window drag from here

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 20, 20)
        p.save()
        p.setClipPath(clip)
        draw_cover(p, r, self._covers, self._custom, self.devicePixelRatioF())
        if self._hover:
            p.fillRect(r, QColor(0, 0, 0, 110))
            p.setPen(QColor("#ffffff"))
            p.setFont(theme.font(15, QFont.Weight.DemiBold))
            p.drawText(r, Qt.AlignCenter, "Change cover")
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.setPen(QColor(255, 255, 255, 34))
        p.drawPath(clip)


class EditPlaylistDialog(ThemedDialog):
    card_w = 620

    def __init__(self, parent, pl, tracks: list):
        super().__init__(parent, "Edit playlist")
        self._src: str | None = None  # new image picked in this dialog
        self._clear = False           # back to the automatic cover
        custom = custom_pixmap(pl.cover)
        self.preview = CoverPreview(mosaic_tracks(tracks), custom)
        self.preview.clicked.connect(self._pick)
        self.change_btn = CapsuleButton("Change cover", "secondary")
        self.remove_btn = CapsuleButton("Remove cover", "secondary")
        self.change_btn.clicked.connect(self._pick)
        self.remove_btn.clicked.connect(self._remove)
        self.remove_btn.setVisible(custom is not None)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(self.preview)
        left.addWidget(self.change_btn)
        left.addWidget(self.remove_btn)
        left.addStretch(1)

        self.name = QLineEdit(pl.name)
        self.name.setFixedHeight(42)
        self.name.setMaxLength(60)
        self.name.setPlaceholderText("Playlist name")
        self.name.setStyleSheet(theme.accentize(FIELD_STYLE))
        self.desc = QPlainTextEdit(pl.description)
        self.desc.setPlaceholderText("Add an optional description")
        self.desc.setStyleSheet(theme.accentize(
            "QPlainTextEdit{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);"
            "border-radius:18px;padding:8px 14px;color:#f3f5ff;font-size:15px;selection-background-color:#4f7bff;}"
            "QPlainTextEdit:focus{border-color:rgba(124,156,255,0.7);}"))
        self.desc.textChanged.connect(self._limit_desc)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.addWidget(self._label("Name"))
        right.addWidget(self.name)
        right.addSpacing(10)
        right.addWidget(self._label("Description"))
        right.addWidget(self.desc, 1)

        row = QHBoxLayout()
        row.setSpacing(24)
        row.addLayout(left)
        row.addLayout(right, 1)
        self.body.addLayout(row)

        self.ok = self.add_buttons("Save")
        self.name.textChanged.connect(lambda t: self.ok.setEnabled(bool(t.strip())))
        self.name.returnPressed.connect(lambda: self.accept() if self.name.text().strip() else None)
        self.ok.setEnabled(bool(pl.name.strip()))
        self.name.setFocus()
        self.name.selectAll()

    @staticmethod
    def _label(text: str) -> QLabel:
        l = QLabel(text)
        l.setFont(theme.font(13, QFont.Weight.Medium))
        l.setStyleSheet(f"color:{theme.DIM};")
        return l

    def _limit_desc(self, max_len: int = 200):
        t = self.desc.toPlainText()
        if len(t) > max_len:
            self.desc.setPlainText(t[:max_len])
            self.desc.moveCursor(QTextCursor.End)

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose cover image", str(Path.home() / "Pictures"),
                                              "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        img = PlaylistService.square_image(path, 320)
        if img is None:
            return  # not a readable image
        self._src, self._clear = path, False
        self.preview.set_custom(QPixmap.fromImage(img))
        self.remove_btn.setVisible(True)

    def _remove(self):
        self._src, self._clear = None, True
        self.preview.set_custom(None)
        self.remove_btn.setVisible(False)

    def result_data(self) -> dict:
        return {"name": self.name.text().strip(), "description": self.desc.toPlainText().strip(),
                "cover_src": self._src, "clear_cover": self._clear and not self._src}


def edit_playlist(parent, playlist, tracks: list) -> dict | None:
    """Edit name, description and cover. Returns the new values, or None if cancelled."""
    d = EditPlaylistDialog(parent, playlist, tracks)
    return d.result_data() if d.exec() == QDialog.Accepted else None