"""Configuración básica y constantes del proyecto."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
STYLE_PATH = RESOURCES_DIR / "style.qss"
