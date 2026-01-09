from __future__ import annotations

import csv
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RunResultRow:
    """Representa uma linha de resultado no CSV."""

    filename: str
    vertex: int
    edge: int
    density: float
    objective: Optional[int]  # Mantido como inteiro
    runtime_s: float
    status: str


def ensure_csv_with_header(csv_path: Path) -> None:
    """Cria o CSV com cabeçalho se não existir."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Cabeçalho customizado
            header = [
                "Grafo",
                "|V|",
                "|E|",
                "Densidade",
                "Objetivo",
                "Tempo (s)",
                "Status",
            ]
            writer.writerow(header)


def append_result(csv_path: Path, row: RunResultRow) -> None:
    """Adiciona uma linha de resultado ao CSV com formatação."""

    ensure_csv_with_header(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                row.filename,
                f"{row.vertex}",  # inteiro
                f"{row.edge}",  # inteiro
                f"{row.density:.2f}",  # duas casas decimais
                row.objective if row.objective is not None else "",  # inteiro
                f"{row.runtime_s:.2f}",  # duas casas decimais
                row.status,
            ]
        )
