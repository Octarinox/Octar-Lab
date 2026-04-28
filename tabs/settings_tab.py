from __future__ import annotations

import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from core.ai_providers.base import ProviderError
from core.ai_providers.factory import ProviderFactory
from core.config import AppSettings, SUPPORTED_LANGUAGES as LANG_CODES, DEFAULT_MODELS
from core.i18n import t, set_language, language_display_name
from core.secrets import (
    delete_api_key, get_api_key, is_secure_backend, mask_key, save_api_key,
)
from tabs.base_tab import BaseTab
from ui.theme import PALETTE as P


class SettingsTab(BaseTab):
    """Settings tab — emits `settings_changed` when user saves anything."""

    settings_changed = pyqtSignal()
    language_changed = pyqtSignal(str)  # new language code

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        # One block per provider — populated in _build_providers_section
        self._provider_blocks: dict[str, dict] = {}
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
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # Section: General
        layout.addWidget(self._build_general_section())

        # Section: AI Providers
        layout.addWidget(self._build_providers_section())

        layout.addStretch()

    def _build_general_section(self) -> QWidget:
        self.general_group = QGroupBox(t("settings.general_group"))
        layout = QVBoxLayout(self.general_group)
        layout.setSpacing(10)

        # Language
        lang_row = QHBoxLayout()
        self.lbl_language = self.section_label(t("settings.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(180)
        for code in LANG_CODES:
            self.lang_combo.addItem(language_display_name(code), userData=code)
        # Pre-select current
        idx = self.lang_combo.findData(self.settings.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_combo_changed)
        lang_row.addWidget(self.lbl_language)
        lang_row.addStretch()
        lang_row.addWidget(self.lang_combo)
        layout.addLayout(lang_row)

        # Output directory
        out_row = QHBoxLayout()
        self.lbl_output = self.section_label(t("settings.output_dir_label"))
        self.output_input = QLineEdit(self.settings.output_directory)
        self.output_input.setMinimumHeight(32)
        self.browse_btn = QPushButton(t("settings.browse_btn"))
        self.browse_btn.setObjectName("ghost")
        self.browse_btn.setFixedHeight(32)
        self.browse_btn.clicked.connect(self._on_browse_output)
        self.output_input.editingFinished.connect(self._on_output_changed)
        out_row.addWidget(self.lbl_output)
        out_row.addWidget(self.output_input, 1)
        out_row.addWidget(self.browse_btn)
        layout.addLayout(out_row)

        # Keyring status
        if is_secure_backend():
            self.keyring_status = QLabel(t("settings.keyring_secure"))
            self.keyring_status.setStyleSheet(f"color: {P['success']};")
        else:
            self.keyring_status = QLabel(t("settings.keyring_insecure"))
            self.keyring_status.setStyleSheet(f"color: {P['warning']};")
        layout.addWidget(self.keyring_status)

        return self.general_group

    def _build_providers_section(self) -> QWidget:
        self.providers_group = QGroupBox(t("settings.providers_group"))
        layout = QVBoxLayout(self.providers_group)
        layout.setSpacing(8)

        # Hint
        self.providers_hint = self.hint_label(t("settings.providers_hint"))
        layout.addWidget(self.providers_hint)

        # Active provider selector
        active_row = QHBoxLayout()
        self.lbl_active = self.section_label(t("settings.active_provider"))
        self.active_combo = QComboBox()
        self.active_combo.setMinimumWidth(220)
        for info in ProviderFactory.info_list():
            self.active_combo.addItem(info.display_name, userData=info.id)
        idx = self.active_combo.findData(self.settings.active_provider)
        if idx >= 0:
            self.active_combo.setCurrentIndex(idx)
        self.active_combo.currentIndexChanged.connect(self._on_active_changed)
        active_row.addWidget(self.lbl_active)
        active_row.addStretch()
        active_row.addWidget(self.active_combo)
        layout.addLayout(active_row)

        # One block per provider
        for info in ProviderFactory.info_list():
            block = self._build_provider_block(info.id)
            layout.addWidget(block)

        return self.providers_group

    def _build_provider_block(self, provider_id: str) -> QWidget:
        info = ProviderFactory.get_info(provider_id)
        if info is None:
            return QWidget()

        block = QGroupBox(info.display_name)
        block.setStyleSheet(f"QGroupBox {{ background-color: {P['bg_panel']}; }}")
        layout = QVBoxLayout(block)
        layout.setSpacing(6)

        # Description
        desc = QLabel(info.description)
        desc.setObjectName("hint")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # API-key row
        key_row = QHBoxLayout()
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setPlaceholderText(t("settings.api_key_placeholder"))
        key_input.setMinimumHeight(30)
        # Pre-fill if a key already exists (masked display)
        existing = get_api_key(provider_id)
        if existing:
            key_input.setText(existing)
        toggle_btn = QPushButton(t("settings.show_key"))
        toggle_btn.setObjectName("ghost")
        toggle_btn.setCheckable(True)
        toggle_btn.setFixedWidth(80)
        toggle_btn.setFixedHeight(30)
        save_btn = QPushButton(t("settings.save_key"))
        save_btn.setObjectName("accent")
        save_btn.setFixedWidth(80)
        save_btn.setFixedHeight(30)
        delete_btn = QPushButton(t("settings.delete_key"))
        delete_btn.setObjectName("ghost")
        delete_btn.setFixedWidth(80)
        delete_btn.setFixedHeight(30)
        test_btn = QPushButton(t("settings.test_key"))
        test_btn.setObjectName("ghost")
        test_btn.setFixedWidth(140)
        test_btn.setFixedHeight(30)

        def on_toggle(checked: bool):
            if checked:
                key_input.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setText(t("settings.hide_key"))
            else:
                key_input.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setText(t("settings.show_key"))
        toggle_btn.toggled.connect(on_toggle)

        save_btn.clicked.connect(lambda: self._on_save_key(provider_id))
        delete_btn.clicked.connect(lambda: self._on_delete_key(provider_id))
        test_btn.clicked.connect(lambda: self._on_test_key(provider_id))

        key_row.addWidget(key_input, 1)
        key_row.addWidget(toggle_btn)
        key_row.addWidget(save_btn)
        key_row.addWidget(delete_btn)
        key_row.addWidget(test_btn)
        layout.addLayout(key_row)

        # Get key link
        link = QLabel(
            f'<a href="{info.api_key_url}" '
            f'style="color: {P["primary_hover"]};">{t("settings.get_key_link")}</a>'
        )
        link.setOpenExternalLinks(True)
        link.setObjectName("hint")
        layout.addWidget(link)

        # Models (architect / coder)
        models_row = QHBoxLayout()
        models_row.setSpacing(8)
        arch_label = QLabel(t("settings.model_architect"))
        arch_combo = QComboBox()
        coder_label = QLabel(t("settings.model_coder"))
        coder_combo = QComboBox()
        # Populate model lists. We don't try to instantiate the provider just
        # to read models — we use the static suggestion list from defaults.
        try:
            cls = ProviderFactory.get_class(provider_id)
            suggested: list[str] = []
            if cls:
                # Try a static fallback first
                suggested = list(DEFAULT_MODELS.get(provider_id, {}).values())
                # Then try the SDK-provided defaults if instantiable
                key = get_api_key(provider_id)
                if key:
                    try:
                        provider = cls(key)
                        suggested = provider.default_models() or suggested
                    except ProviderError:
                        pass
            for m in suggested:
                arch_combo.addItem(m)
                coder_combo.addItem(m)
        except Exception:
            pass
        arch_combo.setEditable(True)
        coder_combo.setEditable(True)
        arch_combo.setCurrentText(self.settings.get_model(provider_id, "architect") or "")
        coder_combo.setCurrentText(self.settings.get_model(provider_id, "coder") or "")
        arch_combo.currentTextChanged.connect(
            lambda txt: self._on_model_changed(provider_id, "architect", txt)
        )
        coder_combo.currentTextChanged.connect(
            lambda txt: self._on_model_changed(provider_id, "coder", txt)
        )
        models_row.addWidget(arch_label)
        models_row.addWidget(arch_combo, 1)
        models_row.addWidget(coder_label)
        models_row.addWidget(coder_combo, 1)
        layout.addLayout(models_row)

        # Status line for this provider
        status = QLabel("")
        status.setObjectName("hint")
        layout.addWidget(status)

        # Stash references for later updates
        self._provider_blocks[provider_id] = {
            "group":         block,
            "description":   desc,
            "key_input":     key_input,
            "toggle_btn":    toggle_btn,
            "save_btn":      save_btn,
            "delete_btn":    delete_btn,
            "test_btn":      test_btn,
            "link":          link,
            "arch_label":    arch_label,
            "coder_label":   coder_label,
            "arch_combo":    arch_combo,
            "coder_combo":   coder_combo,
            "status":        status,
        }
        return block

    def _on_language_combo_changed(self, _idx: int):
        new_lang = self.lang_combo.currentData()
        if not new_lang or new_lang == self.settings.language:
            return
        self.settings.language = new_lang
        self.settings.save()
        set_language(new_lang)
        self.language_changed.emit(new_lang)
        self.settings_changed.emit()

    def _on_output_changed(self):
        new_dir = self.output_input.text().strip()
        if new_dir and new_dir != self.settings.output_directory:
            self.settings.output_directory = new_dir
            self.settings.save()
            self.settings_changed.emit()

    def _on_browse_output(self):
        path = QFileDialog.getExistingDirectory(
            self, t("settings.output_dir_label"), self.settings.output_directory,
        )
        if path:
            self.output_input.setText(path)
            self._on_output_changed()

    def _on_active_changed(self, _idx: int):
        new_active = self.active_combo.currentData()
        if new_active and new_active != self.settings.active_provider:
            self.settings.active_provider = new_active
            self.settings.save()
            self.settings_changed.emit()

    def _on_save_key(self, provider_id: str):
        block = self._provider_blocks[provider_id]
        key = block["key_input"].text().strip()
        if not key:
            block["status"].setText("⚠ Empty key")
            block["status"].setStyleSheet(f"color: {P['warning']};")
            return
        if save_api_key(provider_id, key):
            block["status"].setText(t("settings.key_saved"))
            block["status"].setStyleSheet(f"color: {P['success']};")
        else:
            block["status"].setText("✗ Save failed")
            block["status"].setStyleSheet(f"color: {P['danger']};")

    def _on_delete_key(self, provider_id: str):
        confirm = QMessageBox.question(
            self,
            t("common.confirm"),
            f"{t('settings.delete_key')}: {ProviderFactory.get_info(provider_id).display_name}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        delete_api_key(provider_id)
        block = self._provider_blocks[provider_id]
        block["key_input"].clear()
        block["status"].setText(t("settings.key_deleted"))
        block["status"].setStyleSheet(f"color: {P['text_dim']};")

    def _on_test_key(self, provider_id: str):
        block = self._provider_blocks[provider_id]
        block["status"].setText(t("settings.key_validating"))
        block["status"].setStyleSheet(f"color: {P['info']};")
        block["test_btn"].setEnabled(False)

        # Run validation in a daemon thread to avoid blocking the UI
        def worker():
            try:
                key = block["key_input"].text().strip() or get_api_key(provider_id)
                if not key:
                    self._post_test_result(provider_id, False, "✗ No key entered")
                    return
                provider = ProviderFactory.create(provider_id, key)
                ok, msg = provider.validate_key()
                self._post_test_result(provider_id, ok, msg)
            except ProviderError as e:
                self._post_test_result(provider_id, False, f"✗ {e}")
            except Exception as e:
                self._post_test_result(provider_id, False, f"✗ {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _post_test_result(self, provider_id: str, success: bool, message: str):
        # Marshal back to UI thread
        def apply():
            block = self._provider_blocks[provider_id]
            block["status"].setText(message)
            block["status"].setStyleSheet(
                f"color: {P['success'] if success else P['danger']};"
            )
            block["test_btn"].setEnabled(True)
        QTimer.singleShot(0, apply)

    def _on_model_changed(self, provider_id: str, role: str, model_name: str):
        if not model_name.strip():
            return
        self.settings.set_model(provider_id, role, model_name.strip())
        self.settings.save()
        self.settings_changed.emit()

    def on_language_changed(self):
        self.general_group.setTitle(t("settings.general_group"))
        self.lbl_language.setText(t("settings.language_label"))
        self.lbl_output.setText(t("settings.output_dir_label"))
        self.browse_btn.setText(t("settings.browse_btn"))
        self.providers_group.setTitle(t("settings.providers_group"))
        self.providers_hint.setText(t("settings.providers_hint"))
        self.lbl_active.setText(t("settings.active_provider"))

        if is_secure_backend():
            self.keyring_status.setText(t("settings.keyring_secure"))
        else:
            self.keyring_status.setText(t("settings.keyring_insecure"))

        for pid, block in self._provider_blocks.items():
            block["save_btn"].setText(t("settings.save_key"))
            block["delete_btn"].setText(t("settings.delete_key"))
            block["test_btn"].setText(t("settings.test_key"))
            block["arch_label"].setText(t("settings.model_architect"))
            block["coder_label"].setText(t("settings.model_coder"))
            block["key_input"].setPlaceholderText(t("settings.api_key_placeholder"))
            # toggle_btn label depends on its checked state
            if block["toggle_btn"].isChecked():
                block["toggle_btn"].setText(t("settings.hide_key"))
            else:
                block["toggle_btn"].setText(t("settings.show_key"))
            info = ProviderFactory.get_info(pid)
            if info:
                block["link"].setText(
                    f'<a href="{info.api_key_url}" '
                    f'style="color: {P["primary_hover"]};">{t("settings.get_key_link")}</a>'
                )
