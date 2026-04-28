from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.i18n import t
from tabs.base_tab import BaseTab
from ui.theme import PALETTE as P


class PlaceholderTab(BaseTab):
    """
    Generic placeholder shown for features queued for the next phase.

    Subclass with two class attributes:
      ICON     — emoji or icon prefix
      KEY_NAME — i18n key prefix, e.g. "tab.library"
    """

    ICON: str = "✦"
    KEY_NAME: str = "tab.placeholder"
    DESCRIPTION_KEY: str = "common.placeholder_tab"

    def __init__(self, settings, parent=None):
        super().__init__(settings, parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch(1)

        self.icon_label = QLabel(self.ICON)
        self.icon_label.setStyleSheet(
            f"color: {P['primary_hover']}; font-size: 64px;"
        )
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        self.title_label = QLabel(t(self.KEY_NAME))
        self.title_label.setStyleSheet(
            f"color: {P['text_prim']}; font-size: 24px; font-weight: 700;"
        )
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.coming_label = QLabel(t("common.coming_soon"))
        self.coming_label.setStyleSheet(
            f"color: {P['accent']}; font-size: 13px; "
            f"letter-spacing: 2px; padding-top: 4px;"
        )
        self.coming_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coming_label)

        self.desc_label = QLabel(t(self.DESCRIPTION_KEY))
        self.desc_label.setStyleSheet(
            f"color: {P['text_sec']}; font-size: 14px;"
        )
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        layout.addStretch(2)

    def on_language_changed(self):
        self.title_label.setText(t(self.KEY_NAME))
        self.coming_label.setText(t("common.coming_soon"))
        self.desc_label.setText(t(self.DESCRIPTION_KEY))
