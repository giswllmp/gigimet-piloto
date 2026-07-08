"""Catalogo local de aeropuertos peruanos para GigiMET."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MISSING_AIRPORT_NAME = "Aeropuerto no registrado"
MISSING_VALUE = "No disponible"


def _repair_text(value: Any) -> Any:
    """Corrige texto UTF-8 leido como latin-1 si el archivo llega con mojibake."""
    if isinstance(value, str) and any(marker in value for marker in ("Ã", "Â", "�")):
        try:
            return value.encode("latin1").decode("utf-8")
        except UnicodeError:
            return value
    return value


@dataclass(frozen=True)
class AirportInfo:
    """Datos normalizados desde airports_peru.json."""

    icao: str
    name: str = MISSING_AIRPORT_NAME
    iata: str = MISSING_VALUE
    city: str = MISSING_VALUE
    department: str = MISSING_VALUE
    elevation_ft: str = MISSING_VALUE
    runway: str = MISSING_VALUE
    airport_type: str = MISSING_VALUE
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def city_department(self) -> str:
        if self.city == MISSING_VALUE and self.department == MISSING_VALUE:
            return MISSING_VALUE
        if self.department == MISSING_VALUE:
            return self.city
        if self.city == MISSING_VALUE:
            return self.department
        return f"{self.city}, {self.department}"

    @property
    def elevation_text(self) -> str:
        if self.elevation_ft == MISSING_VALUE:
            return MISSING_VALUE
        text = str(self.elevation_ft).strip()
        return text if text.lower().endswith("ft") else f"{text} ft"

    @property
    def icao_iata_text(self) -> str:
        return f"{self.icao} / {self.iata}" if self.iata != MISSING_VALUE else f"{self.icao} / {MISSING_VALUE}"


class AirportCatalog:
    """Consulta aeropuertos por codigo OACI desde un archivo JSON local en memoria."""

    def __init__(self, airports: dict[str, AirportInfo], source_path: Path) -> None:
        self._airports = airports
        self.source_path = source_path

    def get(self, icao: Any) -> AirportInfo:
        code = "" if icao is None else str(icao).strip().upper()
        if not code:
            return AirportInfo(icao=MISSING_VALUE, name=MISSING_AIRPORT_NAME)
        return self._airports.get(code, AirportInfo(icao=code, name=MISSING_AIRPORT_NAME))

    def __len__(self) -> int:
        return len(self._airports)


def load_airports(path: Path) -> AirportCatalog:
    """Carga una sola vez el catalogo oficial airports_peru.json."""
    if not path.exists():
        return AirportCatalog({}, path)

    with open(path, "r", encoding="utf-8") as source:
        payload = json.load(source)

    raw_airports = payload.get("airports", payload)
    if not isinstance(raw_airports, dict):
        return AirportCatalog({}, path)

    airports: dict[str, AirportInfo] = {}
    for raw_code, raw_airport in raw_airports.items():
        code = str(raw_code).strip().upper()
        if not code or not isinstance(raw_airport, dict):
            continue

        airport = {str(key): _repair_text(value) for key, value in raw_airport.items()}
        airports[code] = AirportInfo(
            icao=str(airport.get("icao", code) or code).upper(),
            name=str(airport.get("name", MISSING_AIRPORT_NAME) or MISSING_AIRPORT_NAME),
            iata=str(airport.get("iata", MISSING_VALUE) or MISSING_VALUE),
            city=str(airport.get("city", MISSING_VALUE) or MISSING_VALUE),
            department=str(airport.get("department", MISSING_VALUE) or MISSING_VALUE),
            elevation_ft=str(airport.get("elevation_ft", MISSING_VALUE) or MISSING_VALUE),
            runway=str(airport.get("runway", MISSING_VALUE) or MISSING_VALUE),
            airport_type=str(airport.get("type", MISSING_VALUE) or MISSING_VALUE),
            raw=airport,
        )

    return AirportCatalog(airports, path)
