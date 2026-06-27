from __future__ import annotations

import argparse
import csv
import math
import shutil
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Iterable

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[3]
UTILS_DIR = PROJECT_ROOT / "python" / "scripts" / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from compute_graph_bounds import graph_bounds, read_graph_edgelist  # noqa: E402


DEFAULT_INSTANCES_DIR = PROJECT_ROOT / "data" / "instances"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "instance_characterization"


@dataclass(frozen=True)
class InstanceStats:
    dataset: str
    graph: str
    path: str
    vertices: int
    edges: int
    max_edges: int
    complement_edges: int
    density: float
    avg_degree: float
    min_degree: int
    max_degree: int
    median_degree: float
    degree_std: float
    isolated_vertices: int
    components: int
    largest_component_vertices: int
    largest_component_ratio: float
    smallest_component_vertices: int
    avg_component_vertices: float
    lb: int
    ub: int


@dataclass(frozen=True)
class SummaryStats:
    dataset: str
    instances: int
    total_vertices: int
    total_edges: int
    global_density: float
    min_vertices: int
    max_vertices: int
    mean_vertices: float
    median_vertices: float
    min_edges: int
    max_edges: int
    mean_edges: float
    median_edges: float
    min_density: float
    max_density: float
    mean_density: float
    median_density: float
    mean_avg_degree: float
    median_avg_degree: float
    min_components: int
    max_components: int
    mean_components: float
    total_isolated_vertices: int
    min_lb: int
    max_lb: int
    mean_lb: float
    min_ub: int
    max_ub: int
    mean_ub: float


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def fmt_number(value: object) -> str:
    if not isinstance(value, (float, int)):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if math.isnan(value):
        return ""
    return f"{value:.6f}"


def write_csv(path: Path, rows: Iterable[object]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"Nenhum dado para escrever em {path}")

    fieldnames = [field.name for field in fields(rows[0])]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: fmt_number(value)
                    for key, value in row.__dict__.items()
                }
            )


def collect_instance_files(instances_dir: Path) -> list[Path]:
    if not instances_dir.is_dir():
        raise FileNotFoundError(f"Diretorio de instancias nao encontrado: {instances_dir}")
    return sorted(path for path in instances_dir.rglob("*.col") if path.is_file())


def characterize_instance(path: Path, instances_dir: Path) -> InstanceStats:
    graph = read_graph_edgelist(path)
    dataset = path.relative_to(instances_dir).parts[0]
    degrees = [degree for _, degree in graph.degree()]
    component_sizes = sorted(
        (len(component) for component in nx.connected_components(graph)),
        reverse=True,
    )

    vertices = graph.number_of_nodes()
    edges = graph.number_of_edges()
    max_edges = vertices * (vertices - 1) // 2
    density = nx.density(graph)
    lb, ub = graph_bounds(graph)

    return InstanceStats(
        dataset=dataset,
        graph=path.stem,
        path=relpath(path),
        vertices=vertices,
        edges=edges,
        max_edges=max_edges,
        complement_edges=max_edges - edges,
        density=density,
        avg_degree=(2 * edges / vertices) if vertices else 0.0,
        min_degree=min(degrees) if degrees else 0,
        max_degree=max(degrees) if degrees else 0,
        median_degree=statistics.median(degrees) if degrees else 0.0,
        degree_std=statistics.pstdev(degrees) if len(degrees) > 1 else 0.0,
        isolated_vertices=sum(1 for degree in degrees if degree == 0),
        components=len(component_sizes),
        largest_component_vertices=component_sizes[0] if component_sizes else 0,
        largest_component_ratio=(component_sizes[0] / vertices)
        if vertices and component_sizes
        else 0.0,
        smallest_component_vertices=component_sizes[-1] if component_sizes else 0,
        avg_component_vertices=statistics.mean(component_sizes)
        if component_sizes
        else 0.0,
        lb=lb,
        ub=ub,
    )


def summarize(dataset: str, rows: list[InstanceStats]) -> SummaryStats:
    if not rows:
        raise ValueError(f"Nenhuma instancia para resumir em {dataset}")

    vertices = [row.vertices for row in rows]
    edges = [row.edges for row in rows]
    densities = [row.density for row in rows]
    avg_degrees = [row.avg_degree for row in rows]
    components = [row.components for row in rows]
    lbs = [row.lb for row in rows]
    ubs = [row.ub for row in rows]
    total_vertices = sum(vertices)
    total_edges = sum(edges)
    total_possible_edges = sum(row.max_edges for row in rows)

    return SummaryStats(
        dataset=dataset,
        instances=len(rows),
        total_vertices=total_vertices,
        total_edges=total_edges,
        global_density=(total_edges / total_possible_edges) if total_possible_edges else 0.0,
        min_vertices=min(vertices),
        max_vertices=max(vertices),
        mean_vertices=statistics.mean(vertices),
        median_vertices=statistics.median(vertices),
        min_edges=min(edges),
        max_edges=max(edges),
        mean_edges=statistics.mean(edges),
        median_edges=statistics.median(edges),
        min_density=min(densities),
        max_density=max(densities),
        mean_density=statistics.mean(densities),
        median_density=statistics.median(densities),
        mean_avg_degree=statistics.mean(avg_degrees),
        median_avg_degree=statistics.median(avg_degrees),
        min_components=min(components),
        max_components=max(components),
        mean_components=statistics.mean(components),
        total_isolated_vertices=sum(row.isolated_vertices for row in rows),
        min_lb=min(lbs),
        max_lb=max(lbs),
        mean_lb=statistics.mean(lbs),
        min_ub=min(ubs),
        max_ub=max(ubs),
        mean_ub=statistics.mean(ubs),
    )


def characterize(instances_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    instance_files = collect_instance_files(instances_dir)
    if not instance_files:
        raise FileNotFoundError(f"Nenhuma instancia .col encontrada em {instances_dir}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    detailed_rows = [
        characterize_instance(path, instances_dir)
        for path in instance_files
    ]

    rows_by_dataset: dict[str, list[InstanceStats]] = defaultdict(list)
    for row in detailed_rows:
        rows_by_dataset[row.dataset].append(row)

    summary_rows = [
        summarize(dataset, rows_by_dataset[dataset])
        for dataset in sorted(rows_by_dataset)
    ]
    summary_rows.append(summarize("ALL", detailed_rows))

    detailed_csv = output_dir / "instances_detailed.csv"
    summary_csv = output_dir / "summary_by_dataset.csv"
    write_csv(detailed_csv, detailed_rows)
    write_csv(summary_csv, summary_rows)

    return detailed_csv, summary_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera uma caracterizacao detalhada das instancias de grafos, "
            "com resumo geral e por base."
        )
    )
    parser.add_argument(
        "--instances-dir",
        type=Path,
        default=DEFAULT_INSTANCES_DIR,
        help=f"Diretorio das instancias (padrao: {relpath(DEFAULT_INSTANCES_DIR)})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Diretorio de saida (padrao: {relpath(DEFAULT_OUTPUT_DIR)})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    detailed_csv, summary_csv = characterize(
        args.instances_dir,
        args.output_dir,
    )

    print(relpath(detailed_csv))
    print(relpath(summary_csv))


if __name__ == "__main__":
    main()
