"""Tabla interactiva para visualizar registros METAR/SPECI."""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from utils.variables import variable_label_with_unit


class AdvancedTable(QTableWidget):
    """Tabla con ordenamiento, seleccion por fila y color por categoria."""

    CATEGORY_COLORS = {
        "VFR": "#48bb78",
        "MVFR": "#4299e1",
        "IFR": "#ed8936",
        "LIFR": "#f56565",
        "UNKNOWN": "#a0aec0",
    }

    DISPLAY_COLUMNS = [
        ("report_type", "Reporte"),
        ("datetime", "Fecha y Hora"),
        ("station", "Estación"),
        ("temperature", variable_label_with_unit("temperature")),
        ("dewpoint", variable_label_with_unit("dewpoint")),
        ("humidity", variable_label_with_unit("humidity")),
        ("pressure", variable_label_with_unit("pressure")),
        ("wind_dir", variable_label_with_unit("wind_dir")),
        ("wind_speed", variable_label_with_unit("wind_speed")),
        ("gust", variable_label_with_unit("gust")),
        ("visibility", variable_label_with_unit("visibility")),
        ("clouds", "Nubosidad"),
        ("ceiling_ft", variable_label_with_unit("ceiling_ft")),
        ("weather", "Fenomeno"),
        ("flight_category", "Categoria de vuelo"),
        ("delta_TTd", variable_label_with_unit("delta_TTd")),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setColumnCount(0)
        self.setRowCount(0)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

    def load_dataframe(self, df: pd.DataFrame, max_rows: int = 2000) -> None:
        """Carga un DataFrame en la tabla respetando columnas de auditoria."""
        self.setSortingEnabled(False)
        visible_df, headers = self._display_dataframe(df.head(max_rows))
        self.setColumnCount(len(visible_df.columns))
        self.setRowCount(len(visible_df))
        self.setHorizontalHeaderLabels(headers)

        for row_idx, (_, row) in enumerate(visible_df.iterrows()):
            for col_idx, column in enumerate(visible_df.columns):
                value = row[column]
                text = "-" if pd.isna(value) else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setFont(QFont("Segoe UI", 10))

                if str(column) == "flight_category":
                    item.setForeground(QColor(self.CATEGORY_COLORS.get(text, "#cbd5e0")))
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

                self.setItem(row_idx, col_idx, item)

        for col in range(len(visible_df.columns)):
            self.resizeColumnToContents(col)
        self.setSortingEnabled(True)

    def get_selected_row(self) -> dict:
        """Devuelve la fila seleccionada como diccionario."""
        if not self.selectedIndexes():
            return {}

        row_idx = self.selectedIndexes()[0].row()
        result = {}
        for col_idx in range(self.columnCount()):
            header_item = self.horizontalHeaderItem(col_idx)
            value_item = self.item(row_idx, col_idx)
            if header_item is not None and value_item is not None:
                result[header_item.text()] = value_item.text()
        return result

    def _display_dataframe(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        columns = [column for column, _ in self.DISPLAY_COLUMNS if column in df.columns]
        headers = [label for column, label in self.DISPLAY_COLUMNS if column in df.columns]
        return df[columns], headers
