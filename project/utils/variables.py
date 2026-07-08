"""Metadatos de variables meteorologicas usadas por GigiMET."""

from __future__ import annotations


VARIABLE_LABELS = {
    "temperature": "Temperatura",
    "dewpoint": "Punto de rocio",
    "humidity": "Humedad relativa",
    "pressure": "Presion QNH",
    "wind_dir": "Direccion del viento",
    "wind_speed": "Velocidad del viento",
    "gust": "Rafaga",
    "visibility": "Visibilidad",
    "ceiling_ft": "Techo de nubes",
    "delta_TTd": "Diferencia T-Td",
}

VARIABLE_UNITS = {
    "temperature": "°C",
    "dewpoint": "°C",
    "humidity": "%",
    "pressure": "hPa",
    "wind_dir": "°",
    "wind_speed": "kt",
    "gust": "kt",
    "visibility": "km",
    "ceiling_ft": "ft",
    "delta_TTd": "°C",
}


def variable_label(column: str) -> str:
    return VARIABLE_LABELS.get(column, column)


def variable_unit(column: str) -> str:
    return VARIABLE_UNITS.get(column, "")


def variable_label_with_unit(column: str) -> str:
    label = variable_label(column)
    unit = variable_unit(column)
    return f"{label} ({unit})" if unit else label
