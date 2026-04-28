from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel


class PulsingDot(QLabel):
    """Small pulsing colored dot — start_pulse() / stop_pulse()."""

    def __init__(self, color: str = "#10b981", parent=None):
        super().__init__("●", parent)
        self._alpha = 255
        self._direction = -8
        self._color = color  # default = success green

        # Parse the hex color into rgb once
        c = color.lstrip("#")
        self._r = int(c[0:2], 16)
        self._g = int(c[2:4], 16)
        self._b = int(c[4:6], 16)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._apply_style(255)
        self.hide()

    def _apply_style(self, alpha: int):
        self.setStyleSheet(
            f"color: rgba({self._r},{self._g},{self._b},{alpha}); font-size: 11px;"
        )

    def _tick(self):
        self._alpha += self._direction
        if self._alpha <= 60:
            self._direction = 8
        if self._alpha >= 255:
            self._direction = -8
        self._apply_style(self._alpha)

    def start_pulse(self):
        self.show()
        self._timer.start(40)

    def stop_pulse(self):
        self._timer.stop()
        self.hide()

    def set_color(self, color: str):
        c = color.lstrip("#")
        self._r = int(c[0:2], 16)
        self._g = int(c[2:4], 16)
        self._b = int(c[4:6], 16)
        self._apply_style(self._alpha)
