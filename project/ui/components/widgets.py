"""Componentes visuales reutilizables para la interfaz."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class Card(QFrame):
    """Tarjeta moderna con borde y padding."""

    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        if title:
            title_label = QLabel(title)
            title_font = QFont()
            title_font.setPointSize(13)
            title_font.setBold(True)
            title_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3)
            title_label.setFont(title_font)
            title_label.setObjectName("titleSection")
            layout.addWidget(title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        layout.addLayout(self.content_layout)
        self.setLayout(layout)

    def add_widget(self, widget: QWidget) -> None:
        """Añade un widget al contenido de la tarjeta."""
        self.content_layout.addWidget(widget)


class StatCard(QFrame):
    """Tarjeta de estadística con valor destacado."""

    def __init__(self, label: str, value: str, icon: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMaximumHeight(130)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(18, 14, 18, 14)

        header = QHBoxLayout()
        header.setSpacing(12)
        if icon:
            icon_label = QLabel(icon)
            icon_font = QFont()
            icon_font.setPointSize(22)
            icon_label.setFont(icon_font)
            header.addWidget(icon_label)

        label_widget = QLabel(label)
        label_font = QFont()
        label_font.setPointSize(12)
        label_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.2)
        label_widget.setFont(label_font)
        label_widget.setObjectName("labelSecondary")
        header.addWidget(label_widget)
        header.addStretch()

        value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        value_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(header)
        layout.addWidget(value_label)
        self.setLayout(layout)


class SectionTitle(QLabel):
    """Título de sección con estilo profesional."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("titleSection")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
        self.setFont(font)
        self.setMargin(0)
        self.setContentsMargins(0, 0, 0, 12)


class DescriptionText(QLabel):
    """Texto descriptivo con mejor legibilidad."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("labelSecondary")
        font = QFont()
        font.setPointSize(13)
        self.setFont(font)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("line-height: 1.6; margin: 0px;")


class SmallText(QLabel):
    """Texto pequeño para detalles."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("labelSmall")
        font = QFont()
        font.setPointSize(11)
        self.setFont(font)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


class HighlightedText(QLabel):
    """Texto destacado o de valor."""

    def __init__(self, text: str = "", color: str = "#4c72b0", parent=None) -> None:
        super().__init__(text, parent)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet(f"color: {color};")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
