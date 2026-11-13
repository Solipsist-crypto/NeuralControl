"""
Темна нейро-тема для NeuralControl.
"""

COLORS = {
    "bg":           "#0a0e1a",
    "panel":        "#131826",
    "card":         "#1a2138",
    "border":       "#2a3350",
    "accent":       "#00d4ff",
    "accent2":      "#7c3aed",
    "success":      "#00ff88",
    "warning":      "#ffaa00",
    "danger":       "#ff3366",
    "text":         "#e2e8f0",
    "text_dim":     "#64748b",
}


DARK_STYLE = f"""
QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 14px;
}}

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['panel']};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS['panel']};
    color: {COLORS['text_dim']};
    padding: 10px 22px;
    margin-right: 4px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['card']};
    color: {COLORS['accent']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTabBar::tab:hover {{
    color: {COLORS['text']};
}}

QPushButton {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COLORS['panel']};
    border-color: {COLORS['accent']};
    color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
}}

QPushButton:disabled {{
    color: {COLORS['text_dim']};
    border-color: {COLORS['border']};
}}

QGroupBox {{
    background-color: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: {COLORS['accent']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['accent']};
}}

QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}

QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['bg']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['card']};
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
}}

QTableWidget {{
    background-color: {COLORS['panel']};
    color: {COLORS['text']};
    gridline-color: {COLORS['border']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
}}

QHeaderView::section {{
    background-color: {COLORS['card']};
    color: {COLORS['accent']};
    border: 1px solid {COLORS['border']};
    padding: 6px;
    font-weight: 600;
}}

QScrollBar:vertical {{
    background: {COLORS['panel']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
    background: {COLORS['card']};
}}

QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
"""