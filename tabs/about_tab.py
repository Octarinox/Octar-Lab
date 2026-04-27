"""
tabs/about_tab.py
══════════════════════════════════════════════════════════════
About tab — mission statement, Octarinox info, license,
contributing links.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from core.config import (
    APP_NAME, APP_VERSION, APP_REPO_URL, APP_LICENSE, APP_AUTHOR,
)
from core.i18n import t
from tabs.base_tab import BaseTab
from ui.theme import PALETTE as P


class AboutTab(BaseTab):
    def __init__(self, settings, parent=None):
        super().__init__(settings, parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        # Hero
        hero = QVBoxLayout()
        hero.setSpacing(6)
        title = QLabel(f"⬢ {APP_NAME.upper()}")
        title.setStyleSheet(
            f"color: {P['primary_hover']}; font-size: 32px; "
            f"font-weight: 800; letter-spacing: 2px;"
        )
        version = QLabel(f"Version {APP_VERSION}  ·  {APP_LICENSE} License")
        version.setStyleSheet(f"color: {P['text_sec']}; font-size: 12px;")
        tagline = QLabel(t("app.tagline"))
        tagline.setStyleSheet(f"color: {P['accent']}; font-size: 14px; letter-spacing: 1px;")
        hero.addWidget(title)
        hero.addWidget(version)
        hero.addWidget(tagline)
        layout.addLayout(hero)

        layout.addWidget(self.hline())

        # Mission
        self.mission_group = self._info_block(
            t("about.mission_title"),
            t("about.mission_body"),
        )
        layout.addWidget(self.mission_group)

        # Octarinox
        self.octarinox_group = self._info_block(
            t("about.octarinox_title"),
            t("about.octarinox_body"),
        )
        layout.addWidget(self.octarinox_group)

        # License
        self.license_group = self._info_block(
            t("about.license_title"),
            t("about.license_body"),
        )
        layout.addWidget(self.license_group)

        # Contributing
        self.contribute_group = self._info_block(
            t("about.contribute_title"),
            t("about.contribute_body"),
        )
        layout.addWidget(self.contribute_group)

        # Tech stack
        self.tech_group = QGroupBox(t("about.tech_title"))
        tech_layout = QVBoxLayout(self.tech_group)
        self.tech_text = QLabel(t("about.tech_body"))
        self.tech_text.setStyleSheet(f"color: {P['text_sec']}; padding: 4px;")
        self.tech_text.setWordWrap(True)
        tech_layout.addWidget(self.tech_text)
        layout.addWidget(self.tech_group)

        # Acknowledgments
        self.thanks_group = self._info_block(
            t("about.thanks_title"),
            t("about.thanks_body"),
        )
        layout.addWidget(self.thanks_group)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.github_btn = QPushButton("🔗  " + t("about.visit_github"))
        self.github_btn.setObjectName("primary")
        self.github_btn.setMinimumHeight(40)
        self.github_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(APP_REPO_URL))
        )
        self.issue_btn = QPushButton("⚠  " + t("about.report_issue"))
        self.issue_btn.setObjectName("ghost")
        self.issue_btn.setMinimumHeight(40)
        self.issue_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"{APP_REPO_URL}/issues"))
        )
        btn_row.addWidget(self.github_btn)
        btn_row.addWidget(self.issue_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Footer
        self.footer = QLabel(f"© 2025 {APP_AUTHOR}  ·  {t('about.footer_motto')}")
        self.footer.setStyleSheet(f"color: {P['text_dim']}; font-size: 11px; padding-top: 12px;")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer)

        layout.addStretch()

    def _info_block(self, title: str, body: str) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        text = QLabel(body)
        text.setWordWrap(True)
        text.setStyleSheet(
            f"color: {P['text_sec']}; line-height: 1.6; padding: 4px;"
        )
        layout.addWidget(text)
        return box

    def on_language_changed(self):
        # Rebuild from scratch — easiest way to refresh all the prose
        # Clear current layout
        old_layout = self.layout()
        if old_layout:
            self._clear_layout(old_layout)
            QWidget().setLayout(old_layout)  # detach old layout
        self._build_ui()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                AboutTab._clear_layout(item.layout())
