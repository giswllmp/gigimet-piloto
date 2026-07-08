"""Punto de entrada principal para la aplicación METAR.

El módulo inicializa la interfaz gráfica y arranca el bucle de eventos.
"""

from ui.mainwindow import MainWindow
from PySide6.QtWidgets import QApplication
import sys


def main() -> int:
    """Inicia la aplicación PySide6."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

