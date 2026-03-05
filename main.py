"""
Entry point — launch the Radar GUI application.
"""
import sys
import os

# Ensure the project root is on sys.path so package imports work
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor('#2b2b2b'))
    palette.setColor(QPalette.WindowText,      Qt.white)
    palette.setColor(QPalette.Base,            QColor('#1e1e1e'))
    palette.setColor(QPalette.AlternateBase,   QColor('#2b2b2b'))
    palette.setColor(QPalette.ToolTipBase,     Qt.white)
    palette.setColor(QPalette.ToolTipText,     Qt.white)
    palette.setColor(QPalette.Text,            Qt.white)
    palette.setColor(QPalette.Button,          QColor('#3c3c3c'))
    palette.setColor(QPalette.ButtonText,      Qt.white)
    palette.setColor(QPalette.BrightText,      Qt.red)
    palette.setColor(QPalette.Highlight,       QColor('#2a5a8a'))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    return palette


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(_dark_palette())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
