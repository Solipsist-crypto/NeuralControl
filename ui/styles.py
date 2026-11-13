DARK_STYLE = """
QWidget {
    color: #e6f1ff;
    font-family: "Rajdhani", "Segoe UI", sans-serif;
    font-size: 14px;
}

#Root {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0e1a, stop:1 #0d1124);
    border: 1px solid rgba(0, 212, 255, 0.25);
    border-radius: 14px;
}

#TitleBar {
    background: transparent;
}

#AppTitle {
    color: #00d4ff;
    font-family: "Orbitron", "Segoe UI";
    font-size: 14px;
    font-weight: bold;
}

#WinBtn {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #6b7a99;
    font-size: 16px;
}
#WinBtn:hover { background: rgba(0, 212, 255, 0.12); color: #00d4ff; }
#WinBtn[danger="true"]:hover { background: rgba(255, 46, 151, 0.2); color: #ff2e97; }

#SidePanel {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
}

QGroupBox {
    border: 1px solid rgba(0, 212, 255, 0.18);
    border-radius: 10px;
    margin-top: 16px;
    padding: 15px 10px 10px 10px;
    font-family: "Orbitron", "Segoe UI";
    font-size: 11px;
    font-weight: bold;
    color: #00d4ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background: transparent;
    color: #6b7a99;
    padding: 10px 22px;
    border: none;
    font-weight: bold;
}
QTabBar::tab:selected {
    color: #00d4ff;
    border-bottom: 2px solid #00d4ff;
}
QTabBar::tab:hover {
    color: #e6f1ff;
}

QPushButton {
    background: rgba(0, 212, 255, 0.08);
    border: 1px solid rgba(0, 212, 255, 0.55);
    border-radius: 8px;
    padding: 8px 16px;
    color: #00d4ff;
    font-weight: bold;
}
QPushButton:hover { background: rgba(0, 212, 255, 0.18); border-color: #00d4ff; }
QPushButton:pressed { background: rgba(0, 212, 255, 0.30); }

QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid rgba(0, 212, 255, 0.5); background: transparent;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00d4ff, stop:1 #7c3aed);
    border-color: #00d4ff;
}
"""