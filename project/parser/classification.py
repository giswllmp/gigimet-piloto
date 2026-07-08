"""Clasificación de condiciones de vuelo y cálculo de ceiling."""

from __future__ import annotations

from typing import List, Optional


def determine_ceiling(sky_layers: List[str]) -> Optional[int]:
    """Determina el ceiling en pies según la capa BKN, OVC o VV más baja."""
    if not sky_layers:
        return None

    heights = []
    for layer in sky_layers:
        layer_upper = layer.upper()
        if any(layer_upper.startswith(t) for t in ["BKN", "OVC", "VV"]):
            try:
                altitude_str = layer_upper.replace("BKN", "").replace("OVC", "").replace("VV", "")
                if altitude_str.isdigit():
                    altitude = int(altitude_str)
                    heights.append(altitude * 100)
            except (ValueError, IndexError):
                pass

    return min(heights) if heights else None


def classify_flight_category(visibility_km: Optional[float], ceiling_ft: Optional[int]) -> str:
    """Clasifica las condiciones de vuelo según visibilidad y ceiling."""
    if visibility_km is None and ceiling_ft is None:
        return "UNKNOWN"
    if visibility_km is not None and visibility_km < 1.6:
        return "LIFR"
    if ceiling_ft is not None and ceiling_ft < 500:
        return "LIFR"
    if visibility_km is not None and visibility_km < 5.0:
        return "IFR"
    if ceiling_ft is not None and ceiling_ft < 1000:
        return "IFR"
    if visibility_km is not None and visibility_km < 8.0:
        return "MVFR"
    if ceiling_ft is not None and ceiling_ft < 3000:
        return "MVFR"
    return "VFR"
