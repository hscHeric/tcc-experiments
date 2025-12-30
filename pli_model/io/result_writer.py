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
    objective: Optional[float]
    runtime_s: float
    status: str
    message: str


def ensure_csv_with_header(csv_path: Path) -> None:
    """Cria o CSV com cabeçalho se não existir."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = [field.name for field in fields(RunResultRow)]
            writer.writerow(header)


def append_result(csv_path: Path, row: RunResultRow) -> None:
    """Adiciona uma linha de resultado ao CSV."""
    ensure_csv_with_header(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                row.filename,
                row.vertex,
                row.edge,
                row.density,
                row.objective if row.objective is not None else "",
                row.runtime_s,
                row.status,
                row.message,
            ]
        )
