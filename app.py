"""Version web local de GigiMET con Streamlit.

Ejecutar desde la PC:
    streamlit run app.py

Abrir desde una tablet en la misma red:
    http://IP_LOCAL_DE_LA_PC:8501
"""

from __future__ import annotations

import socket
import sys
import tempfile
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "project"
for import_dir in (BASE_DIR, PROJECT_DIR):
    if import_dir.exists() and str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

def load_pdf_export():
    """Carga la exportacion PDF sin impedir que Streamlit arranque."""
    errors = []
    for module_name in ("database.export", "project.database.export"):
        try:
            module = import_module(module_name)
            return module.export_metar_pdf, ""
        except ModuleNotFoundError as exc:
            errors.append(f"{module_name}: {exc}")
        except Exception as exc:
            errors.append(f"{module_name}: {exc}")

    return (
        None,
        "La exportacion a PDF no esta disponible en esta version web. "
        "Verifica que project/database/export.py y sus dependencias esten en GitHub. "
        f"Detalle: {' | '.join(errors)}",
    )


export_metar_pdf, EXPORT_IMPORT_ERROR = load_pdf_export()

try:
    from parser.metar_parser import parse_metar_file  # noqa: E402
    from utils.airports import AirportCatalog, AirportInfo, load_airports  # noqa: E402
    from utils.variables import variable_label, variable_label_with_unit, variable_unit  # noqa: E402
except ModuleNotFoundError as exc:
    st.error(
        "No se pudieron importar los modulos principales de GigiMET. "
        "Verifica que las carpetas parser/, utils/ y resources/ esten en GitHub."
    )
    st.exception(exc)
    st.stop()


DISPLAY_COLUMNS = [
    ("report_type", "Reporte"),
    ("datetime", "Fecha y Hora"),
    ("station", "Estacion"),
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

GRAPH_VARIABLES = [
    ("temperature", variable_label_with_unit("temperature")),
    ("dewpoint", variable_label_with_unit("dewpoint")),
    ("humidity", variable_label_with_unit("humidity")),
    ("pressure", variable_label_with_unit("pressure")),
    ("wind_speed", variable_label_with_unit("wind_speed")),
    ("gust", variable_label_with_unit("gust")),
    ("visibility", variable_label_with_unit("visibility")),
    ("ceiling_ft", variable_label_with_unit("ceiling_ft")),
    ("delta_TTd", variable_label_with_unit("delta_TTd")),
]

REPORT_GRAPHS = [
    ("temperature", "Temperatura"),
    ("dewpoint", "Punto de rocio"),
    ("humidity", "Humedad relativa"),
    ("pressure", "Presion atmosferica"),
    ("wind", "Viento"),
    ("visibility", "Visibilidad"),
    ("ceiling_ft", "Ceiling"),
    ("clouds", "Nubosidad"),
    ("weather", "Fenomenos meteorologicos"),
    ("flight_category", "Categorias de vuelo"),
]

CATEGORY_COLORS = {
    "VFR": "#48bb78",
    "MVFR": "#4299e1",
    "IFR": "#ed8936",
    "LIFR": "#f56565",
    "UNKNOWN": "#a0aec0",
}

PALETTES = {
    "GigiMET": ["#4c72b0", "#48bb78", "#ed8936", "#f56565", "#805ad5", "#38b2ac"],
    "Alto contraste": ["#1d4ed8", "#dc2626", "#047857", "#7c2d12", "#6d28d9", "#0f766e"],
    "Blanco y negro": ["#111827", "#4b5563", "#9ca3af", "#000000", "#6b7280", "#374151"],
}


st.set_page_config(
    page_title="GigiMET Web",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    inject_styles()
    airports = get_airports()

    st.sidebar.title("GigiMET")
    st.sidebar.caption("Version web local para PC, tablet y red WiFi.")
    local_ip = get_local_ip()
    st.sidebar.info(f"Tablet: http://{local_ip}:8501")

    uploaded_files, year, month = render_import_controls()
    if st.sidebar.button("Procesar reportes", type="primary", use_container_width=True):
        process_uploads(uploaded_files, year, month)

    df = st.session_state.get("df")
    filtered_df = st.session_state.get("filtered_df")

    tabs = st.tabs(["Inicio", "Variables", "Graficos", "Reportes", "Config"])

    with tabs[0]:
        render_home(df, airports)
    with tabs[1]:
        filtered_df = render_variables(df, airports)
        st.session_state["filtered_df"] = filtered_df
    with tabs[2]:
        render_graphs(filtered_df if filtered_df is not None else df)
    with tabs[3]:
        render_reports(filtered_df if filtered_df is not None else df, airports)
    with tabs[4]:
        render_config(airports, local_ip)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #0f1419; color: #ffffff; }
        [data-testid="stSidebar"] { background: #1a202c; border-right: 1px solid #2d3748; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .gigimet-panel {
            background: #111827;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 14px;
        }
        .gigimet-card {
            background: #182235;
            border: 1px solid #3b4a60;
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 105px;
        }
        .gigimet-label { color: #9cc7ff; font-size: 0.78rem; font-weight: 700; }
        .gigimet-value { color: #ffffff; font-size: 1.35rem; font-weight: 800; margin-top: 4px; }
        .gigimet-subtitle { color: #cbd5e0; font-size: 0.82rem; margin-top: 4px; }
        .airport-line { color: #edf2f7; margin: 2px 0; }
        div[data-testid="stMetric"] {
            background: #171d27;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_import_controls() -> tuple[list, int, int]:
    st.sidebar.header("Importar")
    uploaded_files = st.sidebar.file_uploader(
        "Archivos TXT METAR/SPECI",
        type=["txt"],
        accept_multiple_files=True,
    )
    today = pd.Timestamp.now()
    col_year, col_month = st.sidebar.columns(2)
    with col_year:
        year = st.number_input("Ano", min_value=1950, max_value=2100, value=int(today.year), step=1)
    with col_month:
        month = st.number_input("Mes", min_value=1, max_value=12, value=int(today.month), step=1)
    return uploaded_files or [], int(year), int(month)


def process_uploads(uploaded_files: list, year: int, month: int) -> None:
    if not uploaded_files:
        st.sidebar.warning("Carga uno o varios archivos TXT.")
        return

    with st.spinner("Procesando reportes METAR/SPECI..."):
        try:
            df = parse_uploaded_files(uploaded_files, year, month)
        except Exception as exc:
            st.sidebar.error(f"No se pudo procesar: {exc}")
            return

    if df.empty:
        st.sidebar.error("No se encontraron reportes METAR/SPECI validos.")
        return

    st.session_state["df"] = df
    st.session_state["filtered_df"] = df
    st.session_state["file_count"] = len(uploaded_files)
    st.sidebar.success(f"Procesados {len(df)} reportes.")


def parse_uploaded_files(uploaded_files: list, year: int, month: int) -> pd.DataFrame:
    frames = []
    total_report_lines = 0
    total_skipped_lines = 0
    parser_duplicates = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for index, uploaded_file in enumerate(uploaded_files, 1):
            safe_name = Path(uploaded_file.name).name or f"metar_{index}.txt"
            file_path = tmp_path / f"{index}_{safe_name}"
            file_path.write_bytes(uploaded_file.getvalue())
            parsed = parse_metar_file(str(file_path), year=year, month=month)
            total_report_lines += int(parsed.attrs.get("report_lines", 0))
            total_skipped_lines += int(parsed.attrs.get("skipped_lines", 0))
            parser_duplicates += int(parsed.attrs.get("duplicates_removed", 0))
            if not parsed.empty:
                frames.append(parsed)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    before_dedup = len(combined)
    dedup_subset = [column for column in combined.columns if column != "source_line"]
    combined = combined.drop_duplicates(subset=dedup_subset).reset_index(drop=True)
    if "datetime" in combined.columns:
        combined = combined.sort_values(["datetime", "station"], na_position="last").reset_index(drop=True)

    combined.attrs["report_lines"] = total_report_lines
    combined.attrs["skipped_lines"] = total_skipped_lines
    combined.attrs["duplicates_removed"] = parser_duplicates + before_dedup - len(combined)
    return combined


def render_home(df: Optional[pd.DataFrame], airports: AirportCatalog) -> None:
    st.title("GigiMET")
    st.caption("Sistema de analisis de informacion meteorologica aeronautica.")

    if df is None or df.empty:
        st.info("Carga archivos TXT desde el panel lateral y procesa los reportes para empezar.")
        st.markdown(
            f"""
            <div class="gigimet-panel">
                <b>Catalogo aeroportuario:</b> {len(airports)} codigos OACI cargados.<br>
                La version web conserva importacion, procesamiento, filtros, tabla,
                graficos, exportacion CSV/Excel y reporte PDF.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reportes", len(df))
    col2.metric("Periodo", period_short(df))
    col3.metric("Tipos", report_type_text(df))
    col4.metric("Calidad", quality_percentage(df))

    st.subheader("Resumen ejecutivo")
    render_executive_cards(df)
    st.text_area("Detalles del procesamiento", build_processing_summary(df), height=210)
    render_airport_panel(current_airport_info(df, airports))


def render_variables(df: Optional[pd.DataFrame], airports: AirportCatalog) -> Optional[pd.DataFrame]:
    st.header("Variables")
    if df is None or df.empty:
        st.info("Primero procesa datos METAR/SPECI.")
        return df

    filtered = apply_filters_ui(df)
    shown = len(filtered)
    suffix = "" if shown == len(df) else f" de {len(df)}"
    st.caption(f"Mostrando {shown}{suffix} reportes")

    render_airport_panel(current_airport_info(filtered, airports))
    st.dataframe(presentation_dataframe(filtered), use_container_width=True, height=520)
    return filtered


def apply_filters_ui(df: pd.DataFrame) -> pd.DataFrame:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        query = st.text_input("Buscar", placeholder="Estacion, fenomeno, nubosidad o reporte...")
    with col2:
        type_options = ["Todos los tipos"] + sorted(df.get("report_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
        report_type = st.selectbox("Tipo", type_options)
    with col3:
        category_options = ["Todas las categorias"] + sorted(df.get("flight_category", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
        category = st.selectbox("Categoria", category_options)

    filtered = df.copy()
    if report_type != "Todos los tipos" and "report_type" in filtered.columns:
        filtered = filtered[filtered["report_type"] == report_type]
    if category != "Todas las categorias" and "flight_category" in filtered.columns:
        filtered = filtered[filtered["flight_category"] == category]
    if query:
        searchable_columns = [
            column
            for column in ["station", "weather", "clouds", "raw_report", "report_type", "flight_category"]
            if column in filtered.columns
        ]
        if searchable_columns:
            lowered = query.strip().lower()
            mask = filtered[searchable_columns].fillna("").astype(str).apply(
                lambda row: row.str.lower().str.contains(lowered, regex=False).any(),
                axis=1,
            )
            filtered = filtered[mask]
    return filtered.reset_index(drop=True)


def render_graphs(df: Optional[pd.DataFrame]) -> None:
    st.header("Graficos")
    if df is None or df.empty:
        st.info("Primero procesa datos METAR/SPECI.")
        return

    graph_type = st.radio(
        "Tipo de grafico",
        ["Serie individual", "Comparar variables", "Categorias de vuelo"],
        horizontal=True,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        palette_name = st.selectbox("Paleta", list(PALETTES.keys()))
    with col2:
        width = st.slider("Ancho", 6.0, 14.0, 10.0, 0.5)
    with col3:
        line_width = st.slider("Grosor", 1.0, 5.0, 2.0, 0.25)

    palette = PALETTES[palette_name]
    fig = None
    if graph_type == "Categorias de vuelo":
        fig = category_figure(df, width=width)
    elif graph_type == "Comparar variables":
        available = available_graph_variables(df)
        default = [column for column in ["temperature", "dewpoint", "pressure"] if column in available]
        selected = st.multiselect(
            "Variables",
            options=available,
            default=default,
            format_func=lambda column: variable_label_with_unit(column),
        )
        fig = combined_figure(df, selected, width=width, line_width=line_width, palette=palette)
    else:
        available = available_graph_variables(df)
        selected = st.selectbox(
            "Variable",
            options=available,
            format_func=lambda column: variable_label_with_unit(column),
        )
        fig = timeseries_figure(df, selected, width=width, line_width=line_width, color=palette[0])

    if fig is None:
        st.warning("No hay datos suficientes para generar ese grafico.")
        return

    st.pyplot(fig, use_container_width=True)
    render_graph_downloads(fig)
    plt.close(fig)


def render_graph_downloads(fig: Figure) -> None:
    col1, col2, col3 = st.columns(3)
    downloads = [
        ("PNG", "image/png", "metar_graph.png"),
        ("PDF", "application/pdf", "metar_graph.pdf"),
        ("SVG", "image/svg+xml", "metar_graph.svg"),
    ]
    for column, (fmt, mime, filename) in zip([col1, col2, col3], downloads):
        buffer = BytesIO()
        fig.savefig(buffer, format=fmt.lower(), dpi=160, bbox_inches="tight")
        column.download_button(f"Descargar {fmt}", buffer.getvalue(), filename, mime=mime, use_container_width=True)


def render_reports(df: Optional[pd.DataFrame], airports: AirportCatalog) -> None:
    st.header("Reportes")
    if df is None or df.empty:
        st.info("Primero procesa datos METAR/SPECI.")
        return

    airport = current_airport_info(df, airports)
    cols = st.columns(4)
    cols[0].metric("Registros", len(df))
    cols[1].metric("Periodo", export_period_text(df))
    cols[2].metric("Aeropuerto", airport.name if airport else "Sin datos")
    cols[3].metric("Calidad", quality_percentage(df))

    st.subheader("Exportar datos")
    export_df = presentation_dataframe(df)
    col_csv, col_excel = st.columns(2)
    col_csv.download_button(
        "Descargar CSV",
        export_df.to_csv(index=False).encode("utf-8"),
        "metar_export.csv",
        "text/csv",
        use_container_width=True,
    )
    col_excel.download_button(
        "Descargar Excel",
        dataframe_to_excel_bytes(export_df),
        "metar_export.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.subheader("Reporte PDF")
    if export_metar_pdf is None:
        st.warning(EXPORT_IMPORT_ERROR)
        return

    default_graphs = ["temperature", "pressure", "flight_category"]
    selected_graphs = st.multiselect(
        "Graficos incluidos",
        options=[key for key, _ in REPORT_GRAPHS],
        default=default_graphs,
        format_func=lambda key: dict(REPORT_GRAPHS).get(key, key),
    )
    st.text_area("Vista previa", report_preview_text(df, airport, selected_graphs), height=230)
    st.download_button(
        "Generar y descargar PDF",
        pdf_report_bytes(df, airport, selected_graphs),
        "reporte_metar_speci.pdf",
        "application/pdf",
        use_container_width=True,
    )


def render_config(airports: AirportCatalog, local_ip: str) -> None:
    st.header("Config")
    st.markdown(
        f"""
        <div class="gigimet-panel">
            <b>GigiMET Web</b><br>
            Python + Streamlit + Pandas + Matplotlib<br><br>
            Catalogo OACI: {airports.source_path.name} ({len(airports)} registros)<br>
            Ejecutar en la PC: <code>streamlit run app.py</code><br>
            Abrir en tablet Android: <code>http://{local_ip}:8501</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_airports() -> AirportCatalog:
    root_catalog = BASE_DIR / "resources" / "airports_peru.json"
    project_catalog = PROJECT_DIR / "resources" / "airports_peru.json"
    catalog_path = root_catalog if root_catalog.exists() else project_catalog
    return load_airports(catalog_path)


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "IP_LOCAL_DE_LA_PC"


def available_graph_variables(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column, _ in GRAPH_VARIABLES
        if column in df.columns and pd.to_numeric(df[column], errors="coerce").dropna().any()
    ]


def timeseries_figure(df: pd.DataFrame, column: str, *, width: float, line_width: float, color: str) -> Optional[Figure]:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce")
    if values.dropna().empty:
        return None
    plot_df = df.copy()
    plot_df[column] = values
    plot_df = plot_df.dropna(subset=[column])

    fig = Figure(figsize=(width, 4.8), dpi=130, facecolor="white")
    ax = fig.add_subplot(111)
    if "datetime" in plot_df.columns and pd.to_datetime(plot_df["datetime"], errors="coerce").notna().any():
        x_values = pd.to_datetime(plot_df["datetime"], errors="coerce")
        ax.plot(x_values, plot_df[column], color=color, linewidth=line_width, marker="o", markersize=3)
        ax.set_xlabel("Tiempo")
        fig.autofmt_xdate()
    else:
        ax.plot(range(len(plot_df)), plot_df[column], color=color, linewidth=line_width, marker="o", markersize=3)
        ax.set_xlabel("Registro")
    ax.set_title(f"{variable_label(column)} vs Tiempo", fontweight="bold")
    ax.set_ylabel(variable_unit(column) or variable_label(column))
    style_axis(ax)
    fig.tight_layout()
    return fig


def combined_figure(df: pd.DataFrame, columns: list[str], *, width: float, line_width: float, palette: list[str]) -> Optional[Figure]:
    columns = [column for column in columns if column in df.columns]
    if not columns:
        return None
    fig = Figure(figsize=(width, 5.2), dpi=130, facecolor="white")
    ax = fig.add_subplot(111)
    plotted = 0
    x_values = pd.to_datetime(df["datetime"], errors="coerce") if "datetime" in df.columns else pd.Series(range(len(df)))
    for index, column in enumerate(columns):
        values = pd.to_numeric(df[column], errors="coerce")
        if values.dropna().empty:
            continue
        ax.plot(x_values, values, label=variable_label(column), linewidth=line_width, color=palette[index % len(palette)])
        plotted += 1
    if plotted == 0:
        return None
    ax.set_title("Variables meteorologicas vs Tiempo", fontweight="bold")
    ax.set_xlabel("Tiempo" if "datetime" in df.columns else "Registro")
    ax.legend(frameon=False, fontsize=8)
    style_axis(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def category_figure(df: pd.DataFrame, *, width: float) -> Optional[Figure]:
    if "flight_category" not in df.columns:
        return None
    counts = df["flight_category"].fillna("UNKNOWN").value_counts()
    if counts.empty:
        return None
    colors = [CATEGORY_COLORS.get(str(category), "#a0aec0") for category in counts.index]
    fig = Figure(figsize=(width, 4.8), dpi=130, facecolor="white")
    ax = fig.add_subplot(111)
    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        wedgeprops={"width": 0.42, "edgecolor": "white"},
    )
    for text in texts + autotexts:
        text.set_fontsize(9)
    ax.set_title(f"Distribucion de categorias de vuelo ({int(counts.sum())} reportes)", fontweight="bold")
    fig.tight_layout()
    return fig


def style_axis(ax) -> None:
    ax.grid(True, color="#d1d5db", linewidth=0.7, alpha=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9ca3af")
    ax.spines["bottom"].set_color("#9ca3af")
    ax.tick_params(colors="#374151", labelsize=8)
    ax.xaxis.label.set_color("#374151")
    ax.yaxis.label.set_color("#374151")


def render_executive_cards(df: pd.DataFrame) -> None:
    type_counts = df["report_type"].value_counts().to_dict() if "report_type" in df.columns else {}
    category_counts = df["flight_category"].value_counts().to_dict() if "flight_category" in df.columns else {}
    values = [
        ("METAR", str(type_counts.get("METAR", 0)), "Reportes regulares"),
        ("SPECI", str(type_counts.get("SPECI", 0)), "Reportes especiales"),
        ("Periodo", period_days(df), "Duracion analizada"),
        ("Datos validos", quality_percentage(df), "Campos criticos completos"),
        ("Temperatura media", mean_text(df, "temperature", "C"), "Promedio del periodo"),
        ("Presion media", mean_text(df, "pressure", "hPa"), "QNH promedio"),
        ("Viento predominante", predominant_wind_text(df), "Direccion / velocidad"),
        ("VFR", category_count_text(category_counts, "VFR", len(df)), "Visual Flight Rules"),
        ("MVFR", category_count_text(category_counts, "MVFR", len(df)), "Marginal Visual"),
        ("IFR", category_count_text(category_counts, "IFR", len(df)), "Instrument Flight Rules"),
        ("LIFR", category_count_text(category_counts, "LIFR", len(df)), "Low IFR"),
    ]
    for row_start in range(0, len(values), 4):
        cols = st.columns(4)
        for col, (title, value, subtitle) in zip(cols, values[row_start : row_start + 4]):
            col.markdown(card_html(title, value, subtitle), unsafe_allow_html=True)


def render_airport_panel(airport: Optional[AirportInfo]) -> None:
    if airport is None:
        airport = AirportInfo(icao="No disponible")
    st.markdown(
        f"""
        <div class="gigimet-panel">
            <div class="gigimet-label">Aeropuerto detectado</div>
            <div class="airport-line"><b>Nombre:</b> {airport.name}</div>
            <div class="airport-line"><b>Codigo OACI / IATA:</b> {airport.icao_iata_text}</div>
            <div class="airport-line"><b>Ciudad:</b> {airport.city_department}</div>
            <div class="airport-line"><b>Elevacion:</b> {airport.elevation_text}</div>
            <div class="airport-line"><b>Pista:</b> {airport.runway}</div>
            <div class="airport-line"><b>Tipo:</b> {airport.airport_type}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_html(title: str, value: str, subtitle: str) -> str:
    return f"""
    <div class="gigimet-card">
        <div class="gigimet-label">{title}</div>
        <div class="gigimet-value">{value}</div>
        <div class="gigimet-subtitle">{subtitle}</div>
    </div>
    """


def build_processing_summary(df: pd.DataFrame) -> str:
    if df.empty:
        return "No se encontraron reportes METAR/SPECI."
    lines = [
        "Procesamiento completado",
        f"Reportes METAR/SPECI procesados: {len(df)}",
        f"Archivos cargados: {int(st.session_state.get('file_count', 0))}",
        f"Duplicados exactos eliminados: {int(df.attrs.get('duplicates_removed', 0))}",
    ]
    if "report_type" in df.columns:
        counts_text = ", ".join(f"{key}: {value}" for key, value in df["report_type"].value_counts().to_dict().items())
        lines.append(f"Tipo de reporte: {counts_text}")
    if "datetime" in df.columns and df["datetime"].notna().any():
        lines.append(f"Periodo detectado: {df['datetime'].min()} a {df['datetime'].max()}")

    critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
    missing = {column: int(df[column].isna().sum()) for column in critical if column in df.columns and int(df[column].isna().sum()) > 0}
    lines.append("Datos criticos: completos" if not missing else "Datos faltantes: " + ", ".join(f"{key}: {value}" for key, value in missing.items()))
    if "flight_category" in df.columns:
        category_text = ", ".join(f"{key}: {value}" for key, value in df["flight_category"].value_counts().to_dict().items())
        lines.append(f"Categorias de vuelo: {category_text}")
    stations = station_counts_text(df)
    if stations:
        lines.append(f"Estaciones detectadas: {stations}")
    return "\n".join(lines)


def presentation_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column, _ in DISPLAY_COLUMNS if column in df.columns]
    headers = {column: label for column, label in DISPLAY_COLUMNS if column in df.columns}
    output = df[columns].rename(columns=headers).copy()
    if "Fecha y Hora" in output.columns:
        output["Fecha y Hora"] = pd.to_datetime(output["Fecha y Hora"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    return output


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="METAR")
    return buffer.getvalue()


def pdf_report_bytes(df: pd.DataFrame, airport: Optional[AirportInfo], report_graphs: list[str]) -> bytes:
    if export_metar_pdf is None:
        return b""

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "reporte_metar_speci.pdf"
        export_metar_pdf(df, path, airport=airport, report_graphs=report_graphs)
        return path.read_bytes()


def report_preview_text(df: pd.DataFrame, airport: Optional[AirportInfo], report_graphs: list[str]) -> str:
    graph_names = [dict(REPORT_GRAPHS).get(key, key) for key in report_graphs]
    graph_text = "\n".join(f"- {name}" for name in graph_names) if graph_names else "- Sin graficos seleccionados"
    airport_text = airport.name if airport is not None else "Sin datos"
    return (
        "Vista previa del reporte tecnico\n"
        "================================\n\n"
        f"Registros incluidos : {len(df)}\n"
        f"Periodo             : {export_period_text(df)}\n"
        f"Estacion principal  : {representative_station(df) or 'Sin datos'}\n"
        f"Aeropuerto          : {airport_text}\n"
        f"Calidad estimada    : {quality_percentage(df)}\n\n"
        "Figuras seleccionadas\n"
        "---------------------\n"
        f"{graph_text}"
    )


def current_airport_info(df: Optional[pd.DataFrame], airports: AirportCatalog) -> Optional[AirportInfo]:
    station = representative_station(df)
    return airports.get(station) if station else None


def representative_station(df: Optional[pd.DataFrame]) -> Optional[str]:
    if df is None or df.empty or "station" not in df.columns or df["station"].dropna().empty:
        return None
    return str(df["station"].dropna().astype(str).mode().iloc[0]).upper()


def export_period_text(df: pd.DataFrame) -> str:
    if "datetime" not in df.columns or df["datetime"].dropna().empty:
        return "No detectado"
    dates = pd.to_datetime(df["datetime"], errors="coerce").dropna()
    if dates.empty:
        return "No detectado"
    return f"{dates.min():%d/%m/%Y %H:%M} - {dates.max():%d/%m/%Y %H:%M}"


def period_short(df: pd.DataFrame) -> str:
    if "datetime" not in df.columns or df["datetime"].dropna().empty:
        return "No detectado"
    return f"{df['datetime'].min():%d/%m} - {df['datetime'].max():%d/%m}"


def report_type_text(df: pd.DataFrame) -> str:
    if "report_type" not in df.columns:
        return "Sin datos"
    return " / ".join(f"{key} {value}" for key, value in df["report_type"].value_counts().to_dict().items())


def period_days(df: pd.DataFrame) -> str:
    if "datetime" not in df.columns or df["datetime"].dropna().empty:
        return "No detectado"
    start = df["datetime"].min()
    end = df["datetime"].max()
    return f"{max(1, int((end - start).total_seconds() // 86400) + 1)} dias"


def quality_percentage(df: pd.DataFrame) -> str:
    critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
    present_columns = [column for column in critical if column in df.columns]
    if not present_columns or df.empty:
        return "Sin datos"
    expected_values = len(df) * len(present_columns)
    missing_values = int(df[present_columns].isna().sum().sum())
    return f"{round((expected_values - missing_values) / expected_values * 100, 1)}%"


def mean_text(df: pd.DataFrame, column: str, unit: str) -> str:
    if column not in df.columns or df[column].dropna().empty:
        return "Sin datos"
    return f"{df[column].mean():.1f} {unit}"


def category_count_text(category_counts: dict, category: str, total: int) -> str:
    count = int(category_counts.get(category, 0))
    pct = (count / total * 100.0) if total else 0.0
    return f"{count} ({pct:.1f}%)"


def predominant_wind_text(df: pd.DataFrame) -> str:
    if "wind_dir" not in df.columns or df["wind_dir"].dropna().empty:
        return "VRB"
    rounded_dir = (df["wind_dir"].dropna() / 10).round() * 10
    predominant_dir = int(rounded_dir.mode().iloc[0]) % 360
    speed_text = ""
    if "wind_speed" in df.columns and not df["wind_speed"].dropna().empty:
        speed_text = f" / {df['wind_speed'].mean():.1f} kt"
    return f"{cardinal_direction(predominant_dir)} {predominant_dir:03d}{speed_text}"


def cardinal_direction(degrees: int) -> str:
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((degrees + 22.5) // 45) % 8
    return directions[index]


def station_counts_text(df: pd.DataFrame) -> str:
    if "station" not in df.columns or df["station"].dropna().empty:
        return ""
    counts = df["station"].dropna().astype(str).str.upper().value_counts()
    return ", ".join(f"{station}: {count}" for station, count in counts.head(6).items())


if __name__ == "__main__":
    main()
