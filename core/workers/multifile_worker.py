from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.ai_providers.base import ProviderError
from core.ai_providers.factory import ProviderFactory
from core.workers.base_worker import BaseWorker


# Per-kind copy used in prompts. Keeps the prompts focused so the
# model knows whether to design a "library" vs a "component" vs a
# "schema package".
_KIND_DESCRIPTIONS = {
    "library":   "a focused, single-purpose library (not a full application)",
    "component": "a self-contained UI component or small set of related components",
    "schema":   "a database schema package — DDL, migrations, optional seed data",
    "module":   "a single coherent module with closely-related files",
}


class MultiFileWorker(BaseWorker):
    """Generic multi-file generator with plan → per-file pipeline."""

    def _run(self):
        cfg = self._config

        name             = cfg["name"]
        description      = cfg["description"]
        language         = cfg["language"]
        kind             = cfg.get("kind", "module")
        extra_inst       = cfg.get("extra_instructions", "")
        max_files        = cfg.get("max_files", 8)
        temperature      = cfg.get("temperature", 0.4)
        output_dir       = Path(cfg["output_dir"])
        provider_id      = cfg["provider_id"]
        architect_model  = cfg["architect_model"]
        coder_model      = cfg["coder_model"]

        # 1. Provider initialisation
        self._log(f"Initialising {provider_id}…", "AI")
        provider = ProviderFactory.create(provider_id)
        self._log(f"Provider ready: {provider.INFO.display_name}", "OK")
        self._progress(5)

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        # 2. Architecture plan
        kind_desc = _KIND_DESCRIPTIONS.get(kind, _KIND_DESCRIPTIONS["module"])
        self._log(f"Designing {kind} structure with {architect_model}…", "AI")
        plan_prompt = self._plan_prompt(
            name, description, language, kind_desc, extra_inst, max_files,
        )
        raw_plan = provider.chat_simple(
            prompt=plan_prompt,
            model=architect_model,
            temperature=0.3,  # plan: more deterministic
            max_tokens=2048,
        )
        self._progress(20)

        plan = self.extract_json(raw_plan)
        if not plan:
            raise RuntimeError("Architect did not return parseable JSON")

        files = plan.get("files", [])
        if not files:
            raise RuntimeError("Architect returned an empty file list")

        self._log(f"Plan parsed: {len(files)} files queued", "OK")
        self._progress(25)

        # 3. Per-file generation
        out_base = output_dir / self._sanitize(name)
        out_base.mkdir(parents=True, exist_ok=True)
        self._log(f"Writing into: {out_base}", "FILE")

        n = len(files)
        for i, finfo in enumerate(files):
            if self.is_stopping:
                self._log("Stopped by user", "WARN")
                break

            rel_path = finfo.get("path") or f"file_{i}.txt"
            purpose  = finfo.get("purpose", "")

            self._progress(25 + int((i / n) * 70))
            self._log(f"[{i+1}/{n}] {rel_path}", "FILE")

            full_path = out_base / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = self._gen_file(
                    provider, coder_model, rel_path, purpose,
                    language, name, description, kind, temperature,
                )
                content = self.strip_code_fences(content) + "\n"
                full_path.write_text(content, encoding="utf-8")
                self.file_signal.emit(str(full_path), content)
                self._log(f"   ✓ {len(content)} chars", "OK")
            except ProviderError as e:
                self._log(f"   ⚠ AI error: {e}", "WARN")
            except OSError as e:
                self._log(f"   ✗ Write failed: {e}", "ERR")

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        self._progress(100)
        self._log(f"🎉 {kind.title()} '{name}' complete: {out_base}", "OK")
        self.done_signal.emit(True, str(out_base.resolve()))

    @staticmethod
    def _plan_prompt(name: str, desc: str, lang: str, kind_desc: str,
                     extra: str, max_files: int) -> str:
        extra_section = f"\nAdditional constraints:\n{extra}\n" if extra else ""
        return f"""You are an elite software architect. Design {kind_desc}.

TARGET:
- Name: {name}
- Language/Framework: {lang}
- Description: {desc}
- Maximum files: {max_files}
{extra_section}
Return ONLY valid JSON (no markdown fences, no commentary). Schema:
{{
  "name": "{name}",
  "language": "{lang}",
  "description": "...",
  "files": [
    {{"path": "relative/path/file.ext", "purpose": "what this file does"}}
  ]
}}

Constraints:
- ≤ {max_files} files
- Use idiomatic structure for {lang}
- Keep the scope tight — focus on the stated purpose, not a full app
- Always include a brief README.md (unless extra constraints say otherwise)
"""

    @staticmethod
    def _gen_file(provider, model, path, purpose, language,
                  parent_name, parent_desc, kind, temperature):
        prompt = f"""Generate complete, production-ready code for this file:

File:        {path}
Purpose:     {purpose}
Parent {kind}: {parent_name}
Language:    {language}
Context:     {parent_desc}

Requirements:
- Write COMPLETE, working code (no placeholders, no TODOs)
- Follow {language} best practices and idioms
- Include proper error handling and concise inline comments
- Do NOT include markdown code fences (no triple backticks)
- Do NOT include any explanation outside the code
"""
        return provider.chat_simple(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=4096,
        )

    @staticmethod
    def _sanitize(name: str) -> str:
        return re.sub(r'[^\w\-]', '_', name).strip('_') or "output"
