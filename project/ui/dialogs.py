"""Diálogos adicionales para la aplicación METAR."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class MessageDialog(QDialog):
    """Diálogo simple para mostrar mensajes."""

    def __init__(self, title: str, message: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(message))
        btn = QPushButton("Aceptar")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)
