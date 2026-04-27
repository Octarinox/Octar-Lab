"""
core/workers/generation_worker.py
══════════════════════════════════════════════════════════════
Background QThread that drives the architect tab's generation
pipeline. Decoupled from the UI through Qt signals so the
same worker can be reused by other tabs in the future.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.ai_providers.base import ProviderError
from core.ai_providers.factory import ProviderFactory
from core.config import APP_NAME


class GenerationWorker(QThread):
    """
    Two-stage generation:
      1) Ask the architect model for a JSON project plan.
      2) Generate each file in the plan with the coder model.
    """

    log_signal      = pyqtSignal(str, str)   # (message, level)
    progress_signal = pyqtSignal(int)
    file_signal     = pyqtSignal(str, str)   # (full_path, content)
    tree_signal     = pyqtSignal(dict)
    done_signal     = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self._config = config
        self._stop = False

    def stop(self):
        self._stop = True

    # ── Internal logging shortcut ─────────────────────────
    def _log(self, msg: str, level: str = "INFO"):
        self.log_signal.emit(msg, level)

    # ── Main thread entry point ───────────────────────────
    def run(self):
        try:
            self._generate()
        except ProviderError as e:
            self._log(f"Provider error: {e}", "ERR")
            self.done_signal.emit(False, str(e))
        except Exception as e:
            self._log(f"Unexpected error: {e}", "ERR")
            self.done_signal.emit(False, str(e))

    # ── Generation pipeline ───────────────────────────────
    def _generate(self):
        cfg          = self._config
        name         = cfg["name"]
        description  = cfg["description"]
        language     = cfg["language"]
        temperature  = cfg["temperature"]
        max_files    = cfg["max_files"]
        output_dir   = Path(cfg["output_dir"])
        provider_id  = cfg["provider_id"]
        architect_m  = cfg["architect_model"]
        coder_m      = cfg["coder_model"]

        # 1. Initialise the AI provider
        self._log(f"Initialising {provider_id}…", "AI")
        provider = ProviderFactory.create(provider_id)
        self._log(f"Provider ready: {provider.INFO.display_name}", "OK")
        self.progress_signal.emit(5)

        if self._stop:
            return

        # 2. Generate the architecture plan
        self._log(f"Asking architect ({architect_m}) to design the project…", "AI")
        arch_prompt = self._architect_prompt(name, description, language, max_files)
        raw_plan = provider.chat_simple(
            prompt=arch_prompt,
            model=architect_m,
            temperature=0.3,  # plan should be more deterministic
            max_tokens=4096,
        )
        self.progress_signal.emit(20)

        plan = self._parse_json(raw_plan)
        if not plan:
            raise RuntimeError("Architect did not return parseable JSON")

        self.tree_signal.emit(plan)
        files = plan.get("files", [])
        self._log(f"Project plan parsed — {len(files)} files queued", "OK")
        self.progress_signal.emit(25)

        if not files:
            raise RuntimeError("Architect returned an empty file list")

        # 3. Generate the actual project files
        out_base = output_dir / self._sanitize(name)
        out_base.mkdir(parents=True, exist_ok=True)
        self._log(f"Writing into: {out_base}", "FILE")

        deps = plan.get("dependencies", {}) or {}
        gitignore_extra = plan.get("git_ignore_patterns", []) or []
        n = len(files)

        for i, finfo in enumerate(files):
            if self._stop:
                self._log("Stopped by user", "WARN")
                break

            rel_path = finfo.get("path") or f"file_{i}.txt"
            purpose  = finfo.get("purpose", "")
            ftype    = finfo.get("type", "source")

            self.progress_signal.emit(25 + int((i / n) * 65))
            self._log(f"[{i+1}/{n}] {rel_path}", "FILE")

            full_path = out_base / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Special-case readme/deps/gitignore so we don't burn tokens on them
            if rel_path == "README.md" and cfg.get("gen_readme"):
                content = self._gen_readme(plan, name, description, language)
            elif self._is_dep_file(rel_path) and cfg.get("gen_deps"):
                content = self._gen_deps_file(rel_path, deps, name)
            elif rel_path == ".gitignore":
                content = self._gen_gitignore(gitignore_extra, language)
            else:
                content = self._gen_file(
                    provider, coder_m, rel_path, purpose,
                    language, name, description, ftype, temperature,
                )

            content = self._strip_code_fences(content)

            try:
                full_path.write_text(content, encoding="utf-8")
                self.file_signal.emit(str(full_path), content)
                self._log(f"   ✓ {len(content)} chars", "OK")
            except OSError as e:
                self._log(f"   ✗ Write failed: {e}", "ERR")

        if self._stop:
            self.done_signal.emit(False, "Stopped by user")
            return

        # 4. Optional git init
        self.progress_signal.emit(92)
        if cfg.get("git_init"):
            self._git_init(out_base)

        self.progress_signal.emit(100)
        self._log(f"🎉 Project '{name}' complete: {out_base}", "OK")
        self.done_signal.emit(True, str(out_base.resolve()))

    # ── Prompt builders ───────────────────────────────────
    def _architect_prompt(self, name: str, desc: str, lang: str, max_files: int) -> str:
        return f"""You are an elite software architect. Design a complete, production-ready project.

PROJECT:
- Name: {name}
- Language/Framework: {lang}
- Description: {desc}
- Maximum files: {max_files}

Return ONLY valid JSON (no markdown fences, no commentary). Schema:
{{
  "project_name": "{name}",
  "language": "{lang}",
  "description": "...",
  "files": [
    {{"path": "relative/path/file.ext", "purpose": "what this file does", "type": "source|config|docs|test|asset"}}
  ],
  "dependencies": {{"runtime": [], "dev": []}},
  "git_ignore_patterns": [],
  "readme_sections": ["Overview", "Installation", "Usage", "API", "Contributing", "License"]
}}

Constraints:
- ≤ {max_files} files
- Use idiomatic structure for {lang}
- Include src/, tests/, docs/ folders where appropriate
- Always include README.md and .gitignore
- Always include a dependency file (requirements.txt, package.json, Cargo.toml, go.mod, …)
"""

    def _gen_file(self, provider, model: str, path: str, purpose: str,
                  language: str, project: str, desc: str, ftype: str,
                  temperature: float) -> str:
        prompt = f"""Generate complete, production-ready code for this file:

File:        {path}
Purpose:     {purpose}
Project:     {project}
Language:    {language}
Description: {desc}
File type:   {ftype}

Requirements:
- Write COMPLETE, working code (no placeholders, no TODOs)
- Follow {language} best practices and idioms
- Include proper error handling and concise inline comments
- Do NOT include markdown code fences (no triple backticks)
- Do NOT include any explanation outside the code
- For config files, use the proper format (TOML, JSON, YAML, etc.)
"""
        try:
            return provider.chat_simple(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=4096,
            )
        except ProviderError as e:
            self._log(f"   ⚠ AI error for {path}: {e}", "WARN")
            return f"# Generation failed for {path}\n# Error: {e}\n"

    # ── README / deps / gitignore generators ──────────────
    @staticmethod
    def _gen_readme(plan: dict, name: str, desc: str, language: str) -> str:
        deps = plan.get("dependencies", {}) or {}
        rt   = ", ".join(deps.get("runtime", [])) or "None"
        dv   = ", ".join(deps.get("dev", []))     or "None"
        year = datetime.datetime.now().year
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        return f"""# {name}

> {desc}

[![Language](https://img.shields.io/badge/language-{language.replace(' ', '_')}-8b5cf6)]()
[![License](https://img.shields.io/badge/license-MIT-10b981)]()
[![Status](https://img.shields.io/badge/status-active-10b981)]()

## Overview

{desc}

Generated by **{APP_NAME}** — open-source AI-powered project scaffolding.

## Installation

See language-specific instructions inside the relevant config file.

## Dependencies

- **Runtime:** {rt}
- **Dev:** {dv}

## Usage

See `examples/` or `docs/` for usage patterns.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License

MIT © {year}

---
*Generated on {date}*
"""

    @staticmethod
    def _gen_deps_file(path: str, deps: dict, name: str) -> str:
        runtime = deps.get("runtime", []) or []
        dev     = deps.get("dev", [])     or []
        fname   = Path(path).name

        if fname == "requirements.txt":
            lines = list(runtime)
            if dev:
                lines.append("")
                lines.append("# Dev dependencies")
                lines.extend(dev)
            return "\n".join(lines) + "\n"

        if fname == "package.json":
            data = {
                "name": name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "description": f"{name} project",
                "main": "index.js",
                "scripts": {"test": "jest", "build": "tsc", "lint": "eslint ."},
                "dependencies":    {d: "latest" for d in runtime},
                "devDependencies": {d: "latest" for d in dev},
                "license": "MIT",
            }
            return json.dumps(data, indent=2) + "\n"

        if fname == "Cargo.toml":
            lines = [
                "[package]",
                f'name = "{name.lower().replace(" ", "_")}"',
                'version = "0.1.0"',
                'edition = "2021"',
                "",
                "[dependencies]",
            ]
            for d in runtime:
                lines.append(f'{d} = "*"')
            return "\n".join(lines) + "\n"

        if fname == "go.mod":
            slug = name.lower().replace(" ", "-")
            return f"module github.com/user/{slug}\n\ngo 1.21\n"

        if fname == "pom.xml":
            slug = name.lower().replace(" ", "-")
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.octarinox</groupId>
  <artifactId>{slug}</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>
"""

        return f"# Dependencies for {name}\n" + "\n".join(runtime) + "\n"

    @staticmethod
    def _gen_gitignore(extra: list[str], language: str) -> str:
        defaults = {
            "python":     ["__pycache__/", "*.pyc", ".venv/", "venv/", "dist/", "build/", "*.egg-info/"],
            "javascript": ["node_modules/", "dist/", ".env", "*.log", ".DS_Store"],
            "typescript": ["node_modules/", "dist/", ".env", "*.log", "*.js.map"],
            "go":         ["*.exe", "*.test", "vendor/", ".env"],
            "rust":       ["target/", "Cargo.lock", "*.rlib"],
            "java":       ["*.class", "*.jar", "target/", ".idea/", "*.iml"],
            "c":          ["*.o", "*.out", "*.exe", "build/"],
        }
        lower = language.lower()
        base = ["# Generated by Octar Lab", ""]
        matched = False
        for k, v in defaults.items():
            if k in lower:
                base.extend(v)
                matched = True
                break
        if not matched:
            base.extend(["*.log", ".env", ".DS_Store", "Thumbs.db"])
        if extra:
            base.extend(["", "# Project-specific"])
            base.extend(extra)
        base.extend(["", "# IDEs", ".vscode/", ".idea/", "*.swp", "*.swo", ""])
        return "\n".join(base)

    # ── Helpers ───────────────────────────────────────────
    @staticmethod
    def _git_init(path: Path):
        if not shutil.which("git"):
            return
        try:
            subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
            subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "🚀 Initial commit — Octar Lab"],
                cwd=path, capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        # Strip markdown fences if the model added them despite instructions
        clean = re.sub(r'```(?:json)?\s*', '', text)
        clean = re.sub(r'```\s*$', '', clean, flags=re.MULTILINE).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass
        # Fallback: extract the largest JSON object from the response
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        content = re.sub(r'^```[\w]*\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*$',       '', content, flags=re.MULTILINE)
        return content.strip() + "\n"

    @staticmethod
    def _sanitize(name: str) -> str:
        return re.sub(r'[^\w\-]', '_', name).strip('_') or "project"

    @staticmethod
    def _is_dep_file(path: str) -> bool:
        return Path(path).name in (
            "requirements.txt", "package.json", "Cargo.toml",
            "go.mod", "pom.xml", "Gemfile", "build.gradle",
        )
