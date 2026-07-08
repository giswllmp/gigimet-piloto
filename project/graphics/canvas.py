"""Graficos integrados en la interfaz usando matplotlib."""

from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.dates import AutoDateFormatter, AutoDateLocator
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MatplotlibCanvas(QWidget):
    """Canvas para integrar graficos matplotlib en PySide6."""

    FIGURE_BG = "#0f1722"
    AXIS_BG = "#111d2b"
    GRID = "#2a3b4f"
    TEXT = "#e5edf7"
    MUTED = "#9fb0c3"
    BLUE = "#3b82f6"
    RED = "#ef4444"
    GREEN = "#45b974"
    ORANGE = "#f59e0b"
    TEAL = "#2dd4bf"
    GRAY = "#718096"

    def __init__(self, parent=None, figsize=(10, 6), dpi=100) -> None:
        super().__init__(parent)
        self.figure = Figure(figsize=figsize, dpi=dpi, facecolor=self.FIGURE_BG, edgecolor="none")
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        self._apply_dark_theme()

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def _style_axis(self, ax) -> None:
        ax.set_facecolor(self.AXIS_BG)
        ax.tick_params(colors=self.MUTED, labelsize=9)
        ax.xaxis.label.set_color(self.MUTED)
        ax.yaxis.label.set_color(self.MUTED)
        ax.title.set_color(self.TEXT)
        ax.grid(True, alpha=0.45, color=self.GRID, linestyle="-", linewidth=0.8)
        for side in ["top", "right"]:
            ax.spines[side].set_visible(False)
        for side in ["left", "bottom"]:
            ax.spines[side].set_color(self.GRID)

    def _style_paper_axis(self, ax) -> None:
        self.figure.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.tick_params(colors="#111111", labelsize=9)
        ax.xaxis.label.set_color("#111111")
        ax.yaxis.label.set_color("#111111")
        ax.title.set_color("#111111")
        ax.grid(True, alpha=0.45, color="#b8b8b8", linestyle="-", linewidth=0.7)
        for spine in ax.spines.values():
            spine.set_color("#111111")

    def _apply_dark_theme(self) -> None:
        """Aplica tema oscuro al grafico activo."""
        self.figure.set_facecolor(self.FIGURE_BG)
        self._style_axis(self.ax)

    def clear(self) -> None:
        """Limpia el grafico."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self._apply_dark_theme()

    def set_figure_size(self, width: float, height: float) -> None:
        """Ajusta el tamano fisico de la figura en pulgadas."""
        self.figure.set_size_inches(width, height, forward=True)

    def plot_auto(self, df: pd.DataFrame, x_col: str, y_col: str) -> None:
        """Crea un grafico automaticamente detectando el tipo."""
        self.clear()

        x_data = df[x_col]
        y_data = df[y_col]
        x_is_numeric = pd.api.types.is_numeric_dtype(x_data)
        y_is_numeric = pd.api.types.is_numeric_dtype(y_data)

        if x_is_numeric and y_is_numeric:
            self.ax.scatter(x_data, y_data, alpha=0.75, s=48, color=self.BLUE, edgecolors=self.AXIS_BG)
        elif not x_is_numeric:
            value_counts = x_data.value_counts()
            self.ax.bar(
                range(len(value_counts)),
                value_counts.values,
                color=self.BLUE,
                edgecolor=self.AXIS_BG,
                alpha=0.9,
            )
            self.ax.set_xticks(range(len(value_counts)))
            self.ax.set_xticklabels(value_counts.index, rotation=45, ha="right")
        else:
            self.ax.plot(x_data, y_data, linewidth=2.4, color=self.BLUE, marker="o", markersize=4)

        self.ax.set_title(
            f"{y_col} vs {x_col}",
            fontsize=14,
            fontweight="bold",
            fontfamily="Times New Roman",
            loc="center",
            color=self.TEXT,
        )
        self.ax.set_xlabel(x_col, fontsize=10, color=self.MUTED)
        self.ax.set_ylabel(y_col, fontsize=10, color=self.MUTED)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def plot_timeseries(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str,
        ylabel: str,
        line_width: float = 2.6,
        palette: str = "Operacional",
        custom_colors: dict[str, str] | None = None,
    ) -> None:
        """Grafica una serie temporal con estilo de panel profesional."""
        self.clear()
        if palette == "Blanco y negro":
            self._style_paper_axis(self.ax)
        plot_df = df.sort_values(x_col)
        color = self._series_color(y_col, palette, custom_colors=custom_colors)
        text_color = "#111111" if palette == "Blanco y negro" else self.TEXT
        muted_color = "#111111" if palette == "Blanco y negro" else self.MUTED
        marker_edge = "#ffffff" if palette == "Blanco y negro" else self.FIGURE_BG
        self.ax.plot(
            plot_df[x_col],
            plot_df[y_col],
            linewidth=line_width,
            color=color,
            linestyle=self._series_linestyle(0, palette),
            marker="o",
            markersize=4,
            markerfacecolor=color,
            markeredgecolor=marker_edge,
            markeredgewidth=0.8,
        )
        self.ax.fill_between(plot_df[x_col], plot_df[y_col], plot_df[y_col].min(), color=color, alpha=0.08)
        self.ax.set_title(
            title,
            fontsize=14,
            fontweight="bold",
            fontfamily="Times New Roman",
            loc="center",
            color=text_color,
        )
        self.ax.set_xlabel("Fecha y hora", fontsize=10, color=muted_color)
        self.ax.set_ylabel(ylabel, fontsize=10, color=muted_color)
        self._format_dates(self.ax)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def plot_combined_timeseries(
        self,
        df: pd.DataFrame,
        x_col: str,
        series: list[tuple[str, str, str]],
        title: str,
        line_width: float = 2.6,
        palette: str = "Operacional",
        custom_colors: dict[str, str] | None = None,
    ) -> None:
        """Grafica varias variables en una sola figura."""
        self.clear()
        if palette == "Blanco y negro":
            self._style_paper_axis(self.ax)
        plot_df = df.dropna(subset=[x_col]).sort_values(x_col)
        plotted = 0
        text_color = "#111111" if palette == "Blanco y negro" else self.TEXT
        muted_color = "#111111" if palette == "Blanco y negro" else self.MUTED
        marker_edge = "#ffffff" if palette == "Blanco y negro" else self.FIGURE_BG
        for index, (column, label, unit) in enumerate(series):
            if column not in plot_df.columns:
                continue
            series_df = plot_df.dropna(subset=[column])
            if series_df.empty:
                continue
            color = self._series_color(column, palette, index, custom_colors)
            legend_label = f"{label} ({unit})" if unit else label
            self.ax.plot(
                series_df[x_col],
                series_df[column],
                linewidth=line_width,
                color=color,
                linestyle=self._series_linestyle(index, palette),
                marker="o",
                markersize=3.8,
                markerfacecolor=color,
                markeredgecolor=marker_edge,
                markeredgewidth=0.8,
                label=legend_label,
            )
            plotted += 1

        plotted_units = {unit for _, _, unit in series if unit}
        if plotted == 0:
            self.ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", color=muted_color, transform=self.ax.transAxes)
        else:
            self.ax.legend(loc="upper left", frameon=False, labelcolor=text_color, fontsize=9, ncols=min(3, plotted))

        self.ax.set_title(
            title,
            fontsize=14,
            fontweight="bold",
            fontfamily="Times New Roman",
            loc="center",
            color=text_color,
        )
        self.ax.set_xlabel("Fecha y hora", fontsize=10, color=muted_color)
        ylabel = f"Valor ({next(iter(plotted_units))})" if len(plotted_units) == 1 else "Valor (unidades indicadas en leyenda)"
        self.ax.set_ylabel(ylabel, fontsize=10, color=muted_color)
        self._format_dates(self.ax)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def plot_distribution(self, data: list, title: str, xlabel: str) -> None:
        """Grafica una distribucion."""
        self.clear()
        self.ax.hist(data, bins=20, color=self.BLUE, edgecolor=self.AXIS_BG, alpha=0.9)
        self.ax.set_title(
            title,
            fontsize=14,
            fontweight="bold",
            fontfamily="Times New Roman",
            loc="center",
            color=self.TEXT,
        )
        self.ax.set_xlabel(xlabel, fontsize=10, color=self.MUTED)
        self.ax.set_ylabel("Frecuencia", fontsize=10, color=self.MUTED)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def plot_categories(
        self,
        categories: dict,
        title: str,
        palette: str = "Operacional",
        custom_colors: dict[str, str] | None = None,
    ) -> None:
        """Grafica categorias de vuelo como dona."""
        self.clear()
        self._plot_donut(self.ax, categories, title, palette, custom_colors)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def plot_professional_dashboard(
        self,
        df: pd.DataFrame,
        line_width: float = 2.4,
        palette: str = "Operacional",
        custom_colors: dict[str, str] | None = None,
    ) -> None:
        """Dibuja un panel con temperatura, presion y categorias de vuelo."""
        self.figure.clear()
        temp_ax, pressure_ax, category_ax = self.figure.subplots(
            1,
            3,
            gridspec_kw={"width_ratios": [1.35, 1.25, 1.15]},
        )

        for ax in [temp_ax, pressure_ax, category_ax]:
            self._style_axis(ax)

        dated_df = df.dropna(subset=["datetime"]).sort_values("datetime")

        temp_df = dated_df.dropna(subset=["temperature"])
        if not temp_df.empty:
            temp_ax.plot(
                temp_df["datetime"],
                temp_df["temperature"],
                color=self._series_color("temperature", palette, custom_colors=custom_colors),
                marker="o",
                markersize=3.8,
                linewidth=line_width,
                label="Temperatura (°C)",
            )

        dew_df = dated_df.dropna(subset=["dewpoint"])
        if not dew_df.empty:
            temp_ax.plot(
                dew_df["datetime"],
                dew_df["dewpoint"],
                color=self._series_color("dewpoint", palette, custom_colors=custom_colors),
                marker="o",
                markersize=3.8,
                linewidth=line_width,
                label="Punto de rocio (°C)",
            )

        temp_ax.set_title("Temperatura del aire (°C)", fontsize=13, fontweight="bold", fontfamily="Times New Roman", loc="center")
        temp_ax.set_ylabel("°C")
        temp_ax.legend(loc="upper left", frameon=False, labelcolor=self.TEXT, fontsize=8, ncols=2)
        self._format_dates(temp_ax)

        pressure_df = dated_df.dropna(subset=["pressure"])
        if not pressure_df.empty:
            pressure_ax.plot(
                pressure_df["datetime"],
                pressure_df["pressure"],
                color=self._series_color("pressure", palette, custom_colors=custom_colors),
                marker="o",
                markersize=3.8,
                linewidth=line_width,
                label="QNH (hPa)",
            )
            pressure_ax.legend(loc="upper left", frameon=False, labelcolor=self.TEXT, fontsize=8)

        pressure_ax.set_title("Presion atmosferica (hPa)", fontsize=13, fontweight="bold", fontfamily="Times New Roman", loc="center")
        pressure_ax.set_ylabel("hPa")
        self._format_dates(pressure_ax)

        categories = df["flight_category"].value_counts().to_dict() if "flight_category" in df.columns else {}
        self._plot_donut(category_ax, categories, "Categorias de vuelo", palette, custom_colors)

        self.figure.subplots_adjust(left=0.045, right=0.98, top=0.88, bottom=0.18, wspace=0.28)
        self.canvas.draw()

    def _plot_donut(
        self,
        ax,
        categories: dict,
        title: str,
        palette: str = "Operacional",
        custom_colors: dict[str, str] | None = None,
    ) -> None:
        ax.clear()
        paper = palette == "Blanco y negro"
        if paper:
            self.figure.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff" if paper else self.AXIS_BG)
        text_color = "#111111" if paper else self.TEXT
        muted_color = "#111111" if paper else self.MUTED
        ax.set_title(
            title,
            fontsize=14,
            fontweight="bold",
            fontfamily="Times New Roman",
            loc="center",
            color=text_color,
        )
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

        ordered = ["VFR", "MVFR", "IFR", "LIFR", "UNKNOWN"]
        values = {
            category: int(categories.get(category, 0))
            for category in ordered
            if int(categories.get(category, 0)) > 0
        }
        if not values:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", color=muted_color, transform=ax.transAxes)
            return

        colors_map = self._category_colors(palette, custom_colors)
        labels = list(values.keys())
        counts = list(values.values())
        colors = [colors_map.get(label, self.GRAY) for label in labels]
        wedges, _, autotexts = ax.pie(
            counts,
            colors=colors,
            startangle=90,
            counterclock=False,
            autopct=lambda pct: f"{pct:.1f}%" if pct >= 5 else "",
            pctdistance=0.74,
            wedgeprops={"width": 0.42, "edgecolor": "#ffffff" if paper else self.AXIS_BG, "linewidth": 1.2},
        )
        for text in autotexts:
            text.set_color("#ffffff" if paper else self.TEXT)
            text.set_fontsize(9)
            text.set_fontweight("bold")

        legend_labels = [f"{label} ({count})" for label, count in zip(labels, counts)]
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            labelcolor=text_color,
            fontsize=9,
            handlelength=1,
            handletextpad=0.6,
        )
        ax.set_aspect("equal")

    def _format_dates(self, ax) -> None:
        locator = AutoDateLocator(minticks=4, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(AutoDateFormatter(locator))
        for label in ax.get_xticklabels():
            label.set_rotation(0)
            label.set_ha("center")

    def _series_color(
        self,
        y_col: str,
        palette: str = "Operacional",
        index: int = 0,
        custom_colors: dict[str, str] | None = None,
    ) -> str:
        if palette == "Personalizada" and custom_colors and y_col in custom_colors:
            return custom_colors[y_col]

        palettes = {
            "Operacional": {
                "temperature": self.RED,
                "dewpoint": self.GREEN,
                "humidity": self.TEAL,
                "pressure": self.BLUE,
                "wind_speed": self.ORANGE,
                "gust": self.RED,
                "visibility": self.TEAL,
                "ceiling_ft": self.BLUE,
                "delta_TTd": self.ORANGE,
            },
            "Alto contraste": {
                "temperature": "#ff5c5c",
                "dewpoint": "#60d394",
                "humidity": "#00d4ff",
                "pressure": "#7aa2ff",
                "wind_speed": "#ffd166",
                "gust": "#f72585",
                "visibility": "#4cc9f0",
                "ceiling_ft": "#b8f2e6",
                "delta_TTd": "#ff9f1c",
            },
            "Frio": {
                "temperature": "#38bdf8",
                "dewpoint": "#2dd4bf",
                "humidity": "#818cf8",
                "pressure": "#60a5fa",
                "wind_speed": "#a78bfa",
                "gust": "#f472b6",
                "visibility": "#67e8f9",
                "ceiling_ft": "#93c5fd",
                "delta_TTd": "#c4b5fd",
            },
            "Blanco y negro": {
                "temperature": "#111111",
                "dewpoint": "#444444",
                "humidity": "#666666",
                "pressure": "#000000",
                "wind_speed": "#333333",
                "gust": "#555555",
                "visibility": "#777777",
                "ceiling_ft": "#222222",
                "delta_TTd": "#888888",
            },
        }
        fallback = [self.BLUE, self.TEAL, self.ORANGE, self.RED, self.GREEN, "#a78bfa", "#f472b6"]
        colors = palettes.get(palette, palettes["Operacional"])
        return colors.get(y_col, fallback[index % len(fallback)])

    def _series_linestyle(self, index: int, palette: str) -> str:
        if palette != "Blanco y negro":
            return "-"
        styles = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
        return styles[index % len(styles)]

    def _category_colors(self, palette: str, custom_colors: dict[str, str] | None = None) -> dict[str, str]:
        if palette == "Personalizada" and custom_colors:
            return {
                "VFR": custom_colors.get("VFR", self.BLUE),
                "MVFR": custom_colors.get("MVFR", self.TEAL),
                "IFR": custom_colors.get("IFR", self.ORANGE),
                "LIFR": custom_colors.get("LIFR", self.RED),
                "UNKNOWN": custom_colors.get("UNKNOWN", self.GRAY),
            }

        if palette == "Alto contraste":
            return {
                "VFR": "#7aa2ff",
                "MVFR": "#00d4ff",
                "IFR": "#ffd166",
                "LIFR": "#ff5c5c",
                "UNKNOWN": self.GRAY,
            }
        if palette == "Frio":
            return {
                "VFR": "#60a5fa",
                "MVFR": "#2dd4bf",
                "IFR": "#a78bfa",
                "LIFR": "#f472b6",
                "UNKNOWN": self.GRAY,
            }
        if palette == "Blanco y negro":
            return {
                "VFR": "#111111",
                "MVFR": "#555555",
                "IFR": "#888888",
                "LIFR": "#bbbbbb",
                "UNKNOWN": "#dddddd",
            }
        return {
            "VFR": self.BLUE,
            "MVFR": self.TEAL,
            "IFR": self.ORANGE,
            "LIFR": self.RED,
            "UNKNOWN": self.GRAY,
        }

    def save_figure(self, path: Path, fmt: str = "png") -> None:
        """Guarda la figura en diferentes formatos."""
        try:
            self.figure.savefig(
                path,
                dpi=180,
                facecolor=self.figure.get_facecolor(),
                edgecolor="none",
                bbox_inches="tight",
                format=fmt,
            )
        except Exception as exc:
            raise ValueError(f"Error guardando grafico: {exc}") from exc
