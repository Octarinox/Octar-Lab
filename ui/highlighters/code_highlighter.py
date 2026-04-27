"""
ui/highlighters/code_highlighter.py
══════════════════════════════════════════════════════════════
A pragmatic, multi-language syntax highlighter that recognises
keywords from the most common languages we generate. Not a
full lexer — just enough to make the preview pleasant to read.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re

from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from ui.theme import PALETTE as P


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class CodeHighlighter(QSyntaxHighlighter):
    """Generic, language-agnostic syntax highlighter."""

    KEYWORDS = (
        # Python
        r'def|class|import|from|return|if|else|elif|for|while|try|except|'
        r'finally|with|as|pass|break|continue|lambda|yield|async|await|raise|'
        # Rust
        r'fn|let|mut|pub|use|mod|impl|struct|enum|trait|match|loop|where|'
        r'unsafe|extern|crate|self|Self|'
        # Go
        r'func|var|const|type|interface|package|defer|go|chan|select|'
        # JS/TS
        r'function|new|this|null|undefined|true|false|export|import|'
        r'extends|implements|instanceof|typeof|delete|in|of|switch|case|default|'
        # Java/C#/C++
        r'public|private|protected|static|void|int|string|bool|long|short|'
        r'namespace|using|virtual|override|abstract|final|sealed|readonly|'
        # SQL fragments often appear in generated code
        r'SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|JOIN|GROUP|ORDER|BY|HAVING'
    )

    BUILTINS = (
        r'True|False|None|null|nil|undefined|self|this|super|cls|'
        r'console|print|println|printf|len|range|map|filter|reduce'
    )

    def __init__(self, document):
        super().__init__(document)
        self._rules = self._build_rules()

    def _build_rules(self) -> list[tuple[re.Pattern, QTextCharFormat]]:
        rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        keyword_fmt    = _fmt(P['primary_hover'], bold=True)
        builtin_fmt    = _fmt(P['accent_pink'])
        string_fmt     = _fmt(P['success'])
        number_fmt     = _fmt(P['warning'])
        comment_fmt    = _fmt(P['text_dim'], italic=True)
        function_fmt   = _fmt(P['accent_cyan'], bold=True)
        bracket_fmt    = _fmt(P['accent'])
        decorator_fmt  = _fmt(P['accent_pink'], italic=True)
        operator_fmt   = _fmt(P['text_sec'])

        rules.append((re.compile(rf'\b({self.KEYWORDS})\b'),         keyword_fmt))
        rules.append((re.compile(rf'\b({self.BUILTINS})\b'),         builtin_fmt))
        rules.append((re.compile(r'@\w+'),                            decorator_fmt))
        rules.append((re.compile(r'"(?:[^"\\]|\\.)*"'),               string_fmt))
        rules.append((re.compile(r"'(?:[^'\\]|\\.)*'"),               string_fmt))
        rules.append((re.compile(r'`(?:[^`\\]|\\.)*`'),               string_fmt))
        rules.append((re.compile(r'\b\d+(\.\d+)?\b'),                 number_fmt))
        rules.append((re.compile(r'#[^\n]*'),                         comment_fmt))
        rules.append((re.compile(r'//[^\n]*'),                        comment_fmt))
        rules.append((re.compile(r'/\*.*?\*/', re.DOTALL),            comment_fmt))
        rules.append((re.compile(r'(?<=def\s)\w+|(?<=fn\s)\w+|(?<=function\s)\w+'),
                                                                       function_fmt))
        rules.append((re.compile(r'[(){}\[\]]'),                       bracket_fmt))
        rules.append((re.compile(r'[+\-*/=<>!&|^%]+'),                 operator_fmt))
        return rules

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
