"""
ui/stylesheet.py
══════════════════════════════════════════════════════════════
Builds the application-wide Qt Style Sheet (QSS) from the
palette in ui/theme.py. Pulled out into its own module so the
palette and the styling rules can evolve independently.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from ui.theme import PALETTE as P, FONT_STACK_MONO


def build_stylesheet() -> str:
    return f"""
    /* ═══════════════════════════════════════════════════════ */
    /*   GLOBAL                                               */
    /* ═══════════════════════════════════════════════════════ */
    QMainWindow, QWidget, QDialog {{
        background-color: {P['bg_deep']};
        color: {P['text_prim']};
        font-family: {FONT_STACK_MONO};
        font-size: 13px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   GROUP BOX                                            */
    /* ═══════════════════════════════════════════════════════ */
    QGroupBox {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 10px;
        margin-top: 18px;
        padding: 14px 10px 10px 10px;
        font-weight: bold;
        color: {P['accent']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px; top: 4px;
        padding: 0 6px;
        color: {P['accent']};
        font-size: 11px;
        letter-spacing: 1px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   INPUTS                                               */
    /* ═══════════════════════════════════════════════════════ */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {P['text_prim']};
        selection-background-color: {P['primary']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {P['primary']};
        background-color: {P['bg_hover']};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        color: {P['text_disabled']};
        background-color: {P['bg_panel']};
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   COMBO BOX                                            */
    /* ═══════════════════════════════════════════════════════ */
    QComboBox {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {P['text_prim']};
        min-height: 22px;
    }}
    QComboBox:hover {{ border-color: {P['primary']}; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {P['accent']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {P['bg_card']};
        border: 1px solid {P['primary']};
        color: {P['text_prim']};
        selection-background-color: {P['primary']};
        border-radius: 8px;
        padding: 4px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   BUTTONS                                              */
    /* ═══════════════════════════════════════════════════════ */
    QPushButton {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 8px;
        padding: 9px 20px;
        color: {P['text_prim']};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {P['bg_hover']};
        border-color: {P['primary']};
        color: {P['accent']};
    }}
    QPushButton:pressed {{
        background-color: {P['primary']};
        color: white;
    }}
    QPushButton:disabled {{
        color: {P['text_disabled']};
        border-color: {P['border']};
        background-color: {P['bg_panel']};
    }}

    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {P['primary']}, stop:1 {P['primary_deep']});
        border: none;
        color: white;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 12px 32px;
        border-radius: 10px;
    }}
    QPushButton#primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {P['primary_hover']}, stop:1 {P['primary']});
    }}
    QPushButton#primary:disabled {{
        background: {P['bg_card']};
        color: {P['text_disabled']};
    }}

    QPushButton#danger {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {P['danger']}, stop:1 #b91c1c);
        border: none;
        color: white;
        font-weight: 700;
        border-radius: 10px;
    }}
    QPushButton#danger:hover {{ background: #dc2626; }}

    QPushButton#accent {{
        background-color: transparent;
        border: 1px solid {P['success']};
        color: {P['success']};
        border-radius: 8px;
        padding: 7px 16px;
    }}
    QPushButton#accent:hover {{
        background-color: {P['success']};
        color: {P['bg_deep']};
    }}

    QPushButton#ghost {{
        background-color: transparent;
        border: 1px solid {P['border']};
        color: {P['text_sec']};
        border-radius: 8px;
        padding: 7px 16px;
    }}
    QPushButton#ghost:hover {{
        border-color: {P['primary']};
        color: {P['accent']};
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   PROGRESS BAR                                         */
    /* ═══════════════════════════════════════════════════════ */
    QProgressBar {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 6px;
        text-align: center;
        color: {P['text_prim']};
        font-weight: bold;
        height: 22px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {P['primary_deep']}, stop:0.5 {P['primary']}, stop:1 {P['accent']});
        border-radius: 5px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   TABS                                                 */
    /* ═══════════════════════════════════════════════════════ */
    QTabWidget::pane {{
        background-color: {P['bg_panel']};
        border: 1px solid {P['border']};
        border-radius: 10px;
        top: -1px;
    }}
    QTabBar {{ qproperty-drawBase: 0; }}
    QTabBar::tab {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-bottom: none;
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
        color: {P['text_sec']};
        margin-right: 3px;
        font-weight: 600;
        min-width: 90px;
    }}
    QTabBar::tab:selected {{
        background-color: {P['primary']};
        color: white;
        border-color: {P['primary']};
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {P['bg_hover']};
        color: {P['text_prim']};
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   TREE WIDGET                                          */
    /* ═══════════════════════════════════════════════════════ */
    QTreeWidget {{
        background-color: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 8px;
        color: {P['text_prim']};
        alternate-background-color: {P['bg_hover']};
    }}
    QTreeWidget::item {{ padding: 4px 6px; border-radius: 4px; }}
    QTreeWidget::item:selected {{
        background-color: {P['primary']};
        color: white;
    }}
    QTreeWidget::item:hover:!selected {{ background-color: {P['bg_hover']}; }}
    QHeaderView::section {{
        background-color: {P['bg_panel']};
        color: {P['text_sec']};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {P['border']};
        font-weight: bold;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   SPLITTER                                             */
    /* ═══════════════════════════════════════════════════════ */
    QSplitter::handle {{ background-color: {P['border']}; }}
    QSplitter::handle:horizontal {{ width: 2px; }}
    QSplitter::handle:vertical   {{ height: 2px; }}
    QSplitter::handle:hover {{ background-color: {P['primary']}; }}

    /* ═══════════════════════════════════════════════════════ */
    /*   SCROLLBARS                                           */
    /* ═══════════════════════════════════════════════════════ */
    QScrollBar:vertical {{
        background: {P['bg_card']};
        width: 10px; border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {P['border_glow']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {P['primary']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: {P['bg_card']};
        height: 10px; border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {P['border_glow']};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {P['primary']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ═══════════════════════════════════════════════════════ */
    /*   CHECK BOX                                            */
    /* ═══════════════════════════════════════════════════════ */
    QCheckBox {{ color: {P['text_sec']}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {P['border']};
        border-radius: 4px;
        background: {P['bg_card']};
    }}
    QCheckBox::indicator:checked {{
        background: {P['primary']};
        border-color: {P['primary']};
    }}
    QCheckBox:hover {{ color: {P['text_prim']}; }}

    /* ═══════════════════════════════════════════════════════ */
    /*   SPIN / SLIDER                                        */
    /* ═══════════════════════════════════════════════════════ */
    QSpinBox {{
        background: {P['bg_card']};
        border: 1px solid {P['border']};
        border-radius: 6px;
        padding: 4px 8px;
        color: {P['text_prim']};
    }}
    QSpinBox:focus {{ border-color: {P['primary']}; }}

    QSlider::groove:horizontal {{
        background: {P['bg_card']};
        height: 6px;
        border-radius: 3px;
        border: 1px solid {P['border']};
    }}
    QSlider::handle:horizontal {{
        background: {P['primary']};
        width: 16px; height: 16px;
        border-radius: 8px;
        margin: -5px 0;
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {P['primary_deep']}, stop:1 {P['primary']});
        border-radius: 3px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   LABELS                                               */
    /* ═══════════════════════════════════════════════════════ */
    QLabel#header {{
        font-size: 22px; font-weight: 800;
        color: {P['text_prim']}; letter-spacing: 1px;
    }}
    QLabel#subtitle {{
        font-size: 11px; color: {P['accent']};
        letter-spacing: 2px;
    }}
    QLabel#section {{
        font-size: 11px; font-weight: 700;
        color: {P['text_sec']}; letter-spacing: 1.5px;
        padding: 2px 0;
    }}
    QLabel#hint {{ color: {P['text_dim']}; font-size: 11px; }}
    QLabel#error {{ color: {P['danger']}; }}
    QLabel#success {{ color: {P['success']}; }}

    /* ═══════════════════════════════════════════════════════ */
    /*   STATUS / MENU                                        */
    /* ═══════════════════════════════════════════════════════ */
    QStatusBar {{
        background-color: {P['bg_panel']};
        border-top: 1px solid {P['border']};
        color: {P['text_sec']};
        font-size: 11px;
        padding: 2px 8px;
    }}
    QMenuBar {{
        background-color: {P['bg_panel']};
        border-bottom: 1px solid {P['border']};
        color: {P['text_sec']};
    }}
    QMenuBar::item:selected {{
        background-color: {P['primary']};
        color: white;
        border-radius: 4px;
    }}
    QMenu {{
        background-color: {P['bg_card']};
        border: 1px solid {P['primary']};
        border-radius: 8px;
        padding: 4px;
        color: {P['text_prim']};
    }}
    QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 4px; }}
    QMenu::item:selected {{
        background-color: {P['primary']};
        color: white;
    }}
    QMenu::separator {{
        height: 1px;
        background: {P['border']};
        margin: 4px 8px;
    }}

    /* ═══════════════════════════════════════════════════════ */
    /*   TOOLTIP                                              */
    /* ═══════════════════════════════════════════════════════ */
    QToolTip {{
        background-color: {P['bg_elevated']};
        color: {P['text_prim']};
        border: 1px solid {P['primary']};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    """
