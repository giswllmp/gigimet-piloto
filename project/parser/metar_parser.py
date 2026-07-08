"""Parser auditable para reportes METAR y SPECI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from parser.calculations import calculate_delta_t_td, calculate_humidity
from parser.classification import classify_flight_category, determine_ceiling

logger = logging.getLogger(__name__)

REPORT_PREFIXES = {"METAR", "SPECI"}
REPORT_RE = re.compile(r"^\s*(METAR|SPECI)\b", re.IGNORECASE)


@dataclass
class MetarRecord:
    report_type: str
    source_line: int
    raw_report: str
    datetime: Optional[datetime]
    station: str
    wind_dir: Optional[int]
    wind_speed: Optional[int]
    gust: Optional[int]
    visibility: Optional[float]
    temperature: Optional[float]
    dewpoint: Optional[float]
    humidity: Optional[float]
    pressure: Optional[float]
    weather: Optional[str]
    clouds: Optional[str]
    ceiling_ft: Optional[int]
    flight_category: str
    delta_TTd: Optional[float]


def is_weather_report_line(line: str) -> bool:
    """Devuelve True si la linea empieza con METAR o SPECI."""
    return bool(REPORT_RE.match(line.strip()))


def normalize_report_line(line: str) -> str:
    """Normaliza espacios y retira el terminador opcional '='."""
    return re.sub(r"\s+", " ", line.strip().rstrip("=")).strip()


def _parse_signed_temperature(value: str) -> float:
    """Convierte temperaturas METAR, incluyendo valores negativos con M."""
    if value.startswith("M"):
        return -float(value[1:])
    return float(value)


def _parse_report_datetime(value: str, year: int, month: int) -> Optional[datetime]:
    """Convierte DDHHMMZ a datetime usando el ano y mes indicados."""
    if not value.endswith("Z") or len(value) < 7:
        return None

    day = int(value[:2])
    hour = int(value[2:4])
    minute = int(value[4:6])

    return datetime(year, month, day, hour, minute)


def _parse_visibility(part: str) -> Optional[float]:
    """Extrae visibilidad y la devuelve en kilometros."""
    if part == "CAVOK":
        return 10.0

    if part.endswith("KM"):
        try:
            return float(part[:-2])
        except ValueError:
            return None

    if part.endswith("SM"):
        try:
            return round(float(part[:-2]) * 1.60934, 2)
        except ValueError:
            return None

    if part.isdigit() and len(part) == 4:
        visibility_m = int(part)
        return 10.0 if visibility_m == 9999 else round(visibility_m / 1000.0, 2)

    return None


def _parse_wind(part: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Extrae direccion, velocidad y rafaga desde grupos como 09015G25KT."""
    if not part.endswith("KT"):
        return None, None, None

    payload = part[:-2]
    direction: Optional[int] = None
    speed: Optional[int] = None
    gust: Optional[int] = None

    try:
        if payload.startswith("VRB"):
            direction = None
            wind_values = payload[3:]
        else:
            direction = int(payload[:3])
            wind_values = payload[3:]

        if "G" in wind_values:
            speed_text, gust_text = wind_values.split("G", 1)
            speed = int(speed_text)
            gust = int(gust_text)
        else:
            speed = int(wind_values)
    except ValueError:
        return None, None, None

    return direction, speed, gust


def parse_metar_line(
    line: str,
    source_line: int = 0,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Optional[MetarRecord]:
    """Parsea una linea METAR o SPECI."""
    normalized_line = normalize_report_line(line)
    parts = normalized_line.split()
    if len(parts) < 4:
        return None

    report_type = parts[0].upper()
    if report_type not in REPORT_PREFIXES:
        return None

    station = parts[1]
    datetime_obj: Optional[datetime] = None
    wind_dir: Optional[int] = None
    wind_speed: Optional[int] = None
    gust: Optional[int] = None
    visibility: Optional[float] = None
    temperature: Optional[float] = None
    dewpoint: Optional[float] = None
    pressure: Optional[float] = None
    weather: list[str] = []
    clouds_data: list[str] = []

    try:
        now = datetime.now()
        datetime_obj = _parse_report_datetime(parts[2], year or now.year, month or now.month)
    except ValueError:
        datetime_obj = None

    for raw_part in parts[3:]:
        part = raw_part.strip().rstrip("=")
        if not part:
            continue

        if part == "RMK":
            break

        if part.endswith("KT"):
            parsed_dir, parsed_speed, parsed_gust = _parse_wind(part)
            if parsed_dir is not None or parsed_speed is not None or parsed_gust is not None:
                wind_dir = parsed_dir
                wind_speed = parsed_speed
                gust = parsed_gust
            continue

        parsed_visibility = _parse_visibility(part)
        if parsed_visibility is not None:
            visibility = parsed_visibility
            if part == "CAVOK":
                clouds_data.append(part)
            continue

        if part.startswith(("Q", "A")):
            try:
                pressure_value = float(part[1:])
                pressure = round(pressure_value / 100.0 * 33.8639, 1) if part.startswith("A") else pressure_value
            except ValueError:
                pass
            continue

        if part.startswith(("SKC", "CLR", "FEW", "SCT", "BKN", "OVC", "VV")):
            clouds_data.append(part)
            continue

        if "/" in part and part.count("/") == 1:
            temp_text, dewpoint_text = part.split("/")
            try:
                temperature = _parse_signed_temperature(temp_text)
                dewpoint = _parse_signed_temperature(dewpoint_text)
            except ValueError:
                pass
            continue

        if any(token in part for token in ["+RA", "-RA", "RA", "TS", "SN", "FG", "BR", "DZ", "HZ"]):
            weather.append(part)

    humidity = calculate_humidity(temperature, dewpoint) if temperature is not None and dewpoint is not None else None
    delta = calculate_delta_t_td(temperature, dewpoint) if temperature is not None and dewpoint is not None else None
    ceiling = determine_ceiling(clouds_data)
    flight_category = classify_flight_category(visibility, ceiling)

    return MetarRecord(
        report_type=report_type,
        source_line=source_line,
        raw_report=normalized_line,
        datetime=datetime_obj,
        station=station,
        wind_dir=wind_dir,
        wind_speed=wind_speed,
        gust=gust,
        visibility=visibility,
        temperature=temperature,
        dewpoint=dewpoint,
        humidity=humidity,
        pressure=pressure,
        weather=" ".join(weather) if weather else None,
        clouds=", ".join(clouds_data) if clouds_data else None,
        ceiling_ft=ceiling,
        flight_category=flight_category,
        delta_TTd=delta,
    )


def _drop_exact_report_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina solo reportes identicos, conservando horas/fechas distintas."""
    if df.empty:
        return df

    subset = [
        column
        for column in df.columns
        if column not in {"source_line"}
    ]
    return df.drop_duplicates(subset=subset).reset_index(drop=True)


def parse_metar_file(file_path: str, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
    """Lee un archivo y parsea cada linea que empiece con METAR o SPECI."""
    records: List[Dict[str, Any]] = []
    skipped_lines = 0
    report_lines = 0

    try:
        with open(file_path, "r", encoding="utf-8") as source:
            for line_num, raw_line in enumerate(source, 1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                if not is_weather_report_line(raw_line):
                    skipped_lines += 1
                    continue

                report_lines += 1
                record = parse_metar_line(raw_line, source_line=line_num, year=year, month=month)
                if record is None:
                    skipped_lines += 1
                    continue

                records.append(record.__dict__)
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as source:
            for line_num, raw_line in enumerate(source, 1):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                if not is_weather_report_line(raw_line):
                    skipped_lines += 1
                    continue

                report_lines += 1
                record = parse_metar_line(raw_line, source_line=line_num, year=year, month=month)
                if record is None:
                    skipped_lines += 1
                    continue

                records.append(record.__dict__)
    except Exception as exc:
        logger.error("Error leyendo archivo %s: %s", file_path, exc)

    df = pd.DataFrame(records)
    before_dedup = len(df)
    df = _drop_exact_report_duplicates(df)
    df.attrs["report_lines"] = report_lines
    df.attrs["skipped_lines"] = skipped_lines
    df.attrs["duplicates_removed"] = before_dedup - len(df)

    if df.empty:
        logger.warning("No se encontraron registros METAR/SPECI validos")
    else:
        logger.info(
            "Cargados %s reportes de %s lineas METAR/SPECI; %s lineas ignoradas",
            len(df),
            report_lines,
            skipped_lines,
        )

    return df
