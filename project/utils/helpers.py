"""Funciones utilitarias compartidas por el proyecto."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List


def setup_logger(name: str) -> logging.Logger:
    """Configura un logger básico con manejo de salida en consola."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def resolve_text_files(paths: List[Path]) -> List[Path]:
    """Resuelve archivos y carpetas a una lista de archivos .txt."""
    resolved: List[Path] = []
    for path in paths:
        if path.is_dir():
            resolved.extend(sorted(path.glob("*.txt")))
        elif path.suffix.lower() == ".txt":
            resolved.append(path)
    return resolved
