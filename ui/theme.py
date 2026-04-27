"""
ui/theme.py
══════════════════════════════════════════════════════════════
Centralised color palette and typography for OCTAR LAB.
Theme is "Cosmic Violet" — deep black/charcoal backgrounds
with violet primary and lilac accents.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

# ── Color Palette ─────────────────────────────────────────────
PALETTE = {
    # Surfaces (darkest → lightest)
    "bg_void":       "#08080f",
    "bg_deep":       "#0d0a17",
    "bg_panel":      "#13111c",
    "bg_card":       "#1a1626",
    "bg_hover":      "#241d35",
    "bg_elevated":   "#2a2240",

    # Borders
    "border":        "#2d2438",
    "border_strong": "#3d3052",
    "border_glow":   "#5b21b6",

    # Primary violet (brand)
    "primary":       "#8b5cf6",
    "primary_hover": "#a78bfa",
    "primary_deep":  "#6d28d9",
    "primary_dim":   "#4c1d95",

    # Accents
    "accent":        "#c4b5fd",
    "accent_pink":   "#e879f9",
    "accent_cyan":   "#22d3ee",

    # Status
    "success":       "#10b981",
    "warning":       "#f59e0b",
    "danger":        "#f43f5e",
    "info":          "#60a5fa",

    # Text
    "text_prim":     "#f1f5f9",
    "text_sec":      "#a1a1aa",
    "text_dim":      "#52525b",
    "text_code":     "#c4b5fd",
    "text_disabled": "#3f3f46",
}


# ── Typography ─────────────────────────────────────────────
FONT_STACK_MONO = (
    "'JetBrains Mono', 'Fira Code', 'Cascadia Code', "
    "'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace"
)
FONT_STACK_UI = (
    "'Inter', 'SF Pro Display', 'Segoe UI', "
    "'Helvetica Neue', Arial, sans-serif"
)

FONT_SIZE_BASE     = 13
FONT_SIZE_SMALL    = 11
FONT_SIZE_LARGE    = 15
FONT_SIZE_XLARGE   = 18
FONT_SIZE_HEADER   = 22


def color(name: str, fallback: str = "#ffffff") -> str:
    """Safe palette lookup."""
    return PALETTE.get(name, fallback)


def with_alpha(hex_color: str, alpha: int) -> str:
    """
    Append an alpha channel to a #rrggbb color → #rrggbbaa.
    alpha is 0-255.
    """
    if not hex_color.startswith("#"):
        return hex_color
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return f"#{hex_color}{alpha:02x}"
    return f"#{hex_color}"
