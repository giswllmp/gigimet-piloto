"""Ventana principal con interfaz moderna para procesar reportes METAR."""

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from database.export import export_metar_pdf, export_to_csv, export_to_excel
from graphics.canvas import MatplotlibCanvas
from parser.metar_parser import parse_metar_file
from ui.components.table import AdvancedTable
from utils.airports import AirportCatalog, AirportInfo, load_airports
from utils.variables import variable_label, variable_label_with_unit, variable_unit


class ProcessWorker(QThread):
    """Procesa archivos METAR sin bloquear la interfaz."""

    progress = Signal(int)
    finished = Signal(pd.DataFrame)
    error = Signal(str)

    def __init__(self, file_paths: list[str], year: int, month: int) -> None:
        super().__init__()
        self.file_paths = file_paths
        self.year = year
        self.month = month

    def run(self) -> None:
        try:
            all_data = []
            total_files = len(self.file_paths)
            for index, file_path in enumerate(self.file_paths, 1):
                df = parse_metar_file(file_path, year=self.year, month=self.month)
                if not df.empty:
                    all_data.append(df)
                self.progress.emit(int(index / total_files * 100))

            if not all_data:
                self.error.emit("No se procesaron archivos correctamente")
                return

            combined_df = pd.concat(all_data, ignore_index=True)
            before_dedup = len(combined_df)
            dedup_subset = [column for column in combined_df.columns if column != "source_line"]
            combined_df = combined_df.drop_duplicates(subset=dedup_subset).reset_index(drop=True)
            if "datetime" in combined_df.columns:
                combined_df = combined_df.sort_values(["datetime", "station"], na_position="last").reset_index(drop=True)
            combined_df.attrs["duplicates_removed"] = before_dedup - len(combined_df)
            self.finished.emit(combined_df)
        except Exception as exc:
            self.error.emit(f"Error: {exc}")


class MainWindow(QMainWindow):
    """Ventana principal de la aplicacion."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GigiMET")
        self.setMinimumSize(1600, 900)

        self.airports = self._load_airport_catalog()
        self.df: Optional[pd.DataFrame] = None
        self.filtered_df: Optional[pd.DataFrame] = None
        self.file_paths: list[str] = []
        self.worker: Optional[ProcessWorker] = None
        self.metric_labels: dict[str, QLabel] = {}
        self.executive_labels: dict[str, QLabel] = {}
        self.airport_summary_labels: list[QLabel] = []
        self.export_summary_labels: dict[str, QLabel] = {}
        self.report_graph_checks: dict[str, QCheckBox] = {}
        self.graph_custom_colors: dict[str, str] = {}

        self._load_styles()
        self._setup_ui()

    def _load_styles(self) -> None:
        """Carga el tema oscuro si existe."""
        style_path = Path(__file__).parent.parent / "resources" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as style_file:
                self.setStyleSheet(style_file.read())

    def _load_airport_catalog(self) -> AirportCatalog:
        """Carga el catalogo local de aeropuertos al iniciar la aplicacion."""
        path = Path(__file__).parent.parent / "resources" / "airports_peru.json"
        return load_airports(path)

    def _setup_ui(self) -> None:
        """Configura la interfaz principal."""
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_home_page())
        self.stack.addWidget(self._create_import_page())
        self.stack.addWidget(self._create_process_page())
        self.stack.addWidget(self._create_variables_page())
        self.stack.addWidget(self._create_graphs_page())
        self.stack.addWidget(self._create_export_page())
        self.stack.addWidget(self._create_settings_page())

        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(240)
        self.menu_list.setObjectName("sidebar")
        for item in ["Inicio", "Importar", "Procesar", "Variables", "Graficos", "Exportar", "Config"]:
            self.menu_list.addItem(QListWidgetItem(item))

        self.menu_list.currentRowChanged.connect(self._change_page)
        self.menu_list.setCurrentRow(0)

        main_layout.addWidget(self.menu_list)
        main_layout.addWidget(self.stack, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _create_home_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("GigiMET")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)

        desc = QLabel(
            "Sistema de analisis de informacion meteorologica aeronautica.\n\n"
            "Procesa reportes METAR/SPECI, calcula variables clave y vincula cada estacion "
            "con el catalogo local de aeropuertos del Peru.\n\n"
            f"Catalogo aeroportuario: {len(self.airports)} codigos OACI cargados"
        )
        desc.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(desc)
        self.home_airport_summary = self._create_airport_summary_label()
        layout.addWidget(self.home_airport_summary)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(14)
        metrics.setVerticalSpacing(14)
        metrics.addWidget(self._create_metric_card("Reportes", "0", "METAR/SPECI procesados"), 0, 0)
        metrics.addWidget(self._create_metric_card("Periodo", "Sin datos", "Rango temporal detectado"), 0, 1)
        metrics.addWidget(self._create_metric_card("Tipos", "Sin datos", "Distribucion METAR/SPECI"), 1, 0)
        metrics.addWidget(self._create_metric_card("Calidad", "Sin datos", "Campos criticos completos"), 1, 1)

        self.home_summary = QTextEdit()
        self.home_summary.setReadOnly(True)
        self.home_summary.setMinimumHeight(180)
        self.home_summary.setText(
            "Carga un archivo TXT y procesalo para ver el diagnostico de calidad, "
            "conteos auditables y resumen de variables meteorologicas."
        )

        layout.addLayout(metrics)
        layout.addWidget(self.home_summary)
        layout.addWidget(self._create_executive_panel())
        layout.addStretch()
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_metric_card(self, title: str, value: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(112)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("metricSubtitle")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(subtitle_label)
        card.setLayout(card_layout)
        self.metric_labels[title] = value_label
        return card

    def _create_airport_summary_label(self) -> QLabel:
        label = QLabel(self._format_airport_summary(None))
        label.setObjectName("airportSummary")
        label.setWordWrap(True)
        label.setMinimumHeight(118)
        self.airport_summary_labels.append(label)
        return label

    def _create_executive_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("executivePanel")
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(14)

        header = QLabel("Resumen ejecutivo")
        header.setObjectName("executiveTitle")
        panel_layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        cards = [
            ("total_reports", "Reportes", "0", "METAR/SPECI procesados"),
            ("metar_count", "METAR", "0", "Reportes regulares"),
            ("speci_count", "SPECI", "0", "Reportes especiales"),
            ("period_days", "Periodo", "Sin datos", "Duracion analizada"),
            ("valid_quality", "Datos validos", "Sin datos", "Campos criticos completos"),
            ("temp_mean", "Temperatura media", "Sin datos", "Promedio del periodo"),
            ("pressure_mean", "Presion media", "Sin datos", "QNH promedio"),
            ("wind_predominant", "Viento predominante", "Sin datos", "Direccion / velocidad"),
            ("vfr_count", "VFR", "0", "Visual Flight Rules"),
            ("mvfr_count", "MVFR", "0", "Marginal Visual"),
            ("ifr_count", "IFR", "0", "Instrument Flight Rules"),
            ("lifr_count", "LIFR", "0", "Low IFR"),
        ]

        for index, (key, title, value, subtitle) in enumerate(cards):
            row = index // 3
            col = index % 3
            grid.addWidget(self._create_executive_card(key, title, value, subtitle), row, col)

        panel_layout.addLayout(grid)
        panel.setLayout(panel_layout)
        return panel

    def _create_executive_card(self, key: str, title: str, value: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("executiveCard")
        card.setMinimumHeight(118)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("executiveCardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("executiveCardValue")
        value_label.setWordWrap(True)
        value_label.setMinimumHeight(30)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("executiveCardSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)
        card.setLayout(layout)
        self.executive_labels[key] = value_label
        return card

    def _create_import_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Importar Archivos")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        description = QLabel("Selecciona uno o varios archivos METAR/SPECI en formato TXT para procesarlos.")
        description.setWordWrap(True)
        description.setStyleSheet("color: #cbd5e0; font-size: 13px; line-height: 1.5;")

        # Botones de importación
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        btn_file = QPushButton("Seleccionar archivo(s)")
        btn_file.setObjectName("btnPrimary")
        btn_file.setMinimumHeight(46)
        btn_file.clicked.connect(self._select_files)

        btn_folder = QPushButton("Seleccionar carpeta")
        btn_folder.setObjectName("btnPrimary")
        btn_folder.setMinimumHeight(46)
        btn_folder.clicked.connect(self._select_folder)

        btn_clear = QPushButton("Limpiar")
        btn_clear.setObjectName("btnDanger")
        btn_clear.setMinimumHeight(46)
        btn_clear.clicked.connect(self._clear_files)

        buttons_layout.addWidget(btn_file)
        buttons_layout.addWidget(btn_folder)
        buttons_layout.addWidget(btn_clear)
        buttons_layout.addStretch()

        # Texto con archivos seleccionados
        files_label = QLabel("Archivos seleccionados:")
        files_label_font = QFont()
        files_label_font.setPointSize(13)
        files_label_font.setBold(True)
        files_label.setFont(files_label_font)

        self.import_text = QTextEdit()
        self.import_text.setReadOnly(True)
        self.import_text.setPlaceholderText("Ningún archivo seleccionado. Selecciona archivos o carpetas para empezar.")
        self.import_text.setMinimumHeight(250)
        self.import_text.setStyleSheet(
            "QTextEdit { font-size: 12px; line-height: 1.5; padding: 10px; }"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(buttons_layout)
        layout.addWidget(files_label)
        layout.addWidget(self.import_text)
        layout.addStretch()
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_process_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Procesar METAR")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        # Sección de parámetros
        params_frame = QFrame()
        params_frame.setObjectName("card")
        params_layout = QVBoxLayout()
        params_layout.setSpacing(12)
        params_layout.setContentsMargins(16, 16, 16, 16)

        params_title = QLabel("Parámetros de Procesamiento")
        params_title_font = QFont()
        params_title_font.setPointSize(13)
        params_title_font.setBold(True)
        params_title.setFont(params_title_font)
        params_layout.addWidget(params_title)

        # Layout de inputs
        inputs_layout = QGridLayout()
        inputs_layout.setHorizontalSpacing(20)
        inputs_layout.setVerticalSpacing(14)

        year_label = QLabel("Año de los reportes:")
        year_label.setMinimumWidth(150)
        self.year_input = QSpinBox()
        self.year_input.setRange(1950, 2100)
        self.year_input.setValue(pd.Timestamp.now().year)
        self.year_input.setMinimumWidth(140)
        self.year_input.setMinimumHeight(36)
        self.year_input.setStyleSheet(
            "QSpinBox { padding: 4px; font-size: 13px; }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 30px; }"
        )
        inputs_layout.addWidget(year_label, 0, 0)
        inputs_layout.addWidget(self.year_input, 0, 1)

        month_label = QLabel("Mes:")
        month_label.setMinimumWidth(150)
        self.month_input = QSpinBox()
        self.month_input.setRange(1, 12)
        self.month_input.setValue(pd.Timestamp.now().month)
        self.month_input.setMinimumWidth(140)
        self.month_input.setMinimumHeight(36)
        self.month_input.setStyleSheet(
            "QSpinBox { padding: 4px; font-size: 13px; }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 30px; }"
        )
        inputs_layout.addWidget(month_label, 0, 2)
        inputs_layout.addWidget(self.month_input, 0, 3)
        inputs_layout.setColumnStretch(4, 1)

        params_layout.addLayout(inputs_layout)

        context_note = QLabel("El año y mes se combinan con el día y hora incluidos en cada METAR/SPECI.")
        context_note.setStyleSheet("color: #cbd5e0; font-size: 12px; line-height: 1.5;")
        context_note.setWordWrap(True)
        params_layout.addWidget(context_note)

        params_frame.setLayout(params_layout)

        # Botón procesar
        btn_process = QPushButton("Procesar")
        btn_process.setObjectName("btnPrimary")
        btn_process.setFixedHeight(46)
        btn_process.setMinimumWidth(200)
        btn_process.clicked.connect(self._process_files)

        # Barra de progreso
        progress_label = QLabel("Progreso:")
        progress_label_font = QFont()
        progress_label_font.setPointSize(13)
        progress_label_font.setBold(True)
        progress_label.setFont(progress_label_font)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(24)

        # Texto de salida
        output_label = QLabel("Detalles del procesamiento:")
        output_label_font = QFont()
        output_label_font.setPointSize(13)
        output_label_font.setBold(True)
        output_label.setFont(output_label_font)

        self.process_text = QTextEdit()
        self.process_text.setReadOnly(True)
        self.process_text.setMinimumHeight(250)
        self.process_text.setStyleSheet(
            "QTextEdit { font-size: 12px; line-height: 1.5; padding: 10px; }"
        )

        layout.addWidget(title)
        layout.addWidget(params_frame)
        layout.addWidget(btn_process)
        layout.addWidget(progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(output_label)
        layout.addWidget(self.process_text)
        layout.addStretch()
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_variables_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        title = QLabel("Variables")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        # Panel de filtros
        filters_frame = QFrame()
        filters_frame.setObjectName("card")
        filters_layout_vertical = QVBoxLayout()
        filters_layout_vertical.setSpacing(10)
        filters_layout_vertical.setContentsMargins(14, 14, 14, 14)

        filters_title = QLabel("Filtros")
        filters_title_font = QFont()
        filters_title_font.setPointSize(12)
        filters_title_font.setBold(True)
        filters_title.setFont(filters_title_font)
        filters_layout_vertical.addWidget(filters_title)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar estacion, fenomeno o nubosidad...")
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._apply_filters)

        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["Todos los tipos", "METAR", "SPECI"])
        self.type_filter_combo.setMinimumHeight(36)
        self.type_filter_combo.currentIndexChanged.connect(self._apply_filters)

        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItems(["Todas las categorias", "VFR", "MVFR", "IFR", "LIFR", "UNKNOWN"])
        self.category_filter_combo.setMinimumHeight(36)
        self.category_filter_combo.currentIndexChanged.connect(self._apply_filters)

        btn_reset = QPushButton("Restablecer")
        btn_reset.setObjectName("btnWarning")
        btn_reset.setMinimumHeight(36)
        btn_reset.setMaximumWidth(140)
        btn_reset.clicked.connect(self._reset_filters)

        filters_layout.addWidget(self.search_input, 2)
        filters_layout.addWidget(self.type_filter_combo, 1)
        filters_layout.addWidget(self.category_filter_combo, 1)
        filters_layout.addWidget(btn_reset)

        filters_layout_vertical.addLayout(filters_layout)
        filters_frame.setLayout(filters_layout_vertical)

        self.variables_status = QLabel("Sin datos cargados")
        self.variables_status.setStyleSheet("color: #cbd5e0; font-size: 12px;")

        self.variables_airport_summary = self._create_airport_summary_label()

        self.table = AdvancedTable()
        layout.addWidget(title)
        layout.addWidget(filters_frame)
        layout.addWidget(self.variables_status)
        layout.addWidget(self.variables_airport_summary)
        layout.addWidget(self.table, 1)
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_graphs_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Gráficos")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        controls_layout = QGridLayout()
        controls_layout.setHorizontalSpacing(14)
        controls_layout.setVerticalSpacing(12)

        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(["Serie individual", "Comparar variables", "Categorias de vuelo"])
        self.graph_type_combo.currentIndexChanged.connect(self._update_graph_controls_state)

        self.graph_variable_combo = QComboBox()
        self.graph_variable_combo.setMinimumWidth(260)

        self.graph_palette_combo = QComboBox()
        self.graph_palette_combo.addItems(["Operacional", "Alto contraste", "Frio", "Blanco y negro", "Personalizada"])

        btn_colors = QPushButton("Elegir colores")
        btn_colors.setObjectName("graphActionButton")
        btn_colors.setFixedHeight(40)
        btn_colors.setFixedWidth(150)
        btn_colors.clicked.connect(self._choose_graph_colors)

        self.graph_line_width_input = QDoubleSpinBox()
        self.graph_line_width_input.setRange(1.0, 6.0)
        self.graph_line_width_input.setSingleStep(0.25)
        self.graph_line_width_input.setValue(2.6)
        self.graph_line_width_input.setSuffix(" px")
        self.graph_line_width_input.setFixedWidth(150)

        self.graph_width_input = QDoubleSpinBox()
        self.graph_width_input.setRange(6.0, 18.0)
        self.graph_width_input.setSingleStep(0.5)
        self.graph_width_input.setValue(12.0)
        self.graph_width_input.setSuffix(" in")
        self.graph_width_input.setFixedWidth(150)

        self.graph_height_input = QDoubleSpinBox()
        self.graph_height_input.setRange(3.0, 12.0)
        self.graph_height_input.setSingleStep(0.5)
        self.graph_height_input.setValue(6.0)
        self.graph_height_input.setSuffix(" in")
        self.graph_height_input.setFixedWidth(150)

        controls_layout.addWidget(QLabel("Vista"), 0, 0)
        controls_layout.addWidget(self.graph_type_combo, 0, 1)
        controls_layout.addWidget(QLabel("Variable"), 0, 2)
        controls_layout.addWidget(self.graph_variable_combo, 0, 3)
        controls_layout.addWidget(QLabel("Paleta"), 1, 0)
        controls_layout.addWidget(self.graph_palette_combo, 1, 1)
        controls_layout.addWidget(QLabel("Grosor"), 1, 2)
        controls_layout.addWidget(self.graph_line_width_input, 1, 3)
        controls_layout.addWidget(btn_colors, 1, 4)
        controls_layout.addWidget(QLabel("Ancho"), 2, 0)
        controls_layout.addWidget(self.graph_width_input, 2, 1)
        controls_layout.addWidget(QLabel("Alto"), 2, 2)
        controls_layout.addWidget(self.graph_height_input, 2, 3)
        controls_layout.setColumnStretch(1, 1)
        controls_layout.setColumnStretch(3, 1)

        self.graph_multi_list = QListWidget()
        self.graph_multi_list.setObjectName("graphMultiList")
        self.graph_multi_list.setMinimumHeight(118)
        self.graph_multi_list.setVisible(False)

        btn_gen = QPushButton("Generar grafico")
        btn_gen.setObjectName("graphActionButton")
        btn_gen.setFixedHeight(44)
        btn_gen.setFixedWidth(190)
        btn_gen.clicked.connect(self._generate_graph)

        save_layout = QHBoxLayout()
        save_layout.setSpacing(10)
        btn_save_png = QPushButton("PNG")
        btn_save_png.setObjectName("graphExportButton")
        btn_save_png.setFixedHeight(40)
        btn_save_png.setFixedWidth(88)
        btn_save_png.clicked.connect(lambda: self._save_graph("png"))

        btn_save_pdf = QPushButton("PDF")
        btn_save_pdf.setObjectName("graphExportButton")
        btn_save_pdf.setFixedHeight(40)
        btn_save_pdf.setFixedWidth(88)
        btn_save_pdf.clicked.connect(lambda: self._save_graph("pdf"))

        btn_save_svg = QPushButton("SVG")
        btn_save_svg.setObjectName("graphExportButton")
        btn_save_svg.setFixedHeight(40)
        btn_save_svg.setFixedWidth(88)
        btn_save_svg.clicked.connect(lambda: self._save_graph("svg"))

        btn_save_scientific = QPushButton("Paper B/N")
        btn_save_scientific.setObjectName("graphExportButton")
        btn_save_scientific.setFixedHeight(40)
        btn_save_scientific.setFixedWidth(120)
        btn_save_scientific.clicked.connect(self._save_scientific_graph)

        generate_layout = QHBoxLayout()
        generate_layout.setSpacing(12)
        generate_layout.addWidget(btn_gen)

        export_label = QLabel("Exportar grafico")
        export_label.setObjectName("labelSecondary")
        save_layout.addWidget(btn_save_png)
        save_layout.addWidget(btn_save_pdf)
        save_layout.addWidget(btn_save_svg)
        save_layout.addWidget(btn_save_scientific)
        save_layout.addStretch()

        self.canvas = MatplotlibCanvas(figsize=(12, 6))
        self.canvas.setMinimumHeight(430)
        self.canvas.setMaximumWidth(1240)
        self.graph_status = QLabel("Selecciona una vista y presiona Generar")
        self.graph_status.setStyleSheet("color: #cbd5e0; font-size: 11px;")

        graph_panel = QFrame()
        graph_panel.setObjectName("graphCanvasPanel")
        graph_panel_layout = QHBoxLayout()
        graph_panel_layout.setContentsMargins(14, 14, 14, 14)
        graph_panel_layout.addStretch()
        graph_panel_layout.addWidget(self.canvas)
        graph_panel_layout.addStretch()
        graph_panel.setLayout(graph_panel_layout)

        controls_panel = QFrame()
        controls_panel.setObjectName("graphControlsPanel")
        controls_panel_layout = QVBoxLayout()
        controls_panel_layout.setContentsMargins(16, 14, 16, 14)
        controls_panel_layout.setSpacing(12)

        primary_actions = QHBoxLayout()
        primary_actions.setSpacing(12)
        primary_actions.addLayout(generate_layout)
        primary_actions.addWidget(self.graph_status, 1)
        primary_actions.addStretch()

        export_row = QHBoxLayout()
        export_row.setSpacing(12)
        export_row.addWidget(export_label)
        export_row.addLayout(save_layout)

        controls_panel_layout.addLayout(primary_actions)
        controls_panel_layout.addLayout(controls_layout)
        controls_panel_layout.addWidget(self.graph_multi_list)
        controls_panel_layout.addLayout(export_row)
        controls_panel.setLayout(controls_panel_layout)

        layout.addWidget(title)
        layout.addWidget(graph_panel, 1)
        layout.addWidget(controls_panel)
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_export_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel("Reportes")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        page_subtitle = QLabel(
            "Prepara la vista filtrada como archivo de datos o como informe tecnico con resumen, "
            "indicadores y graficos seleccionados."
        )
        page_subtitle.setObjectName("labelSecondary")
        page_subtitle.setWordWrap(True)

        summary_panel = QFrame()
        summary_panel.setObjectName("reportPanel")
        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(20, 18, 20, 18)
        summary_layout.setSpacing(14)

        summary_title = QLabel("Resumen de exportacion")
        summary_title.setObjectName("reportPanelTitle")
        summary_note = QLabel("Estos datos corresponden a la vista actual, incluyendo filtros activos.")
        summary_note.setObjectName("labelMuted")
        summary_note.setWordWrap(True)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(summary_note)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)
        for index, (key, card_title, value, subtitle) in enumerate(
            [
                ("records", "Registros", "0", "Filas de la vista actual"),
                ("period", "Periodo", "Sin datos", "Rango temporal procesado"),
                ("airport", "Aeropuerto", "Sin datos", "Estacion representativa"),
                ("formats", "Formatos", "CSV / Excel / PDF", "Destino elegido por el usuario"),
            ]
        ):
            row = index // 2
            col = index % 2
            summary_grid.addWidget(self._create_export_summary_card(key, card_title, value, subtitle), row, col)
        summary_layout.addLayout(summary_grid)
        summary_panel.setLayout(summary_layout)

        report_graphs_panel = self._create_report_graphs_panel()

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        cards_layout.addWidget(
            self._create_export_action_card(
                "Exportar CSV",
                "Tabla filtrada en formato compatible con hojas de calculo y sistemas externos.",
                "Guardar CSV",
                lambda: self._export_data("csv"),
            ),
            0,
            0,
        )
        cards_layout.addWidget(
            self._create_export_action_card(
                "Exportar Excel",
                "Libro XLSX con las columnas presentadas en la vista de variables.",
                "Guardar Excel",
                lambda: self._export_data("excel"),
            ),
            0,
            1,
        )
        cards_layout.addWidget(
            self._create_export_action_card(
                "Generar Reporte PDF",
                "Informe tecnico con las figuras seleccionadas para el reporte.",
                "Crear PDF",
                self._export_pdf_report,
            ),
            1,
            0,
            1,
            2,
        )

        self.export_text = QTextEdit()
        self.export_text.setObjectName("reportPreview")
        self.export_text.setReadOnly(True)
        self.export_text.setMinimumHeight(160)
        self.export_text.setPlaceholderText("La vista previa y los resultados de exportacion apareceran aqui.")

        layout.addWidget(title)
        layout.addWidget(page_subtitle)
        layout.addWidget(summary_panel)
        layout.addWidget(report_graphs_panel)
        layout.addLayout(cards_layout)
        layout.addWidget(self.export_text)
        layout.addStretch()
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _create_export_summary_card(self, key: str, title: str, value: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("reportSummaryCard")
        card.setMinimumHeight(112)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 13, 16, 13)
        card_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("reportCardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("reportCardValue")
        value_label.setWordWrap(True)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("reportCardSubtitle")
        subtitle_label.setWordWrap(True)

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(subtitle_label)
        card.setLayout(card_layout)
        self.export_summary_labels[key] = value_label
        return card

    def _create_report_graphs_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("reportPanel")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title = QLabel("Graficos para el reporte")
        title.setObjectName("reportPanelTitle")
        subtitle = QLabel("Marca las figuras que deseas incluir en el PDF.")
        subtitle.setObjectName("labelMuted")
        subtitle.setWordWrap(True)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        btn_select_all = QPushButton("Seleccionar todo")
        btn_select_all.setObjectName("graphExportButton")
        btn_select_all.setFixedHeight(38)
        btn_select_all.clicked.connect(self._select_all_report_graphs)
        btn_clear = QPushButton("Limpiar seleccion")
        btn_clear.setObjectName("graphExportButton")
        btn_clear.setFixedHeight(38)
        btn_clear.clicked.connect(self._clear_report_graphs)
        btn_preview = QPushButton("Vista previa del reporte")
        btn_preview.setObjectName("graphActionButton")
        btn_preview.setFixedHeight(38)
        btn_preview.clicked.connect(self._preview_pdf_report)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(btn_select_all)
        header_layout.addWidget(btn_clear)
        header_layout.addWidget(btn_preview)

        checks_grid = QGridLayout()
        checks_grid.setHorizontalSpacing(16)
        checks_grid.setVerticalSpacing(10)
        for index, (key, label) in enumerate(self._report_graph_options()):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("reportGraphCheck")
            checkbox.setChecked(key in {"temperature", "pressure", "flight_category"})
            self.report_graph_checks[key] = checkbox
            checks_grid.addWidget(checkbox, index // 3, index % 3)

        layout.addLayout(header_layout)
        layout.addLayout(checks_grid)
        panel.setLayout(layout)
        return panel

    def _report_graph_options(self) -> list[tuple[str, str]]:
        return [
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

    def _selected_report_graphs(self) -> list[str]:
        return [key for key, _ in self._report_graph_options() if self.report_graph_checks.get(key) and self.report_graph_checks[key].isChecked()]

    def _selected_report_graph_names(self) -> list[str]:
        labels = dict(self._report_graph_options())
        return [labels[key] for key in self._selected_report_graphs()]

    def _select_all_report_graphs(self) -> None:
        for checkbox in self.report_graph_checks.values():
            checkbox.setChecked(True)
        self.export_text.setText("Seleccionados todos los graficos disponibles para el reporte PDF.")

    def _clear_report_graphs(self) -> None:
        for checkbox in self.report_graph_checks.values():
            checkbox.setChecked(False)
        self.export_text.setText("Seleccion de graficos limpiada. El PDF se generara solo con tablas y resumen si no marcas figuras.")

    def _preview_pdf_report(self) -> None:
        if self.df is None:
            self.export_text.setText("Primero procesa datos METAR.")
            return
        report_df = self._current_dataframe()
        selected = self._selected_report_graph_names()
        graph_text = "\n".join(f"- {name}" for name in selected) if selected else "- Sin graficos seleccionados"
        airport = self._current_airport_info(report_df)
        airport_text = airport.name if airport is not None else "Sin datos"
        station_text = self._representative_station(report_df) or "Sin datos"
        self.export_text.setText(
            "Vista previa del reporte tecnico\n"
            "================================\n\n"
            f"Registros incluidos : {len(report_df)}\n"
            f"Periodo             : {self._export_period_text(report_df)}\n"
            f"Estacion principal  : {station_text}\n"
            f"Aeropuerto          : {airport_text}\n"
            f"Calidad estimada    : {self._quality_percentage(report_df)}\n\n"
            "Figuras seleccionadas\n"
            "---------------------\n"
            f"{graph_text}\n\n"
            "El PDF final se guardara en la ubicacion que elijas al presionar Crear PDF."
        )

    def _create_export_action_card(self, title: str, description: str, button_text: str, callback) -> QFrame:
        card = QFrame()
        card.setObjectName("reportActionCard")
        card.setMinimumHeight(164)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("reportActionTitle")
        title_label.setWordWrap(True)

        desc_label = QLabel(description)
        desc_label.setObjectName("reportActionDescription")
        desc_label.setWordWrap(True)

        button = QPushButton(button_text)
        button.setObjectName("graphActionButton")
        button.setFixedHeight(42)
        button.clicked.connect(callback)

        card_layout.addWidget(title_label)
        card_layout.addWidget(desc_label)
        card_layout.addStretch()
        card_layout.addWidget(button)
        card.setLayout(card_layout)
        return card

    def _create_settings_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Configuración")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)

        info = QLabel(
            "GigiMET v1.0\n\n"
            "Python 3.12+ • PySide6 • Pandas\n\n"
            f"Catálogo OACI: {self.airports.source_path.name} ({len(self.airports)} registros)\n\n"
            "© 2026"
        )
        info.setWordWrap(True)
        info_font = QFont()
        info_font.setPointSize(12)
        info.setFont(info_font)
        info.setStyleSheet("line-height: 1.8;")

        layout.addWidget(title)
        layout.addWidget(info)
        layout.addStretch()
        page.setLayout(layout)
        scroll.setWidget(page)
        return scroll

    def _select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos", "", "Archivos TXT (*.txt)")
        if files:
            self.file_paths.extend(files)
            self.import_text.setText("\n".join(self.file_paths))

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            files = sorted(Path(folder).glob("*.txt"))
            self.file_paths.extend(str(file) for file in files)
            self.import_text.setText("\n".join(self.file_paths))

    def _clear_files(self) -> None:
        self.file_paths = []
        self.import_text.clear()

    def _process_files(self) -> None:
        if not self.file_paths:
            self.process_text.setText("No hay archivos cargados")
            return

        self.process_text.setText("Procesando...")
        self.progress_bar.setValue(0)
        self.worker = ProcessWorker(self.file_paths, self.year_input.value(), self.month_input.value())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, df: pd.DataFrame) -> None:
        self.df = df
        self.filtered_df = df
        self.progress_bar.setValue(100)
        self.process_text.setText(self._build_processing_summary(df))
        self._reset_filters()
        self.table.load_dataframe(df)
        self._update_variables_status(df)
        self._populate_graph_columns(df)
        self._update_dashboard(df)
        self._update_airport_summaries(df)
        self._update_export_summary(df)
        self.stack.setCurrentIndex(3)
        self.menu_list.setCurrentRow(3)

    def _on_error(self, error: str) -> None:
        self.process_text.setText(f"Error: {error}")

    def _generate_graph(self) -> None:
        if self.df is None:
            self.graph_status.setText("Primero procesa datos METAR.")
            return

        try:
            graph_type = self.graph_type_combo.currentText()
            graph_df = self._current_dataframe()
            palette = self.graph_palette_combo.currentText()
            self._apply_graph_size()

            if graph_type == "Categorias de vuelo":
                categories = graph_df["flight_category"].value_counts().to_dict()
                self.canvas.plot_categories(
                    categories,
                    f"Distribucion de categorias de vuelo ({sum(categories.values())} reportes)",
                    palette=palette,
                    custom_colors=self.graph_custom_colors,
                )
                self.graph_status.setText("Grafico generado: dona de categorias de vuelo")
                return

            if graph_type == "Comparar variables":
                series = self._selected_graph_series()
                if not series:
                    self.graph_status.setText("Selecciona una o mas variables para comparar.")
                    return
                plot_df = graph_df.dropna(subset=["datetime"])
                if plot_df.empty or all(plot_df[column].dropna().empty for column, _, _ in series if column in plot_df.columns):
                    self.graph_status.setText("No hay datos suficientes para comparar esas variables.")
                    return
                self.canvas.plot_combined_timeseries(
                plot_df,
                "datetime",
                series,
                    "Variables meteorologicas vs Tiempo",
                    line_width=self.graph_line_width_input.value(),
                    palette=palette,
                    custom_colors=self.graph_custom_colors,
                )
                self.graph_status.setText(f"Grafico combinado generado: {len(series)} variable(s)")
                return

            variable = self.graph_variable_combo.currentData()
            label = self.graph_variable_combo.currentText()
            if not variable:
                self.graph_status.setText("Selecciona una variable.")
                return

            plot_df = graph_df.dropna(subset=["datetime", variable])
            if plot_df.empty:
                self.graph_status.setText("No hay datos suficientes para esa variable.")
                return

            units = self._graph_units()
            self.canvas.plot_timeseries(
                plot_df,
                "datetime",
                variable,
                f"{variable_label(variable)} vs Tiempo",
                units.get(variable, variable),
                line_width=self.graph_line_width_input.value(),
                palette=palette,
                custom_colors=self.graph_custom_colors,
            )
            self.graph_status.setText(f"Grafico generado: {variable_label(variable)} vs Tiempo")
        except Exception as exc:
            self.graph_status.setText(f"Error generando grafico: {exc}")

    def _apply_graph_size(self) -> None:
        self.canvas.set_figure_size(self.graph_width_input.value(), self.graph_height_input.value())

    def _populate_graph_columns(self, df: pd.DataFrame) -> None:
        """Carga las variables meteorologicas disponibles para graficar."""
        self.graph_variable_combo.clear()
        self.graph_multi_list.clear()

        variable_options = self._graph_variable_options()
        available_columns = set(df.columns)
        for label, column in variable_options:
            if column in available_columns:
                self.graph_variable_combo.addItem(label, column)
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, column)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if column in {"temperature", "dewpoint", "pressure"} else Qt.CheckState.Unchecked)
                self.graph_multi_list.addItem(item)

        if self.graph_variable_combo.count() == 0:
            self.graph_status.setText("No hay variables disponibles para graficar.")
        self._update_graph_controls_state()

    def _graph_variable_options(self) -> list[tuple[str, str]]:
        return [
            (variable_label_with_unit("temperature"), "temperature"),
            (variable_label_with_unit("dewpoint"), "dewpoint"),
            (variable_label_with_unit("humidity"), "humidity"),
            (variable_label_with_unit("pressure"), "pressure"),
            (variable_label_with_unit("wind_speed"), "wind_speed"),
            (variable_label_with_unit("gust"), "gust"),
            (variable_label_with_unit("visibility"), "visibility"),
            (variable_label_with_unit("ceiling_ft"), "ceiling_ft"),
            (variable_label_with_unit("delta_TTd"), "delta_TTd"),
        ]

    def _graph_units(self) -> dict[str, str]:
        return {
            column: variable_unit(column)
            for _, column in self._graph_variable_options()
        }

    def _selected_graph_series(self) -> list[tuple[str, str, str]]:
        labels_by_column = {column: variable_label(column) for _, column in self._graph_variable_options()}
        units = self._graph_units()
        selected = []
        for row in range(self.graph_multi_list.count()):
            item = self.graph_multi_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                column = item.data(Qt.ItemDataRole.UserRole)
                selected.append((column, labels_by_column.get(column, column), units.get(column, "")))
        return selected

    def _update_graph_controls_state(self) -> None:
        if not hasattr(self, "graph_type_combo"):
            return
        graph_type = self.graph_type_combo.currentText()
        self.graph_variable_combo.setEnabled(graph_type == "Serie individual")
        self.graph_multi_list.setVisible(graph_type == "Comparar variables")

    def _choose_graph_colors(self) -> None:
        """Permite definir colores personalizados para la grafica activa."""
        graph_type = self.graph_type_combo.currentText()
        if graph_type == "Categorias de vuelo":
            targets = [("VFR", "VFR"), ("MVFR", "MVFR"), ("IFR", "IFR"), ("LIFR", "LIFR"), ("UNKNOWN", "UNKNOWN")]
        elif graph_type == "Comparar variables":
            targets = [(column, label) for column, label, _ in self._selected_graph_series()]
        else:
            column = self.graph_variable_combo.currentData()
            label = self.graph_variable_combo.currentText()
            targets = [(column, label)] if column else []

        if not targets:
            self.graph_status.setText("Selecciona una variable antes de elegir colores.")
            return

        for key, label in targets:
            initial = QColor(self.graph_custom_colors.get(key, "#3b82f6"))
            color = QColorDialog.getColor(initial=initial, parent=self, title=f"Color para {label}")
            if color.isValid():
                self.graph_custom_colors[key] = color.name()

        self.graph_palette_combo.setCurrentText("Personalizada")
        self.graph_status.setText("Colores personalizados actualizados")

    def _save_graph(self, fmt: str) -> None:
        """Guarda el grafico actual en PNG, PDF o SVG."""
        if self.df is None:
            self.graph_status.setText("Primero procesa datos METAR.")
            return

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar grafico",
            str(output_dir / f"metar_graph.{fmt}"),
            f"{fmt.upper()} (*.{fmt})",
        )
        if not path:
            return

        try:
            self.canvas.save_figure(Path(path), fmt)
            self.graph_status.setText(f"Grafico guardado en: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"No se pudo guardar el grafico:\n{exc}")

    def _save_scientific_graph(self) -> None:
        """Exporta el grafico actual con paleta blanco y negro para documentos cientificos."""
        if self.df is None:
            self.graph_status.setText("Primero procesa datos METAR.")
            return

        previous_palette = self.graph_palette_combo.currentText()
        self.graph_palette_combo.setCurrentText("Blanco y negro")
        self._generate_graph()

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar grafico cientifico",
            str(output_dir / "gigimet_scientific_graph.pdf"),
            "PDF (*.pdf);;PNG (*.png);;SVG (*.svg)",
        )
        if not path:
            self.graph_palette_combo.setCurrentText(previous_palette)
            self._generate_graph()
            return

        target_path = Path(path)
        fmt = target_path.suffix.lower().lstrip(".") or "pdf"
        if not target_path.suffix:
            target_path = target_path.with_suffix(f".{fmt}")
        try:
            self.canvas.save_figure(target_path, fmt)
            saved_message = f"Grafico cientifico B/N guardado en: {target_path}"
        except Exception as exc:
            saved_message = ""
            QMessageBox.warning(self, "Error", f"No se pudo guardar el grafico cientifico:\n{exc}")
        finally:
            self.graph_palette_combo.setCurrentText(previous_palette)
            self._generate_graph()
            if saved_message:
                self.graph_status.setText(saved_message)

    def _export_data(self, fmt: str) -> None:
        if self.df is None:
            self.export_text.setText("Primero procesa datos METAR.")
            return

        export_df = self._presentation_dataframe(self._current_dataframe())
        default_name = "metar_export.csv" if fmt == "csv" else "metar_export.xlsx"
        file_filter = "CSV (*.csv)" if fmt == "csv" else "Excel (*.xlsx)"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar exportacion", default_name, file_filter)
        if not path:
            return

        target_path = Path(path)
        expected_suffix = ".csv" if fmt == "csv" else ".xlsx"
        if target_path.suffix.lower() != expected_suffix:
            target_path = target_path.with_suffix(expected_suffix)

        try:
            if fmt == "csv":
                export_to_csv(export_df, target_path)
                self.export_text.setText(f"CSV guardado en:\n{target_path}\n\nRegistros exportados: {len(export_df)}")
            else:
                export_to_excel(export_df, target_path)
                self.export_text.setText(f"Excel guardado en:\n{target_path}\n\nRegistros exportados: {len(export_df)}")
        except Exception as exc:
            self.export_text.setText(f"Error: {exc}")

    def _export_pdf_report(self) -> None:
        if self.df is None:
            self.export_text.setText("Primero procesa datos METAR.")
            return

        report_df = self._current_dataframe()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte PDF",
            "reporte_metar_speci.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return

        target_path = Path(path)
        if target_path.suffix.lower() != ".pdf":
            target_path = target_path.with_suffix(".pdf")

        try:
            selected_graphs = self._selected_report_graphs()
            export_metar_pdf(
                report_df,
                target_path,
                airport=self._current_airport_info(report_df),
                report_graphs=selected_graphs,
            )
            graph_names = self._selected_report_graph_names()
            graph_text = ", ".join(graph_names) if graph_names else "Sin figuras seleccionadas"
            self.export_text.setText(
                "Reporte PDF generado en:\n"
                f"{target_path}\n\n"
                f"Registros incluidos: {len(report_df)}\n"
                f"Periodo: {self._export_period_text(report_df)}\n"
                f"Graficos incluidos: {graph_text}"
            )
        except Exception as exc:
            self.export_text.setText(f"Error generando PDF: {exc}")

    def _change_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _build_processing_summary(self, df: pd.DataFrame) -> str:
        """Construye un resumen auditable del procesamiento."""
        if df.empty:
            return "No se encontraron reportes METAR/SPECI."

        lines = [
            "Procesamiento completado",
            f"Reportes METAR/SPECI procesados: {len(df)}",
            f"Archivos cargados: {len(self.file_paths)}",
        ]

        duplicates_removed = int(df.attrs.get("duplicates_removed", 0))
        lines.append(f"Duplicados exactos eliminados: {duplicates_removed}")

        if "report_type" in df.columns:
            counts = df["report_type"].value_counts().to_dict()
            counts_text = ", ".join(f"{key}: {value}" for key, value in counts.items())
            lines.append(f"Tipo de reporte: {counts_text}")

        if "datetime" in df.columns and df["datetime"].notna().any():
            start = df["datetime"].min()
            end = df["datetime"].max()
            lines.append(f"Periodo detectado: {start} a {end}")

        critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
        missing = {
            column: int(df[column].isna().sum())
            for column in critical
            if column in df.columns and int(df[column].isna().sum()) > 0
        }
        if missing:
            missing_text = ", ".join(f"{column}: {count}" for column, count in missing.items())
            lines.append(f"Datos faltantes: {missing_text}")
        else:
            lines.append("Datos criticos: completos")

        if "flight_category" in df.columns:
            category_counts = df["flight_category"].value_counts().to_dict()
            category_text = ", ".join(f"{key}: {value}" for key, value in category_counts.items())
            lines.append(f"Categorias de vuelo: {category_text}")

        stations = self._station_counts_text(df)
        if stations:
            lines.append(f"Estaciones detectadas: {stations}")

        return "\n".join(lines)

    def _update_dashboard(self, df: pd.DataFrame) -> None:
        """Actualiza las tarjetas del tablero principal."""
        if df.empty:
            return

        self.metric_labels["Reportes"].setText(str(len(df)))

        if "datetime" in df.columns and df["datetime"].notna().any():
            start = df["datetime"].min().strftime("%d/%m %H:%M")
            end = df["datetime"].max().strftime("%d/%m %H:%M")
            self.metric_labels["Periodo"].setText(f"{start} - {end}")
        else:
            self.metric_labels["Periodo"].setText("No detectado")

        if "report_type" in df.columns:
            counts = df["report_type"].value_counts().to_dict()
            self.metric_labels["Tipos"].setText(" / ".join(f"{key} {value}" for key, value in counts.items()))

        critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
        present_columns = [column for column in critical if column in df.columns]
        if present_columns:
            expected_values = len(df) * len(present_columns)
            missing_values = int(df[present_columns].isna().sum().sum())
            quality = round((expected_values - missing_values) / expected_values * 100, 1)
            self.metric_labels["Calidad"].setText(f"{quality}%")

        self.home_summary.setText(self._build_processing_summary(df))
        self._update_executive_panel(df)
        self._update_airport_summaries(df)

    def _apply_filters(self) -> None:
        """Filtra la tabla por texto, tipo de reporte y categoria de vuelo."""
        if self.df is None:
            return

        filtered = self.df.copy()

        report_type = self.type_filter_combo.currentText()
        if report_type != "Todos los tipos" and "report_type" in filtered.columns:
            filtered = filtered[filtered["report_type"] == report_type]

        category = self.category_filter_combo.currentText()
        if category != "Todas las categorias" and "flight_category" in filtered.columns:
            filtered = filtered[filtered["flight_category"] == category]

        query = self.search_input.text().strip().lower()
        if query:
            searchable_columns = [
                column
                for column in ["station", "weather", "clouds", "raw_report", "report_type", "flight_category"]
                if column in filtered.columns
            ]
            if searchable_columns:
                mask = filtered[searchable_columns].fillna("").astype(str).apply(
                    lambda row: row.str.lower().str.contains(query, regex=False).any(),
                    axis=1,
                )
                filtered = filtered[mask]

        self.filtered_df = filtered.reset_index(drop=True)
        self.table.load_dataframe(self.filtered_df)
        self._update_variables_status(self.filtered_df)
        self._update_airport_summaries(self.filtered_df)
        self._update_export_summary(self.filtered_df)

    def _reset_filters(self) -> None:
        """Limpia todos los filtros de la vista de variables."""
        if hasattr(self, "search_input"):
            self.search_input.blockSignals(True)
            self.search_input.clear()
            self.search_input.blockSignals(False)

        if hasattr(self, "type_filter_combo"):
            self.type_filter_combo.blockSignals(True)
            self.type_filter_combo.setCurrentIndex(0)
            self.type_filter_combo.blockSignals(False)

        if hasattr(self, "category_filter_combo"):
            self.category_filter_combo.blockSignals(True)
            self.category_filter_combo.setCurrentIndex(0)
            self.category_filter_combo.blockSignals(False)

        if self.df is not None:
            self.filtered_df = self.df
            self.table.load_dataframe(self.df)
            self._update_variables_status(self.df)
            self._update_airport_summaries(self.df)
            self._update_export_summary(self.df)

    def _update_variables_status(self, df: pd.DataFrame) -> None:
        """Actualiza el contador de la vista de variables."""
        total = len(self.df) if self.df is not None else 0
        shown = len(df)
        suffix = "" if shown == total else f" de {total}"
        self.variables_status.setText(f"Mostrando {shown}{suffix} reportes")

    def _current_dataframe(self) -> pd.DataFrame:
        """Devuelve la vista filtrada cuando existe; si no, el DataFrame completo."""
        if self.filtered_df is not None:
            return self.filtered_df
        if self.df is not None:
            return self.df
        return pd.DataFrame()

    def _presentation_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Devuelve los datos con columnas meteorologicas y nombres legibles."""
        columns = [column for column, _ in AdvancedTable.DISPLAY_COLUMNS if column in df.columns]
        headers = {column: label for column, label in AdvancedTable.DISPLAY_COLUMNS if column in df.columns}
        return df[columns].rename(columns=headers)

    def _update_export_summary(self, df: Optional[pd.DataFrame]) -> None:
        if not hasattr(self, "export_summary_labels") or not self.export_summary_labels:
            return

        if df is None or df.empty:
            self.export_summary_labels["records"].setText("0")
            self.export_summary_labels["period"].setText("Sin datos")
            self.export_summary_labels["airport"].setText("Sin datos")
            return

        airport = self._current_airport_info(df)
        station = self._representative_station(df) or "Sin estacion"
        airport_name = airport.name if airport is not None else station
        if len(airport_name) > 36:
            airport_name = f"{airport_name[:33]}..."

        self.export_summary_labels["records"].setText(str(len(df)))
        self.export_summary_labels["period"].setText(self._export_period_text(df))
        self.export_summary_labels["airport"].setText(f"{station} - {airport_name}")

    def _export_period_text(self, df: pd.DataFrame) -> str:
        if "datetime" not in df.columns or df["datetime"].dropna().empty:
            return "No detectado"
        dates = pd.to_datetime(df["datetime"], errors="coerce").dropna()
        if dates.empty:
            return "No detectado"
        return f"{dates.min():%d/%m/%Y %H:%M} - {dates.max():%d/%m/%Y %H:%M}"

    def _current_airport_info(self, df: Optional[pd.DataFrame]) -> Optional[AirportInfo]:
        station = self._representative_station(df)
        return self.airports.get(station) if station else None

    def _update_airport_summaries(self, df: Optional[pd.DataFrame]) -> None:
        station = self._representative_station(df)
        summary = self._format_airport_summary(self.airports.get(station) if station else None)
        for label in self.airport_summary_labels:
            label.setText(summary)

    def _representative_station(self, df: Optional[pd.DataFrame]) -> Optional[str]:
        if df is None or df.empty or "station" not in df.columns or df["station"].dropna().empty:
            return None
        return str(df["station"].dropna().astype(str).mode().iloc[0]).upper()

    def _format_airport_summary(self, airport: Optional[AirportInfo]) -> str:
        if airport is None:
            return (
                "📍 Nombre: Nombre no disponible\n"
                "🛫 Codigo OACI / IATA: No disponible\n"
                "🌎 Ciudad: No disponible\n"
                "📏 Elevacion: No disponible\n"
                "🛬 Pista: No disponible\n"
                "🏷 Tipo: No disponible"
            )

        return (
            f"📍 Nombre: {airport.name}\n"
            f"🛫 Codigo OACI / IATA: {airport.icao_iata_text}\n"
            f"🌎 Ciudad: {airport.city_department}\n"
            f"📏 Elevacion: {airport.elevation_text}\n"
            f"🛬 Pista: {airport.runway}\n"
            f"🏷 Tipo: {airport.airport_type}"
        )

    def _station_counts_text(self, df: pd.DataFrame) -> str:
        if "station" not in df.columns or df["station"].dropna().empty:
            return ""
        counts = df["station"].dropna().astype(str).str.upper().value_counts()
        return ", ".join(f"{station}: {count}" for station, count in counts.head(6).items())

    def _update_executive_panel(self, df: pd.DataFrame) -> None:
        """Actualiza el resumen ejecutivo con indicadores meteorologicos."""
        if df.empty:
            return

        self.executive_labels["total_reports"].setText(str(len(df)))

        type_counts = df["report_type"].value_counts().to_dict() if "report_type" in df.columns else {}
        self.executive_labels["metar_count"].setText(str(type_counts.get("METAR", 0)))
        self.executive_labels["speci_count"].setText(str(type_counts.get("SPECI", 0)))

        if "datetime" in df.columns and df["datetime"].notna().any():
            start = df["datetime"].min()
            end = df["datetime"].max()
            days = max(1, int((end - start).total_seconds() // 86400) + 1)
            self.executive_labels["period_days"].setText(f"{days} dias")
        else:
            self.executive_labels["period_days"].setText("No detectado")

        self.executive_labels["valid_quality"].setText(self._quality_percentage(df))

        category_counts = df["flight_category"].value_counts().to_dict() if "flight_category" in df.columns else {}
        for category, key in [
            ("VFR", "vfr_count"),
            ("MVFR", "mvfr_count"),
            ("IFR", "ifr_count"),
            ("LIFR", "lifr_count"),
        ]:
            count = int(category_counts.get(category, 0))
            pct = (count / len(df) * 100.0) if len(df) else 0.0
            self.executive_labels[key].setText(f"{count} ({pct:.1f}%)")

        self.executive_labels["temp_mean"].setText(self._mean_text(df, "temperature", "C"))
        self.executive_labels["pressure_mean"].setText(self._mean_text(df, "pressure", "hPa"))
        self.executive_labels["wind_predominant"].setText(self._predominant_wind_text(df))

    def _quality_percentage(self, df: pd.DataFrame) -> str:
        critical = ["temperature", "dewpoint", "pressure", "visibility", "wind_speed"]
        present_columns = [column for column in critical if column in df.columns]
        if not present_columns or df.empty:
            return "Sin datos"
        expected_values = len(df) * len(present_columns)
        missing_values = int(df[present_columns].isna().sum().sum())
        return f"{round((expected_values - missing_values) / expected_values * 100, 1)}%"

    def _mean_text(self, df: pd.DataFrame, column: str, unit: str) -> str:
        if column not in df.columns or df[column].dropna().empty:
            return "Sin datos"
        return f"{df[column].mean():.1f} {unit}"

    def _predominant_wind_text(self, df: pd.DataFrame) -> str:
        if "wind_dir" not in df.columns or df["wind_dir"].dropna().empty:
            return "VRB"

        rounded_dir = (df["wind_dir"].dropna() / 10).round() * 10
        predominant_dir = int(rounded_dir.mode().iloc[0]) % 360
        speed_text = ""
        if "wind_speed" in df.columns and not df["wind_speed"].dropna().empty:
            speed_text = f" / {df['wind_speed'].mean():.1f} kt"
        return f"{self._cardinal_direction(predominant_dir)} {predominant_dir:03d}{speed_text}"

    def _cardinal_direction(self, degrees: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((degrees + 22.5) // 45) % 8
        return directions[index]
