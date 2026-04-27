"""
tabs/devops_tab.py
══════════════════════════════════════════════════════════════
DevOps Templates tab.
Generates production-grade infrastructure templates:
  • Dockerfile (single or multi-stage)
  • docker-compose.yml
  • GitHub Actions / GitLab CI workflows
  • Makefile
  • Kubernetes manifests (Deployment + Service + Ingress)
  • Terraform modules
  • Nginx configuration
  • systemd unit files

Single-file output — uses SimpleWorker.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.simple_worker import SimpleWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P
from ui.widgets.output_panel import OutputPanel


# Template kind → (i18n key, output filename, log label, fence-strip)
KINDS = {
    "dockerfile": {
        "key":      "devops.kind_dockerfile",
        "filename": "Dockerfile",
        "log":      "Generating Dockerfile",
        "strip":    True,
    },
    "compose": {
        "key":      "devops.kind_compose",
        "filename": "docker-compose.yml",
        "log":      "Generating docker-compose",
        "strip":    True,
    },
    "github_actions": {
        "key":      "devops.kind_github_actions",
        "filename": ".github/workflows/ci.yml",
        "log":      "Generating GitHub Actions workflow",
        "strip":    True,
    },
    "gitlab_ci": {
        "key":      "devops.kind_gitlab_ci",
        "filename": ".gitlab-ci.yml",
        "log":      "Generating GitLab CI pipeline",
        "strip":    True,
    },
    "makefile": {
        "key":      "devops.kind_makefile",
        "filename": "Makefile",
        "log":      "Generating Makefile",
        "strip":    True,
    },
    "kubernetes": {
        "key":      "devops.kind_kubernetes",
        "filename": "k8s.yaml",
        "log":      "Generating Kubernetes manifests",
        "strip":    True,
    },
    "terraform": {
        "key":      "devops.kind_terraform",
        "filename": "main.tf",
        "log":      "Generating Terraform module",
        "strip":    True,
    },
    "nginx": {
        "key":      "devops.kind_nginx",
        "filename": "nginx.conf",
        "log":      "Generating Nginx configuration",
        "strip":    True,
    },
    "systemd": {
        "key":      "devops.kind_systemd",
        "filename": "service.service",
        "log":      "Generating systemd unit",
        "strip":    True,
    },
}

TARGETS = {
    "dev":     "devops.target_dev",
    "staging": "devops.target_staging",
    "prod":    "devops.target_prod",
}


def build_system_prompt(kind: str, target: str,
                        multistage: bool, healthcheck: bool,
                        security: bool, caching: bool, comments: bool) -> str:
    target_label = {
        "dev":     "development (fast iteration, debug logging, hot reload where applicable)",
        "staging": "staging (production-like but with verbose logging and observability)",
        "prod":    "production (optimized, minimal, secure, observability-ready)",
    }.get(target, "production")

    # Per-kind base prompt
    if kind == "dockerfile":
        base = (
            "You are an expert in container best practices. Write a single Dockerfile "
            "for the application described by the user.\n"
        )
        opts = []
        if multistage:
            opts.append("- Use a multi-stage build to minimize the final image size")
        if healthcheck:
            opts.append("- Include a HEALTHCHECK instruction")
        if security:
            opts.append("- Apply security hardening: non-root user, pinned base image versions, "
                        "no unnecessary packages, minimal final image")
        if caching:
            opts.append("- Order COPY/RUN steps for optimal Docker layer caching "
                        "(dependencies before source code)")

    elif kind == "compose":
        base = (
            "You are an expert in Docker Compose. Write a docker-compose.yml file for "
            "the application described by the user.\n"
            "Use compose specification version 3.8+ syntax. Define all services, networks, "
            "and named volumes the application needs.\n"
        )
        opts = []
        if healthcheck:
            opts.append("- Include healthcheck definitions for each service")
        if security:
            opts.append("- Apply security best practices: read-only file systems where possible, "
                        "drop unnecessary capabilities, no privileged mode")

    elif kind == "github_actions":
        base = (
            "You are an expert in GitHub Actions. Write a .github/workflows/ci.yml workflow "
            "file for the application described by the user.\n"
            "Use the latest stable action versions. Define jobs for lint, test, build, and "
            "(where appropriate) deploy.\n"
        )
        opts = []
        if caching:
            opts.append("- Use actions/cache for dependencies to speed up runs")
        if security:
            opts.append("- Pin all third-party actions to a specific commit SHA, not just version tag")

    elif kind == "gitlab_ci":
        base = (
            "You are an expert in GitLab CI. Write a .gitlab-ci.yml pipeline for the "
            "application described by the user.\n"
            "Define stages: lint, test, build, deploy. Use templates and includes where helpful.\n"
        )
        opts = []
        if caching:
            opts.append("- Use cache: definitions to speed up dependency installation")

    elif kind == "makefile":
        base = (
            "You are an expert in Makefiles. Write a Makefile for the project described by "
            "the user with targets for: install, lint, test, build, run, clean, and any "
            "deployment commands appropriate to the project.\n"
            "Use .PHONY targets, the := assignment operator for variables, and a default "
            "`help` target that lists all available targets.\n"
        )
        opts = []

    elif kind == "kubernetes":
        base = (
            "You are an expert in Kubernetes. Write Kubernetes manifests for the application "
            "described by the user — typically a Deployment, a Service, and an Ingress.\n"
            "Use apiVersion that's stable in current K8s (1.28+). Separate manifests with `---`.\n"
        )
        opts = []
        if healthcheck:
            opts.append("- Define livenessProbe and readinessProbe on the container")
        if security:
            opts.append("- Apply pod and container security context: runAsNonRoot, "
                        "readOnlyRootFilesystem, drop ALL capabilities, seccompProfile RuntimeDefault")

    elif kind == "terraform":
        base = (
            "You are an expert in Terraform. Write a Terraform module for the infrastructure "
            "described by the user.\n"
            "Use HCL2 syntax. Declare required_providers, variables with types and descriptions, "
            "resources, and outputs. Follow the standard module layout (main.tf style — but in "
            "a single file unless asked otherwise).\n"
        )
        opts = []

    elif kind == "nginx":
        base = (
            "You are an expert in Nginx configuration. Write an nginx.conf (or server block) "
            "for the application described by the user.\n"
        )
        opts = []
        if security:
            opts.append("- Include security headers: X-Frame-Options, X-Content-Type-Options, "
                        "Referrer-Policy, and recommended CSP")
            opts.append("- Disable server tokens; hide the Nginx version")
        if caching:
            opts.append("- Enable gzip compression and configure sensible cache headers for static assets")

    elif kind == "systemd":
        base = (
            "You are an expert in systemd. Write a systemd unit file for the service "
            "described by the user.\n"
            "Define [Unit], [Service], and [Install] sections. Use Type=simple/notify as "
            "appropriate. Configure Restart, RestartSec, and standard output/error.\n"
        )
        opts = []
        if security:
            opts.append("- Apply systemd hardening: NoNewPrivileges, ProtectSystem=strict, "
                        "ProtectHome, PrivateTmp, ProtectKernelTunables, etc.")

    else:
        base = "Generate the requested DevOps template based on the user's project description."
        opts = []

    parts = [
        base,
        f"Target environment: {target_label}.",
    ]
    if opts:
        parts.append("\n".join(opts))
    if comments:
        parts.append("Include concise inline comments explaining non-obvious choices.")
    else:
        parts.append("Keep it terse — comments only where strictly necessary.")
    parts.append(
        "Output ONLY the file contents — no markdown code fences, no prose explanations "
        "before or after the file."
    )
    return "\n".join(parts)


class DevOpsTab(BaseTab):
    """Generate DevOps templates."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: SimpleWorker | None = None
        self._pending_filename: str = "Dockerfile"
        self._build_ui()

    # ── UI Construction ───────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([700, 700])
        layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration
        self.cfg_group = QGroupBox(t("devops.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("devops.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Kind + Target
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_kind = self.section_label(t("devops.kind_label"))
        self.kind_combo = QComboBox()
        self.kind_combo.setMinimumHeight(32)
        for kind_id, kind_def in KINDS.items():
            self.kind_combo.addItem(t(kind_def["key"]), userData=kind_id)

        self.lbl_target = self.section_label(t("devops.target_label"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumHeight(32)
        for target_id, key in TARGETS.items():
            self.target_combo.addItem(t(key), userData=target_id)
        self.target_combo.setCurrentIndex(2)  # default: prod

        row1.addWidget(self.lbl_kind)
        row1.addWidget(self.kind_combo, 1)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_target)
        row1.addWidget(self.target_combo, 1)
        cfg_layout.addLayout(row1)

        # Options
        opts1 = QHBoxLayout()
        self.chk_multistage  = QCheckBox(t("devops.include_multistage"))
        self.chk_multistage.setChecked(True)
        self.chk_healthcheck = QCheckBox(t("devops.include_healthcheck"))
        self.chk_healthcheck.setChecked(True)
        opts1.addWidget(self.chk_multistage)
        opts1.addWidget(self.chk_healthcheck)
        opts1.addStretch()
        cfg_layout.addLayout(opts1)

        opts2 = QHBoxLayout()
        self.chk_security = QCheckBox(t("devops.include_security"))
        self.chk_security.setChecked(True)
        self.chk_caching  = QCheckBox(t("devops.include_caching"))
        self.chk_caching.setChecked(True)
        opts2.addWidget(self.chk_security)
        opts2.addWidget(self.chk_caching)
        opts2.addStretch()
        cfg_layout.addLayout(opts2)

        opts3 = QHBoxLayout()
        self.chk_comments = QCheckBox(t("devops.include_comments"))
        self.chk_comments.setChecked(True)
        opts3.addWidget(self.chk_comments)
        opts3.addStretch()
        cfg_layout.addLayout(opts3)

        layout.addWidget(self.cfg_group)

        # Input
        self.input_group = QGroupBox(t("devops.context_label"))
        in_layout = QVBoxLayout(self.input_group)
        in_layout.setSpacing(6)

        in_header = QHBoxLayout()
        self.paste_btn = QPushButton("📋 " + t("common.paste"))
        self.clear_input_btn = QPushButton(t("common.clear"))
        for b in (self.paste_btn, self.clear_input_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
        self.paste_btn.clicked.connect(self._paste_input)
        self.clear_input_btn.clicked.connect(lambda: self.input_view.clear())
        in_header.addStretch()
        in_header.addWidget(self.paste_btn)
        in_header.addWidget(self.clear_input_btn)
        in_layout.addLayout(in_header)

        self.input_view = QPlainTextEdit()
        self.input_view.setPlaceholderText(t("devops.context_placeholder"))
        self.input_view.setFont(QFont("JetBrains Mono", 10))
        self.input_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 10px;
                selection-background-color: {P['primary']};
            }}
            QPlainTextEdit:focus {{ border-color: {P['primary']}; }}
        """)
        self.input_highlighter = CodeHighlighter(self.input_view.document())
        in_layout.addWidget(self.input_view)

        layout.addWidget(self.input_group, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.run_btn = QPushButton(t("devops.run_btn"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.run_btn.clicked.connect(self._start_run)
        self.stop_btn = QPushButton(t("common.stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_run)
        btn_row.addWidget(self.run_btn, 4)
        btn_row.addWidget(self.stop_btn, 1)
        layout.addLayout(btn_row)

        return panel

    def _build_right_panel(self) -> QWidget:
        self.output = OutputPanel()
        self.output.copy_requested.connect(self._copy_result)
        self.output.save_requested.connect(self._save_result)
        return self.output

    # ── Actions ───────────────────────────────────────────
    def _paste_input(self):
        text = QApplication.clipboard().text()
        if text:
            self.input_view.setPlainText(text)

    def _copy_result(self):
        text = self.output.get_result_text()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit(t("common.copied"), "ok")

    def _save_result(self):
        text = self.output.get_result_text()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.save"), self._pending_filename, "All Files (*.*)"
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.status_signal.emit(f"Saved: {Path(path).name}", "ok")
            except OSError as e:
                QMessageBox.warning(self, "—", f"Save failed: {e}")

    def _start_run(self):
        context = self.input_view.toPlainText().strip()
        if not context:
            QMessageBox.warning(self, "—", t("common.no_input"))
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        kind   = self.kind_combo.currentData()   or "dockerfile"
        target = self.target_combo.currentData() or "prod"

        kind_def = KINDS[kind]

        system_prompt = build_system_prompt(
            kind=kind,
            target=target,
            multistage=self.chk_multistage.isChecked(),
            healthcheck=self.chk_healthcheck.isChecked(),
            security=self.chk_security.isChecked(),
            caching=self.chk_caching.isChecked(),
            comments=self.chk_comments.isChecked(),
        )
        user_prompt = f"Project context:\n\n{context}"

        config = {
            "provider_id":   provider_id,
            "model":         self.settings.get_model(provider_id, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.3,
            "max_tokens":    4096,
            "strip_fences":  kind_def["strip"],
            "log_label":     kind_def["log"],
        }

        self._pending_filename = kind_def["filename"]

        # Reset UI
        self.output.clear()
        self.output.show_processing()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        self._worker = SimpleWorker(config)
        self._worker.log_signal.connect(self.output.log)
        self._worker.progress_signal.connect(self.output.set_progress)
        self._worker.result_signal.connect(self._on_result)
        self._worker.done_signal.connect(self._on_done)
        self._worker.start()

    def _stop_run(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_result(self, text: str):
        self.output.set_result(text, self._pending_filename)

    def _on_done(self, success: bool, message: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self.status_signal.emit(t("status.complete"), "ok")
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.warning(self, t("status.error"), message)

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.cfg_group.setTitle(t("devops.title"))
        self.lbl_subtitle.setText(t("devops.subtitle"))
        self.lbl_kind.setText(t("devops.kind_label"))
        self.lbl_target.setText(t("devops.target_label"))
        self.input_group.setTitle(t("devops.context_label"))
        self.input_view.setPlaceholderText(t("devops.context_placeholder"))
        self.chk_multistage.setText(t("devops.include_multistage"))
        self.chk_healthcheck.setText(t("devops.include_healthcheck"))
        self.chk_security.setText(t("devops.include_security"))
        self.chk_caching.setText(t("devops.include_caching"))
        self.chk_comments.setText(t("devops.include_comments"))
        self.run_btn.setText(t("devops.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.paste_btn.setText("📋 " + t("common.paste"))
        self.clear_input_btn.setText(t("common.clear"))

        # Re-translate combos (preserve selection)
        cur_kind = self.kind_combo.currentData()
        self.kind_combo.clear()
        for kind_id, kind_def in KINDS.items():
            self.kind_combo.addItem(t(kind_def["key"]), userData=kind_id)
        idx = self.kind_combo.findData(cur_kind)
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)

        cur_target = self.target_combo.currentData()
        self.target_combo.clear()
        for target_id, key in TARGETS.items():
            self.target_combo.addItem(t(key), userData=target_id)
        idx = self.target_combo.findData(cur_target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)

        self.output.retranslate()
