"""Exportacion de datos, graficos y reportes para el proyecto METAR."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.variables import variable_label, variable_unit


def export_to_csv(df: pd.DataFrame, path: Path) -> None:
    """Exporta el DataFrame a CSV."""
    df.to_csv(path, index=False, encoding="utf-8")


def export_to_excel(df: pd.DataFrame, path: Path) -> None:
    """Exporta el DataFrame a Excel."""
    df.to_excel(path, index=False)


def export_figure(fig, path: Path) -> None:
    """Exporta una figura matplotlib a PNG o PDF."""
    fig.savefig(path, dpi=150, bbox_inches="tight")


def export_metar_pdf(
    df: pd.DataFrame,
    path: Path,
    *,
    project_title: str = "GigiMET - Reporte tecnico METAR/SPECI",
    airport: Optional[Any] = None,
    figure: Optional[Any] = None,
    report_graphs: Optional[list[str]] = None,
) -> None:
    """Genera un reporte tecnico PDF a partir de los datos procesados."""
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=project_title,
    )
    styles = _report_styles()
    story: list[Any] = []

    station = _station_text(df)
    period = _period_text(df)
    airport_name = getattr(airport, "name", "No disponible") if airport else "No disponible"
    icao = getattr(airport, "icao", station) if airport else station

    story.append(_report_header(project_title, station, period, len(df), styles))
    story.append(Spacer(1, 0.35 * cm))

    story.append(_section("Identificacion del analisis", styles))
    story.append(
        _key_value_table(
            [
                ("Aeropuerto analizado", airport_name),
                ("Codigo OACI", icao),
                ("Estacion principal", station),
                ("Periodo de analisis", period),
                ("Total de reportes procesados", str(len(df))),
            ]
        )
    )

    type_counts = df["report_type"].value_counts().to_dict() if "report_type" in df.columns else {}
    story.append(Spacer(1, 0.25 * cm))
    story.append(_section("Conteo de reportes", styles))
    story.append(_key_value_table([("METAR", str(type_counts.get("METAR", 0))), ("SPECI", str(type_counts.get("SPECI", 0)))]))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_section("Resumen de variables principales", styles))
    story.append(_variable_summary_table(df))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_section("Distribucion de categorias de vuelo", styles))
    story.append(_category_table(df))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_section("Datos criticos detectados", styles))
    story.append(Paragraph(_critical_data_text(df), styles["Body"]))

    story.append(Spacer(1, 0.25 * cm))
    story.append(_section("Fenomenos meteorologicos observados", styles))
    story.append(Paragraph(_weather_text(df), styles["Body"]))

    figure_images = _selected_report_graph_images(df, report_graphs or [])
    if not figure_images and figure is not None and report_graphs:
        fallback_image = _figure_image(figure)
        figure_images = [("Grafico actual", fallback_image)] if fallback_image is not None else []
    if figure_images:
        story.append(PageBreak())
        story.append(_section("Figuras del analisis", styles))
        for title, image in figure_images:
            story.append(Paragraph(title, styles["Section"]))
            story.append(image)
            story.append(Spacer(1, 0.35 * cm))

    story.append(Spacer(1, 0.35 * cm))
    story.append(_section("Conclusiones generales", styles))
    story.append(Paragraph(_conclusions_text(df), styles["Body"]))

    doc.build(story)


def _report_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "GigimetTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.white,
            spaceAfter=6,
        ),
        "Subtitle": ParagraphStyle(
            "GigimetSubtitle",
            parent=base["Normal"],
            fontSize=10.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#dbeafe"),
        ),
        "Section": ParagraphStyle(
            "GigimetSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e40af"),
            spaceBefore=6,
            spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "GigimetBody",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#111827"),
        ),
        "HeaderMetric": ParagraphStyle(
            "GigimetHeaderMetric",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "HeaderMetricLabel": ParagraphStyle(
            "GigimetHeaderMetricLabel",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#bfdbfe"),
        ),
    }


def _section(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles["Section"])


def _report_header(project_title: str, station: str, period: str, records: int, styles: dict[str, ParagraphStyle]) -> Table:
    title = Paragraph(project_title, styles["Title"])
    subtitle = Paragraph("Resumen del procesamiento de reportes meteorologicos aeronauticos", styles["Subtitle"])
    metrics = Table(
        [
            [
                Paragraph(str(records), styles["HeaderMetric"]),
                Paragraph(station, styles["HeaderMetric"]),
                Paragraph(period, styles["HeaderMetric"]),
            ],
            [
                Paragraph("Reportes", styles["HeaderMetricLabel"]),
                Paragraph("Estacion principal", styles["HeaderMetricLabel"]),
                Paragraph("Periodo analizado", styles["HeaderMetricLabel"]),
            ],
        ],
        colWidths=[4.5 * cm, 4.5 * cm, 7.0 * cm],
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1f2f46")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#4c72b0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#4c72b0")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    header = Table([[title], [subtitle], [Spacer(1, 0.2 * cm)], [metrics]], colWidths=[16.0 * cm])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#334155")),
                ("TOPPADDING", (0, 0), (-1, 0), 18),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
            ]
        )
    )
    return header


def _key_value_table(rows: list[tuple[str, str]]) -> Table:
    table = Table([["Indicador", "Valor"], *rows], colWidths=[6.2 * cm, 10.0 * cm], hAlign="LEFT")
    table.setStyle(_table_style())
    return table


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2f46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#1e40af")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _station_text(df: pd.DataFrame) -> str:
    if "station" not in df.columns or df["station"].dropna().empty:
        return "No disponible"
    return str(df["station"].dropna().astype(str).mode().iloc[0]).upper()


def _period_text(df: pd.DataFrame) -> str:
    if "datetime" not in df.columns or df["datetime"].dropna().empty:
        return "No detectado"
    dates = pd.to_datetime(df["datetime"], errors="coerce").dropna()
    if dates.empty:
        return "No detectado"
    return f"{dates.min():%d/%m/%Y %H:%M} - {dates.max():%d/%m/%Y %H:%M}"


def _variable_summary_table(df: pd.DataFrame) -> Table:
    rows = [["Variable", "Minimo", "Media", "Maximo", "Unidad"]]
    columns = ["temperature", "dewpoint", "humidity", "pressure", "wind_speed", "gust", "visibility", "ceiling_ft", "delta_TTd"]
    for column in columns:
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            rows.append([variable_label(column), "Sin datos", "Sin datos", "Sin datos", variable_unit(column)])
        else:
            rows.append([variable_label(column), f"{values.min():.1f}", f"{values.mean():.1f}", f"{values.max():.1f}", variable_unit(column)])
    if len(rows) == 1:
        rows.append(["Sin variables numericas", "-", "-", "-", "-"])
    table = Table(rows, colWidths=[5.0 * cm, 2.7 * cm, 2.7 * cm, 2.7 * cm, 2.2 * cm], hAlign="LEFT")
    table.setStyle(_table_style())
    return table


def _category_table(df: pd.DataFrame) -> Table:
    rows = [["Categoria", "Reportes", "Porcentaje"]]
    if "flight_category" in df.columns and len(df):
        counts = df["flight_category"].fillna("UNKNOWN").value_counts()
        for category in ["VFR", "MVFR", "IFR", "LIFR", "UNKNOWN"]:
            count = int(counts.get(category, 0))
            rows.append([category, str(count), f"{count / len(df) * 100:.1f}%"])
    else:
        rows.append(["Sin datos", "0", "0.0%"])
    table = Table(rows, colWidths=[5.0 * cm, 5.0 * cm, 5.0 * cm], hAlign="LEFT")
    table.setStyle(_table_style())
    return table


def _critical_data_text(df: pd.DataFrame) -> str:
    critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed", "ceiling_ft"]
    details = []
    for column in critical:
        if column in df.columns:
            missing = int(df[column].isna().sum())
            if missing:
                details.append(f"{variable_label(column)}: {missing} registros sin dato")
    if "flight_category" in df.columns:
        severe = int(df["flight_category"].isin(["IFR", "LIFR"]).sum())
        details.append(f"Categorias IFR/LIFR detectadas: {severe} reportes")
    return "; ".join(details) if details else "No se detectaron faltantes en los campos criticos disponibles."


def _weather_text(df: pd.DataFrame) -> str:
    if "weather" not in df.columns or df["weather"].dropna().empty:
        return "No se registraron fenomenos meteorologicos codificados en la muestra procesada."
    tokens = df["weather"].dropna().astype(str).str.split().explode()
    counts = tokens[tokens.str.strip().ne("")].value_counts().head(8)
    if counts.empty:
        return "No se registraron fenomenos meteorologicos codificados en la muestra procesada."
    return "; ".join(f"{token}: {count}" for token, count in counts.items())


def _conclusions_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "No hay registros disponibles para emitir conclusiones del procesamiento."

    quality = _quality_percentage(df)
    category = "No determinada"
    if "flight_category" in df.columns and df["flight_category"].dropna().any():
        category = str(df["flight_category"].dropna().astype(str).mode().iloc[0])
    return (
        f"El procesamiento consolido {len(df)} reportes METAR/SPECI para el periodo analizado. "
        f"La categoria de vuelo predominante fue {category} y la completitud estimada de variables criticas fue {quality}. "
        "Los resultados permiten revisar tendencias operacionales, condiciones restrictivas y eventos meteorologicos "
        "relevantes para el aeropuerto seleccionado."
    )


def _quality_percentage(df: pd.DataFrame) -> str:
    critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
    present_columns = [column for column in critical if column in df.columns]
    if not present_columns or df.empty:
        return "sin datos"
    expected_values = len(df) * len(present_columns)
    missing_values = int(df[present_columns].isna().sum().sum())
    return f"{round((expected_values - missing_values) / expected_values * 100, 1)}%"


def _figure_image(figure: Optional[Any]) -> Optional[Image]:
    if figure is None or not getattr(figure, "axes", None):
        return None
    has_content = any(ax.has_data() or ax.texts or ax.patches or ax.collections for ax in figure.axes)
    if not has_content:
        return None

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    buffer.seek(0)
    image = Image(buffer, width=16.0 * cm, height=8.5 * cm)
    image.hAlign = "CENTER"
    return image


def _selected_report_graph_images(df: pd.DataFrame, graph_keys: list[str]) -> list[tuple[str, Image]]:
    images = []
    for key in graph_keys:
        figure = _build_report_graph(df, key)
        if figure is None:
            continue
        image = _figure_image(figure)
        if image is not None:
            images.append((_graph_title(key), image))
    return images


def _build_report_graph(df: pd.DataFrame, key: str) -> Optional[Figure]:
    if df.empty:
        return None
    if key in {"temperature", "dewpoint", "humidity", "pressure", "visibility", "ceiling_ft"}:
        return _line_graph(df, key, _graph_title(key))
    if key == "wind":
        return _wind_graph(df)
    if key == "clouds":
        return _bar_graph(df, "clouds", "Nubosidad observada", "Grupos de nubosidad")
    if key == "weather":
        return _weather_graph(df)
    if key == "flight_category":
        return _bar_graph(df, "flight_category", "Categorias de vuelo", "Categoria")
    return None


def _line_graph(df: pd.DataFrame, column: str, title: str) -> Optional[Figure]:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce")
    if values.dropna().empty:
        return None

    fig = Figure(figsize=(7.8, 3.8), dpi=140, facecolor="white")
    ax = fig.add_subplot(111)
    if "datetime" in df.columns and pd.to_datetime(df["datetime"], errors="coerce").notna().any():
        x_values = pd.to_datetime(df["datetime"], errors="coerce")
        ax.plot(x_values, values, color="#1d4ed8", linewidth=1.8)
        ax.set_xlabel("Tiempo")
        fig.autofmt_xdate()
    else:
        ax.plot(range(len(values)), values, color="#1d4ed8", linewidth=1.8)
        ax.set_xlabel("Registro")
    ax.set_title(title, fontsize=11, fontweight="bold")
    unit = variable_unit(column)
    ax.set_ylabel(unit if unit else variable_label(column))
    _style_report_axis(ax)
    fig.tight_layout()
    return fig


def _wind_graph(df: pd.DataFrame) -> Optional[Figure]:
    columns = [column for column in ["wind_speed", "gust"] if column in df.columns and pd.to_numeric(df[column], errors="coerce").dropna().any()]
    if not columns:
        return None

    fig = Figure(figsize=(7.8, 3.8), dpi=140, facecolor="white")
    ax = fig.add_subplot(111)
    x_values = pd.to_datetime(df["datetime"], errors="coerce") if "datetime" in df.columns else pd.Series(range(len(df)))
    for column, color in [("wind_speed", "#1d4ed8"), ("gust", "#dc2626")]:
        if column in columns:
            ax.plot(x_values, pd.to_numeric(df[column], errors="coerce"), label=variable_label(column), linewidth=1.8, color=color)
    ax.set_title("Viento observado", fontsize=11, fontweight="bold")
    ax.set_xlabel("Tiempo" if "datetime" in df.columns else "Registro")
    ax.set_ylabel("kt")
    ax.legend(frameon=False, fontsize=8)
    _style_report_axis(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _bar_graph(df: pd.DataFrame, column: str, title: str, xlabel: str) -> Optional[Figure]:
    if column not in df.columns or df[column].dropna().empty:
        return None
    counts = df[column].dropna().astype(str).value_counts().head(10)
    if counts.empty:
        return None

    fig = Figure(figsize=(7.8, 3.8), dpi=140, facecolor="white")
    ax = fig.add_subplot(111)
    ax.bar(range(len(counts)), counts.values, color="#2563eb", alpha=0.88)
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=35, ha="right", fontsize=8)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Reportes")
    _style_report_axis(ax)
    fig.tight_layout()
    return fig


def _weather_graph(df: pd.DataFrame) -> Optional[Figure]:
    if "weather" not in df.columns or df["weather"].dropna().empty:
        return None
    tokens = df["weather"].dropna().astype(str).str.split().explode()
    counts = tokens[tokens.str.strip().ne("")].value_counts().head(10)
    if counts.empty:
        return None

    fig = Figure(figsize=(7.8, 3.8), dpi=140, facecolor="white")
    ax = fig.add_subplot(111)
    ax.bar(range(len(counts)), counts.values, color="#0f766e", alpha=0.88)
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=35, ha="right", fontsize=8)
    ax.set_title("Fenomenos meteorologicos observados", fontsize=11, fontweight="bold")
    ax.set_xlabel("Fenomeno")
    ax.set_ylabel("Reportes")
    _style_report_axis(ax)
    fig.tight_layout()
    return fig


def _style_report_axis(ax: Any) -> None:
    ax.grid(True, color="#d1d5db", linewidth=0.7, alpha=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9ca3af")
    ax.spines["bottom"].set_color("#9ca3af")
    ax.tick_params(colors="#374151", labelsize=8)
    ax.xaxis.label.set_color("#374151")
    ax.yaxis.label.set_color("#374151")


def _graph_title(key: str) -> str:
    titles = {
        "temperature": "Temperatura",
        "dewpoint": "Punto de rocio",
        "humidity": "Humedad relativa",
        "pressure": "Presion atmosferica",
        "wind": "Viento",
        "visibility": "Visibilidad",
        "ceiling_ft": "Ceiling",
        "clouds": "Nubosidad",
        "weather": "Fenomenos meteorologicos",
        "flight_category": "Categorias de vuelo",
    }
    return titles.get(key, key)
