"""Cálculos derivados para variables meteorológicas."""

from __future__ import annotations

from typing import Optional


def calculate_humidity(temperature: float, dewpoint: float) -> Optional[float]:
    """Calcula la humedad relativa a partir de temperatura y punto de rocío."""
    if temperature is None or dewpoint is None:
        return None
    try:
        ratio = 6.112 * pow(2.718281828459045, (17.67 * dewpoint) / (dewpoint + 243.5))
        saturation = 6.112 * pow(2.718281828459045, (17.67 * temperature) / (temperature + 243.5))
        humidity_value = (ratio / saturation) * 100.0
        return round(humidity_value, 1)
    except Exception:
        return None


def calculate_delta_t_td(temperature: float, dewpoint: float) -> Optional[float]:
    """Calcula la diferencia T - Td."""
    if temperature is None or dewpoint is None:
        return None
    return round(temperature - dewpoint, 1)
