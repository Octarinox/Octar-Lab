"""
ui/widgets/glow_label.py
══════════════════════════════════════════════════════════════
Title label with a pulsing violet glow behind the text.
Used for the main app header.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QLabel

from ui.theme import PALETTE as P


class GlowLabel(QLabel):
    """A label that pulses with a violet glow."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._glow_value = 0.0
        self._direction = 1
        self.setObjectName("header")
        self.setMinimumHeight(36)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._glow_value += 0.03 * self._direction
        if self._glow_value >= 1.0:
            self._direction = -1
        elif self._glow_value <= 0.0:
            self._direction = 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())

        alpha = int(60 + 80 * self._glow_value)
        glow_hex = P['primary'].lstrip('#')

        # Draw 3 layered shadows for the glow effect
        for offset, a in [(4, alpha // 3), (2, alpha // 2), (1, alpha)]:
            painter.setPen(QColor(f"#{glow_hex}{a:02x}"))
            painter.drawText(
                self.rect().adjusted(offset, offset, offset, offset),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.text(),
            )
            painter.drawText(
                self.rect().adjusted(-offset, -offset, -offset, -offset),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.text(),
            )

        painter.setPen(QColor(P['text_prim']))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
        painter.end()
