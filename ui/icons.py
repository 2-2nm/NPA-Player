from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def draw_icon(p: QPainter, name: str, r: QRectF, color: str, filled_color: str | None = None):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    pen = QPen(c, 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = min(r.width(), r.height())
    u = s / 24
    cx, cy = r.center().x(), r.center().y()

    def pt(a, b):
        return QPointF(cx + (a - 12) * u, cy + (b - 12) * u)

    def box(a, b, w, h):
        return QRectF(cx + (a - 12) * u, cy + (b - 12) * u, w * u, h * u)

    if name == "grid":
        for a, b in ((3.5, 3.5), (13.5, 3.5), (3.5, 13.5), (13.5, 13.5)):
            p.drawRoundedRect(box(a, b, 7, 7), 2 * u, 2 * u)
    elif name == "wave":
        for a, t, b in ((4, 10, 14), (8, 6, 18), (12, 3, 21), (16, 8, 16), (20, 10, 14)):
            p.drawLine(pt(a, t), pt(a, b))
    elif name == "queue":
        for y, x2 in ((6, 20), (12, 14), (18, 10)):
            p.drawLine(pt(4, y), pt(x2, y))
        p.drawLine(pt(17, 15), pt(21, 15))
        p.drawLine(pt(19, 13), pt(19, 17))
    elif name == "playlist":
        for y, x2 in ((6, 20), (12, 12), (18, 10)):
            p.drawLine(pt(4, y), pt(x2, y))
        p.drawLine(pt(16, 12), pt(16, 17.5))
        p.drawLine(pt(16, 17.5), pt(20.5, 17.5))
        p.drawLine(pt(18.3, 15.3), pt(20.5, 17.5))
        p.drawLine(pt(18.3, 19.7), pt(20.5, 17.5))
    elif name == "plus":
        p.drawLine(pt(12, 4), pt(12, 20))
        p.drawLine(pt(4, 12), pt(20, 12))
    elif name == "plus_circle":
        p.drawEllipse(pt(12, 12), 9 * u, 9 * u)
        p.drawLine(pt(12, 8), pt(12, 16))
        p.drawLine(pt(8, 12), pt(16, 12))
    elif name == "clock":
        p.drawEllipse(pt(12, 12), 9 * u, 9 * u)
        p.drawLine(pt(12, 7), pt(12, 12))
        p.drawLine(pt(12, 12), pt(15.5, 14))
    elif name == "trend":
        p.drawLine(pt(3, 17), pt(9, 11))
        p.drawLine(pt(9, 11), pt(13, 15))
        p.drawLine(pt(13, 15), pt(21, 7))
        p.drawLine(pt(15, 7), pt(21, 7))
        p.drawLine(pt(21, 7), pt(21, 13))
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(pt(12, 20))
        path.cubicTo(pt(6, 16), pt(3, 12.5), pt(3, 8.5))
        path.cubicTo(pt(3, 5.5), pt(5.3, 3.5), pt(7.5, 3.5))
        path.cubicTo(pt(9.5, 3.5), pt(11.2, 4.6), pt(12, 6.3))
        path.cubicTo(pt(12.8, 4.6), pt(14.5, 3.5), pt(16.5, 3.5))
        path.cubicTo(pt(18.7, 3.5), pt(21, 5.5), pt(21, 8.5))
        path.cubicTo(pt(21, 12.5), pt(18, 16), pt(12, 20))
        p.drawPath(path)
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(pt(3, 7))
        path.lineTo(pt(9, 7))
        path.lineTo(pt(11.5, 9.5))
        path.lineTo(pt(21, 9.5))
        path.lineTo(pt(21, 19))
        path.lineTo(pt(3, 19))
        path.closeSubpath()
        p.drawPath(path)
    elif name == "folder_music":  # rounded folder with a music note: the folders page (music + lyrics folders)
        path = QPainterPath()
        path.moveTo(pt(3, 7))
        path.quadTo(pt(3, 5), pt(5, 5))
        path.lineTo(pt(9.3, 5))
        path.lineTo(pt(11, 7.5))
        path.lineTo(pt(19, 7.5))
        path.quadTo(pt(21, 7.5), pt(21, 9.5))
        path.lineTo(pt(21, 17))
        path.quadTo(pt(21, 19), pt(19, 19))
        path.lineTo(pt(5, 19))
        path.quadTo(pt(3, 19), pt(3, 17))
        path.closeSubpath()
        p.drawPath(path)
        note = QPainterPath()  # stem with a small flag
        note.moveTo(pt(12.4, 15.4))
        note.lineTo(pt(12.4, 10.9))
        note.lineTo(pt(15, 12.1))
        p.drawPath(note)
        p.setBrush(c)  # note head
        p.drawEllipse(pt(10.9, 15.6), 1.5 * u, 1.5 * u)
        p.setBrush(Qt.NoBrush)
    elif name in ("volume", "volume_low", "volume_mute"):
        body = QPainterPath()
        body.moveTo(pt(4, 9.5))
        body.lineTo(pt(8, 9.5))
        body.lineTo(pt(13, 5.5))
        body.lineTo(pt(13, 18.5))
        body.lineTo(pt(8, 14.5))
        body.lineTo(pt(4, 14.5))
        body.closeSubpath()
        p.drawPath(body)
        if name == "volume_mute":
            p.drawLine(pt(16.5, 9.5), pt(21, 14.5))
            p.drawLine(pt(21, 9.5), pt(16.5, 14.5))
        else:
            p.drawArc(box(8.5, 7.5, 9, 9), -45 * 16, 90 * 16)
            if name == "volume":
                p.drawArc(box(5, 4, 16, 16), -45 * 16, 90 * 16)
    elif name == "search":
        p.drawEllipse(pt(10.5, 10.5), 6.5 * u, 6.5 * u)
        p.drawLine(pt(15.3, 15.3), pt(20, 20))
    elif name == "gear":
        import math
        path = QPainterPath()
        pts = []
        for i in range(8):  # eight teeth
            base = i * math.pi / 4
            for da, r in ((-0.30, 7.2), (-0.17, 9.7), (0.17, 9.7), (0.30, 7.2)):
                pts.append(pt(12 + r * math.cos(base + da), 12 + r * math.sin(base + da)))
        path.moveTo(pts[0])
        for q in pts[1:]:
            path.lineTo(q)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(pt(12, 12), 3 * u, 3 * u)
    elif name == "sun":
        p.drawEllipse(pt(12, 12), 4 * u, 4 * u)
        import math
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(pt(12 + 7 * math.cos(a), 12 + 7 * math.sin(a)), pt(12 + 9.5 * math.cos(a), 12 + 9.5 * math.sin(a)))
    else:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(filled_color or color))
        if name == "play":
            path = QPainterPath()
            path.moveTo(pt(8, 5))
            path.lineTo(pt(19, 12))
            path.lineTo(pt(8, 19))
            path.closeSubpath()
            p.drawPath(path)
        elif name == "pause":
            p.drawRoundedRect(box(6.5, 5, 3.8, 14), 1.2 * u, 1.2 * u)
            p.drawRoundedRect(box(13.7, 5, 3.8, 14), 1.2 * u, 1.2 * u)
        elif name in ("prev", "next"):
            path = QPainterPath()
            if name == "prev":
                p.drawRoundedRect(box(5, 5.5, 2.6, 13), 1 * u, 1 * u)
                path.moveTo(pt(19, 5.5)); path.lineTo(pt(9.5, 12)); path.lineTo(pt(19, 18.5))
            else:
                p.drawRoundedRect(box(16.4, 5.5, 2.6, 13), 1 * u, 1 * u)
                path.moveTo(pt(5, 5.5)); path.lineTo(pt(14.5, 12)); path.lineTo(pt(5, 18.5))
            path.closeSubpath()
            p.drawPath(path)
    p.restore()