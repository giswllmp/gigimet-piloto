"""Funciones de generación de gráficos para reportes METAR."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_series(df: pd.DataFrame, x: str, y: str, title: str, output_path: Optional[Path] = None) -> plt.Figure:
    """Genera un gráfico de serie temporal y opcionalmente lo exporta."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df[x], df[y], marker="o", linestyle="-", color="#4c72b0")
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    return fig
