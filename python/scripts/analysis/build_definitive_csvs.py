#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp") / "matplotlib"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy import stats  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
UTILS_DIR = PROJECT_ROOT / "python" / "scripts" / "utils"
sys.path.insert(0, str(UTILS_DIR))

from add_graph_bounds import graph_bounds, read_graph_edgelist  # noqa: E402


DEFAULT_DATASETS = [
    (
        "CUBIC",
        "results/pli/CUBIC/cubic_results.csv",
        "data/instances/CUBIC",
        "cubic_results_definitivo.csv",
    ),
    (
        "DIMACS",
        "results/pli/DIMACS/dimacs_resultados.csv",
        "data/instances/DIMACS",
        "dimacs_resultados_definitivo.csv",
    ),
    (
        "HB",
        "results/pli/HB/harwell_boieng_results.csv",
        "data/instances/HB",
        "harwell_boieng_results_definitivo.csv",
    ),
]

DEFAULT_ALGORITHMS = [
    ("HHO_RVNS", "results/experiments/hho_rvns"),
    ("ACO_TS", "results/experiments/aco_ts"),
]

ALGORITHM_LABELS = {
    "ACO_TS": r"$\mathrm{ACO}_{\mathbb{R}}$-TS",
    "HHO_RVNS": "HHO-RVNS",
}

ALGORITHM_COLORS = {
    "ACO_TS": "#1F4E79",
    "HHO_RVNS": "#A23E48",
}

EPS = 1e-9


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    csv_path: Path
    instances_dir: Path
    output_name: str


@dataclass(frozen=True)
class AlgorithmConfig:
    column_prefix: str
    results_dir: Path


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def graph_stem(value: Any) -> str:
    name = Path(str(value)).name
    return name[:-4] if name.lower().endswith(".col") else name


def parse_dataset(value: str) -> DatasetConfig:
    parts = value.split(":")
    if len(parts) not in {3, 4}:
        raise argparse.ArgumentTypeError("Use DATASET:CSV:INSTANCES_DIR[:OUTPUT_NAME].")

    name, csv_path, instances_dir = parts[:3]
    output_name = (
        parts[3] if len(parts) == 4 else f"{Path(csv_path).stem}_definitivo.csv"
    )
    return DatasetConfig(
        name=name,
        csv_path=project_path(csv_path),
        instances_dir=project_path(instances_dir),
        output_name=output_name,
    )


def parse_algorithm(value: str) -> AlgorithmConfig:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Use COLUNA:DIRETORIO_JSONS.")

    prefix, directory = parts
    return AlgorithmConfig(column_prefix=prefix, results_dir=project_path(directory))


def default_datasets() -> list[DatasetConfig]:
    return [
        DatasetConfig(
            name=name,
            csv_path=project_path(csv_path),
            instances_dir=project_path(instances_dir),
            output_name=output_name,
        )
        for name, csv_path, instances_dir, output_name in DEFAULT_DATASETS
    ]


def default_algorithms() -> list[AlgorithmConfig]:
    return [
        AlgorithmConfig(column_prefix=prefix, results_dir=project_path(directory))
        for prefix, directory in DEFAULT_ALGORITHMS
    ]


def index_instances(instances_dir: Path) -> dict[str, Path]:
    if not instances_dir.is_dir():
        raise FileNotFoundError(
            f"Diretorio de instancias nao encontrado: {instances_dir}"
        )
    return {
        path.stem: path for path in sorted(instances_dir.rglob("*")) if path.is_file()
    }


def compute_bounds(df: pd.DataFrame, instances_dir: Path) -> pd.DataFrame:
    instance_by_stem = index_instances(instances_dir)
    lbs: list[int] = []
    ubs: list[int] = []

    for graph_name in df["Grafo"]:
        stem = graph_stem(graph_name)
        instance_path = instance_by_stem.get(stem)
        if instance_path is None:
            raise FileNotFoundError(
                f"Instancia '{stem}' nao encontrada em {instances_dir}"
            )

        graph = read_graph_edgelist(instance_path)
        lb, ub = graph_bounds(graph)
        lbs.append(lb)
        ubs.append(ub)

    result = df.copy()
    result["Grafo"] = result["Grafo"].map(graph_stem)
    result["LB"] = lbs
    result["UB"] = ubs
    return result


def attempt_value(attempt: dict[str, Any]) -> float | None:
    value = attempt.get("final_solution_value")
    if value is None:
        convergence = attempt.get("convergence")
        if isinstance(convergence, list) and convergence:
            last = convergence[-1]
            if isinstance(last, dict):
                value = last.get("best_fitness")

    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def has_convergence(attempt: dict[str, Any]) -> bool:
    convergence = attempt.get("convergence")
    return isinstance(convergence, list) and bool(convergence)


def load_algorithm_results(
    config: AlgorithmConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    convergence_rows: list[dict[str, Any]] = []
    if not config.results_dir.is_dir():
        return pd.DataFrame(), pd.DataFrame()

    for json_path in sorted(config.results_dir.glob("*.json")):
        try:
            with json_path.open(encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(data, dict):
            continue

        attempts = data.get("attempts")
        if not isinstance(attempts, list):
            attempts = []

        values = [
            value
            for attempt in attempts
            if isinstance(attempt, dict)
            for value in [attempt_value(attempt)]
            if value is not None
        ]
        if not values:
            global_best = data.get("best_fitness_global")
            if global_best is not None:
                values = [float(global_best)]

        if not values:
            continue

        total_runtime = sum(
            float(attempt.get("total_runtime_seconds", 0.0))
            for attempt in attempts
            if isinstance(attempt, dict)
        )
        parameters = data.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}
        local_search_start = parameters.get("local_search_start")
        best_value = min(values)
        best_candidates: list[dict[str, Any]] = []
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            value = attempt_value(attempt)
            if value is not None and math.isclose(
                value, best_value, rel_tol=0.0, abs_tol=EPS
            ):
                best_candidates.append(attempt)

        best_attempt = next(
            (attempt for attempt in best_candidates if has_convergence(attempt)),
            best_candidates[0] if best_candidates else None,
        )
        best_round = best_attempt.get("attempt") if best_attempt is not None else None

        graph_key = graph_stem(data.get("graph", json_path.stem))
        series = pd.Series(values, dtype="float64")
        prefix = config.column_prefix
        rows.append(
            {
                "graph_key": graph_key,
                prefix: best_value,
                f"{prefix}_media": float(series.mean()),
                f"{prefix}_mediana": float(series.median()),
                f"{prefix}_rodadas": len(values),
                f"{prefix}_melhor_rodada": best_round,
                f"{prefix}_melhor_avaliacoes": (
                    best_attempt.get("evaluations")
                    if best_attempt is not None
                    else pd.NA
                ),
                f"{prefix}_melhor_iteracoes": (
                    best_attempt.get("iterations")
                    if best_attempt is not None
                    else pd.NA
                ),
                f"{prefix}_melhor_tempo_s": (
                    best_attempt.get("total_runtime_seconds")
                    if best_attempt is not None
                    else pd.NA
                ),
                f"{prefix}_melhor_criterio_parada": (
                    best_attempt.get("stop_reason")
                    if best_attempt is not None
                    else pd.NA
                ),
                f"{prefix}_melhor_seed": (
                    best_attempt.get("seed") if best_attempt is not None else pd.NA
                ),
                f"{prefix}_tempo_total_s": total_runtime,
                f"{prefix}_json": str(json_path.relative_to(PROJECT_ROOT)),
                f"{prefix}_valores_rodadas": ";".join(f"{value:g}" for value in values),
            }
        )

        if isinstance(best_attempt, dict):
            convergence = best_attempt.get("convergence")
            if isinstance(convergence, list):
                for point in convergence:
                    if not isinstance(point, dict):
                        continue
                    convergence_rows.append(
                        {
                            "algoritmo": prefix,
                            "Grafo": graph_key,
                            "melhor_rodada": best_round,
                            "melhor_valor": best_value,
                            "iteration": point.get("iteration"),
                            "elapsed_ms": point.get("elapsed_ms"),
                            "elapsed_seconds": point.get("elapsed_seconds"),
                            "evaluations": point.get("evaluations"),
                            "best_fitness": point.get("best_fitness"),
                            "local_search_start": local_search_start,
                            "json": str(json_path.relative_to(PROJECT_ROOT)),
                        }
                    )

    return pd.DataFrame(rows), pd.DataFrame(convergence_rows)


def add_gap_columns(
    df: pd.DataFrame,
    value_column: str,
    reference_column: str,
    prefix: str,
) -> None:
    gap_column = f"{prefix}_gap_prova"
    relative_gap_column = f"{prefix}_gap_relativo"

    df[gap_column] = df[value_column] - df[reference_column]
    df[relative_gap_column] = (df[gap_column] / df[reference_column]) * 100.0
    df.loc[
        df[value_column].isna()
        | df[reference_column].isna()
        | (df[reference_column] == 0),
        relative_gap_column,
    ] = pd.NA


def add_bounds_check(df: pd.DataFrame, value_column: str, output_column: str) -> None:
    value = df[value_column]
    df[output_column] = value.isna() | (
        (value + EPS >= df["LB"]) & (value <= df["UB"] + EPS)
    )


def collect_bound_violations(
    df: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        graph = row["Grafo"]
        lb = row["LB"]
        ub = row["UB"]
        pli_value = row["Objetivo"]
        if pd.notna(pli_value) and not (
            pli_value + EPS >= lb and pli_value <= ub + EPS
        ):
            rows.append(
                {
                    "Grafo": graph,
                    "algoritmo": "PLI",
                    "rodada": pd.NA,
                    "valor": pli_value,
                    "LB": lb,
                    "UB": ub,
                    "violacao": "abaixo_LB" if pli_value < lb else "acima_UB",
                }
            )

        for algorithm in algorithms:
            values_column = f"{algorithm.column_prefix}_valores_rodadas"
            if values_column not in df.columns or pd.isna(row.get(values_column)):
                continue

            values = [
                float(value)
                for value in str(row[values_column]).split(";")
                if value.strip()
            ]
            for index, value in enumerate(values, start=1):
                if value + EPS >= lb and value <= ub + EPS:
                    continue
                rows.append(
                    {
                        "Grafo": graph,
                        "algoritmo": algorithm.column_prefix,
                        "rodada": index,
                        "valor": value,
                        "LB": lb,
                        "UB": ub,
                        "violacao": "abaixo_LB" if value < lb else "acima_UB",
                    }
                )

    return pd.DataFrame(rows)


def enrich_dataset(
    dataset: DatasetConfig,
    algorithm_tables: dict[str, pd.DataFrame],
    algorithms: list[AlgorithmConfig],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not dataset.csv_path.is_file():
        raise FileNotFoundError(f"CSV do PLI nao encontrado: {dataset.csv_path}")

    df = pd.read_csv(dataset.csv_path)
    required_columns = {"Grafo", "Objetivo"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"{dataset.csv_path} nao tem colunas obrigatorias: {sorted(missing)}"
        )

    df = compute_bounds(df, dataset.instances_dir)
    df["dataset"] = dataset.name
    df["graph_key"] = df["Grafo"].map(graph_stem)
    df["Objetivo"] = pd.to_numeric(df["Objetivo"], errors="coerce")
    add_gap_columns(df, "Objetivo", "Objetivo", "PLI")
    add_bounds_check(df, "Objetivo", "PLI_dentro_bounds")

    for algorithm in algorithms:
        table = algorithm_tables.get(algorithm.column_prefix, pd.DataFrame())
        if not table.empty:
            df = df.merge(table, on="graph_key", how="left")
        else:
            df[algorithm.column_prefix] = pd.NA

        prefix = algorithm.column_prefix
        add_gap_columns(df, prefix, "Objetivo", prefix)
        add_bounds_check(df, prefix, f"{prefix}_dentro_bounds")

        values_column = f"{prefix}_valores_rodadas"
        if values_column in df.columns:
            df[f"{prefix}_todas_rodadas_dentro_bounds"] = df.apply(
                lambda row: all_values_inside_bounds(row, values_column),
                axis=1,
            )
        else:
            df[f"{prefix}_todas_rodadas_dentro_bounds"] = pd.NA

    violations = collect_bound_violations(df, algorithms)
    df = df.drop(columns=["graph_key"])
    return order_columns(df, algorithms), violations


def all_values_inside_bounds(row: pd.Series, values_column: str) -> bool | pd.NA:
    if pd.isna(row.get(values_column)):
        return pd.NA
    values = [
        float(value) for value in str(row[values_column]).split(";") if value.strip()
    ]
    return all(row["LB"] - EPS <= value <= row["UB"] + EPS for value in values)


def order_columns(df: pd.DataFrame, algorithms: list[AlgorithmConfig]) -> pd.DataFrame:
    original_columns = [
        column
        for column in [
            "dataset",
            "Grafo",
            "|V|",
            "|E|",
            "Densidade",
            "Objetivo",
            "Tempo (s)",
            "Status",
        ]
        if column in df.columns
    ]
    proof_columns = [
        "LB",
        "UB",
        "PLI_gap_prova",
        "PLI_gap_relativo",
        "PLI_dentro_bounds",
    ]
    algorithm_columns: list[str] = []
    for algorithm in algorithms:
        prefix = algorithm.column_prefix
        algorithm_columns.extend(
            [
                prefix,
                f"{prefix}_media",
                f"{prefix}_mediana",
                f"{prefix}_gap_prova",
                f"{prefix}_gap_relativo",
                f"{prefix}_dentro_bounds",
                f"{prefix}_todas_rodadas_dentro_bounds",
                f"{prefix}_rodadas",
                f"{prefix}_melhor_rodada",
                f"{prefix}_melhor_avaliacoes",
                f"{prefix}_melhor_iteracoes",
                f"{prefix}_melhor_tempo_s",
                f"{prefix}_melhor_criterio_parada",
                f"{prefix}_melhor_seed",
                f"{prefix}_tempo_total_s",
                f"{prefix}_valores_rodadas",
                f"{prefix}_json",
            ]
        )

    ordered = original_columns + proof_columns + algorithm_columns
    remaining = [column for column in df.columns if column not in ordered]
    return df[[column for column in ordered + remaining if column in df.columns]]


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "grafico"


def natural_sort_key(value: Any) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", str(value))
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def sort_instances_for_plots(df: pd.DataFrame) -> pd.DataFrame:
    helper = df.assign(_graph_sort_key=df["Grafo"].map(natural_sort_key))
    if "|V|" in helper.columns:
        helper["_vertices_sort_key"] = pd.to_numeric(helper["|V|"], errors="coerce")
        return (
            helper.sort_values(
                ["_vertices_sort_key", "_graph_sort_key"], na_position="last"
            )
            .drop(columns=["_vertices_sort_key", "_graph_sort_key"])
            .reset_index(drop=True)
        )

    return (
        helper.sort_values("_graph_sort_key")
        .drop(columns="_graph_sort_key")
        .reset_index(drop=True)
    )


def algorithm_label(value: str) -> str:
    return ALGORITHM_LABELS.get(value, value.replace("_", "-"))


def clean_obsolete_convergence_csvs(
    output_dir: Path,
    algorithms: list[AlgorithmConfig],
) -> None:
    obsolete_files = [output_dir / "convergencia_melhor_caso.csv"]
    obsolete_files.extend(
        output_dir / f"convergencia_melhor_caso_{algorithm.column_prefix}.csv"
        for algorithm in algorithms
    )

    for path in obsolete_files:
        path.unlink(missing_ok=True)


def plot_best_convergence_curves(
    convergence_tables: dict[str, pd.DataFrame],
    combined: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
) -> int:
    plots_dir = output_dir / "curvas_convergencia"
    if plots_dir.exists():
        shutil.rmtree(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    graph_dataset = dict(zip(combined["Grafo"].map(graph_stem), combined["dataset"]))
    graph_objective = dict(zip(combined["Grafo"].map(graph_stem), combined["Objetivo"]))
    plot_count = 0

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 6.3,
            "legend.title_fontsize": 6.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.edgecolor": "#2B2B2B",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    for graph_name in sorted(graph_dataset, key=natural_sort_key):
        dataset = graph_dataset[graph_name]
        graph_dir = plots_dir / safe_filename(dataset)
        graph_dir.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        plotted = False

        for algorithm in algorithms:
            table = convergence_tables.get(algorithm.column_prefix, pd.DataFrame())
            if table.empty or "Grafo" not in table.columns:
                continue

            curve = table[table["Grafo"].eq(graph_name)].copy()
            if curve.empty:
                continue

            curve["iteration"] = pd.to_numeric(curve["iteration"], errors="coerce")
            curve["best_fitness"] = pd.to_numeric(
                curve["best_fitness"], errors="coerce"
            )
            curve = curve.dropna(subset=["iteration", "best_fitness"]).sort_values(
                "iteration"
            )
            if curve.empty:
                continue

            local_search_values = pd.to_numeric(
                curve["local_search_start"], errors="coerce"
            ).dropna()
            best_value = curve["melhor_valor"].dropna()
            label = algorithm_label(algorithm.column_prefix)
            if not best_value.empty:
                label = f"{label} ({float(best_value.iloc[0]):g})"

            ax.plot(
                curve["iteration"],
                curve["best_fitness"],
                marker="o",
                markersize=3.2,
                linewidth=1.7,
                drawstyle="steps-post",
                color=ALGORITHM_COLORS.get(algorithm.column_prefix),
                markeredgewidth=0.0,
                label=label,
            )
            if not local_search_values.empty:
                local_search_start = float(local_search_values.iloc[0])
                ax.axvline(
                    local_search_start,
                    color=ALGORITHM_COLORS.get(algorithm.column_prefix),
                    linewidth=1.0,
                    linestyle=(0, (2, 3)),
                    alpha=0.75,
                    label=(f"Busca Local ({algorithm_label(algorithm.column_prefix)})"),
                )
            plotted = True

        if not plotted:
            plt.close(fig)
            continue

        objective = graph_objective.get(graph_name)
        if pd.notna(objective):
            ax.axhline(
                float(objective),
                color="#4A4A4A",
                linewidth=1.1,
                linestyle=(0, (4, 3)),
                label=f"PLI ({float(objective):g})",
            )

        ax.set_title(f"Curva de Convergência - Instância {graph_name}", pad=12)
        ax.set_xlabel("Iteração")
        ax.set_ylabel("Melhor Valor Encontrado")
        ax.grid(True, axis="y", color="#D9D9D9", linewidth=0.7)
        ax.grid(True, axis="x", color="#ECECEC", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plot_path = graph_dir / f"{safe_filename(graph_name)}.png"
        place_legend_inside_upper_right(ax, columns=2)
        save_plot_with_external_legend(fig, plot_path)
        plot_count += 1

    return plot_count


def numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def parse_round_values(value: Any) -> list[float]:
    if pd.isna(value):
        return []
    values: list[float] = []
    for item in str(value).split(";"):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except ValueError:
            continue
    return values


def summary_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 6.3,
            "legend.title_fontsize": 6.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.edgecolor": "#2B2B2B",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def add_top_headroom(ax: plt.Axes, fraction: float = 0.22) -> None:
    bottom, top = ax.get_ylim()
    if bottom == top:
        return
    if ax.get_yscale() == "log":
        if bottom > 0 and top > 0:
            ratio = top / bottom
            ax.set_ylim(bottom, top * (ratio**fraction))
        return
    span = top - bottom
    ax.set_ylim(bottom, top + span * fraction)


def place_legend_inside_upper_right(
    ax: plt.Axes,
    title: str | None = None,
    columns: int = 2,
) -> None:
    add_top_headroom(ax)
    ax.legend(
        title=title,
        frameon=True,
        loc="upper right",
        ncol=columns,
        handlelength=1.6,
        columnspacing=0.6,
        handletextpad=0.35,
        borderpad=0.25,
        labelspacing=0.22,
        framealpha=0.88,
        facecolor="white",
        edgecolor="#D9D9D9",
    )


def save_plot_with_external_legend(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def finish_summary_plot(fig: plt.Figure, ax: plt.Axes, path: Path) -> None:
    ax.grid(True, axis="y", color="#D9D9D9", linewidth=0.7)
    ax.grid(True, axis="x", color="#EFEFEF", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_relative_gap_by_instance(
    df: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
) -> int:
    count = 0
    for dataset, subset in df.groupby("dataset", sort=True):
        subset = sort_instances_for_plots(subset)
        x = range(len(subset))
        width = 0.38
        fig_width = max(8.0, min(18.0, len(subset) * 0.28))
        fig, ax = plt.subplots(figsize=(fig_width, 4.8))

        for index, algorithm in enumerate(algorithms):
            column = f"{algorithm.column_prefix}_gap_relativo"
            if column not in subset.columns:
                continue
            offset = (index - (len(algorithms) - 1) / 2) * width
            ax.bar(
                [position + offset for position in x],
                numeric_series(subset, column),
                width=width,
                color=ALGORITHM_COLORS.get(algorithm.column_prefix),
                label=algorithm_label(algorithm.column_prefix),
            )

        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_title(f"Gap Relativo por Instância - {dataset}")
        ax.set_xlabel("Instância")
        ax.set_ylabel("Gap relativo (%)")
        ax.set_xticks(list(x))
        ax.set_xticklabels(subset["Grafo"], rotation=90)
        place_legend_inside_upper_right(ax, columns=2)
        finish_summary_plot(
            fig, ax, output_dir / f"gap_relativo_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_round_gap_boxplots(
    df: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
) -> int:
    count = 0
    for dataset, subset in df.groupby("dataset", sort=True):
        box_data: list[list[float]] = []
        labels: list[str] = []
        colors: list[str | None] = []

        for algorithm in algorithms:
            values_column = f"{algorithm.column_prefix}_valores_rodadas"
            if values_column not in subset.columns:
                continue
            gaps: list[float] = []
            for _, row in subset.iterrows():
                objective = row.get("Objetivo")
                if pd.isna(objective) or float(objective) == 0.0:
                    continue
                for value in parse_round_values(row.get(values_column)):
                    gaps.append(100.0 * (value - float(objective)) / float(objective))
            if gaps:
                box_data.append(gaps)
                labels.append(algorithm_label(algorithm.column_prefix))
                colors.append(ALGORITHM_COLORS.get(algorithm.column_prefix))

        if not box_data:
            continue

        fig, ax = plt.subplots(figsize=(6.8, 4.6))
        boxplot = ax.boxplot(
            box_data,
            tick_labels=labels,
            patch_artist=True,
            showmeans=True,
            meanline=True,
        )
        for patch, color in zip(boxplot["boxes"], colors):
            patch.set_facecolor(color or "#B0B0B0")
            patch.set_alpha(0.72)
        for median in boxplot["medians"]:
            median.set_color("#111111")
            median.set_linewidth(1.2)
        for mean in boxplot["means"]:
            mean.set_color("#FFFFFF")
            mean.set_linewidth(1.0)

        ax.set_title(f"Distribuição do Gap Relativo nas Execuções - {dataset}")
        ax.set_xlabel("Método")
        ax.set_ylabel("Gap relativo por execução (%)")
        finish_summary_plot(
            fig,
            ax,
            output_dir / f"boxplot_gap_relativo_execucoes_{safe_filename(dataset)}.png",
        )
        count += 1
    return count


def plot_best_run_metric_by_instance(
    df: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
    metric_suffix: str,
    title: str,
    ylabel: str,
    output_prefix: str,
    use_log_scale: bool,
) -> int:
    count = 0
    for dataset, subset in df.groupby("dataset", sort=True):
        subset = sort_instances_for_plots(subset)
        x = range(len(subset))
        width = 0.38
        fig_width = max(8.0, min(18.0, len(subset) * 0.28))
        fig, ax = plt.subplots(figsize=(fig_width, 4.8))

        for index, algorithm in enumerate(algorithms):
            column = f"{algorithm.column_prefix}_{metric_suffix}"
            if column not in subset.columns:
                continue
            offset = (index - (len(algorithms) - 1) / 2) * width
            ax.bar(
                [position + offset for position in x],
                numeric_series(subset, column),
                width=width,
                color=ALGORITHM_COLORS.get(algorithm.column_prefix),
                label=algorithm_label(algorithm.column_prefix),
            )

        if use_log_scale:
            ax.set_yscale("log")
        ax.set_title(f"{title} - {dataset}")
        ax.set_xlabel("Instância")
        ax.set_ylabel(ylabel)
        ax.set_xticks(list(x))
        ax.set_xticklabels(subset["Grafo"], rotation=90)
        place_legend_inside_upper_right(ax, columns=2)
        finish_summary_plot(
            fig, ax, output_dir / f"{output_prefix}_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_stop_reason_counts(
    df: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
) -> int:
    rows: list[dict[str, Any]] = []
    for algorithm in algorithms:
        column = f"{algorithm.column_prefix}_melhor_criterio_parada"
        if column not in df.columns:
            continue
        counts = df[column].fillna("indefinido").value_counts().sort_index()
        for reason, count in counts.items():
            rows.append(
                {
                    "Método": algorithm_label(algorithm.column_prefix),
                    "Critério": str(reason),
                    "Quantidade": int(count),
                }
            )

    if not rows:
        return 0

    table = pd.DataFrame(rows)
    pivot = table.pivot(index="Critério", columns="Método", values="Quantidade").fillna(
        0
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    x = range(len(pivot.index))
    width = 0.38
    methods = list(pivot.columns)
    for index, method in enumerate(methods):
        offset = (index - (len(methods) - 1) / 2) * width
        color = None
        for algorithm in algorithms:
            if algorithm_label(algorithm.column_prefix) == method:
                color = ALGORITHM_COLORS.get(algorithm.column_prefix)
                break
        ax.bar(
            [position + offset for position in x],
            pivot[method],
            width=width,
            color=color,
            label=method,
        )

    ax.set_title("Critério de Parada da Melhor Execução")
    ax.set_xlabel("Critério de parada")
    ax.set_ylabel("Quantidade de instâncias")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index, rotation=0)
    place_legend_inside_upper_right(ax, columns=2)
    finish_summary_plot(fig, ax, output_dir / "criterio_parada_melhor_execucao.png")
    return 1


def plot_summary_charts(
    combined: pd.DataFrame,
    algorithms: list[AlgorithmConfig],
    output_dir: Path,
) -> int:
    charts_dir = output_dir / "graficos_resumo"
    if charts_dir.exists():
        shutil.rmtree(charts_dir)
    charts_dir.mkdir(parents=True, exist_ok=True)
    summary_plot_style()

    count = 0
    count += plot_relative_gap_by_instance(combined, algorithms, charts_dir)
    count += plot_round_gap_boxplots(combined, algorithms, charts_dir)
    count += plot_best_run_metric_by_instance(
        combined,
        algorithms,
        charts_dir,
        "melhor_tempo_s",
        "Tempo da Melhor Execução",
        "Tempo (s)",
        "tempo_melhor_execucao",
        use_log_scale=True,
    )
    count += plot_best_run_metric_by_instance(
        combined,
        algorithms,
        charts_dir,
        "melhor_avaliacoes",
        "Avaliações da Melhor Execução",
        "Número de avaliações",
        "avaliacoes_melhor_execucao",
        use_log_scale=True,
    )
    count += plot_stop_reason_counts(combined, algorithms, charts_dir)
    return count


def plain_method_label(method: str) -> str:
    if method == "PLI":
        return "PLI"
    if method == "ACO_TS":
        return "ACO_R-TS"
    if method == "HHO_RVNS":
        return "HHO-RVNS"
    return method


def plot_method_label(method: str) -> str:
    if method == "PLI":
        return "PLI"
    return algorithm_label(method)


def holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [math.nan] * m
    running_max = 0.0
    for rank, (index, p_value) in enumerate(indexed):
        corrected = min((m - rank) * p_value, 1.0)
        running_max = max(running_max, corrected)
        adjusted[index] = running_max
    return adjusted


def safe_wilcoxon(x: pd.Series, y: pd.Series) -> tuple[float, float, str]:
    paired = pd.DataFrame({"x": x, "y": y}).dropna()
    if paired.empty:
        return math.nan, math.nan, "sem_dados"

    differences = paired["x"] - paired["y"]
    if (differences.abs() <= EPS).all():
        return 0.0, 1.0, "todos_empates"

    try:
        result = stats.wilcoxon(paired["x"], paired["y"], zero_method="wilcox")
    except ValueError as error:
        return math.nan, math.nan, str(error)
    return float(result.statistic), float(result.pvalue), "ok"


def method_value_table(df: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    columns = {"PLI": "Objetivo", "HHO_RVNS": "HHO_RVNS", "ACO_TS": "ACO_TS"}
    table = pd.DataFrame({"dataset": df["dataset"], "Grafo": df["Grafo"]})
    for method in methods:
        table[method] = numeric_series(df, columns[method])
    return table.dropna(subset=methods)


def mean_rank_table(values: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    ranks = values[methods].rank(axis=1, method="average", ascending=True)
    rows = []
    for method in methods:
        rows.append(
            {
                "metodo": method,
                "rotulo": plain_method_label(method),
                "rank_medio": float(ranks[method].mean()),
                "rank_mediano": float(ranks[method].median()),
                "melhor_em_instancias": int((ranks[method] == ranks.min(axis=1)).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("rank_medio")


def run_friedman_with_pli(
    combined: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    methods = ["PLI", "HHO_RVNS", "ACO_TS"]
    rows = []
    rank_frames = []

    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )

    for dataset, subset in groups:
        values = method_value_table(subset, methods)
        if len(values) < 2:
            rows.append(
                {
                    "dataset": dataset,
                    "metodos": ",".join(methods),
                    "n_instancias": len(values),
                    "estatistica": math.nan,
                    "p_valor": math.nan,
                    "observacao": "instancias_insuficientes",
                }
            )
            continue

        result = stats.friedmanchisquare(*(values[method] for method in methods))
        rows.append(
            {
                "dataset": dataset,
                "metodos": ",".join(methods),
                "n_instancias": len(values),
                "estatistica": float(result.statistic),
                "p_valor": float(result.pvalue),
                "observacao": "analise_complementar_inclui_pli",
            }
        )
        ranks = mean_rank_table(values, methods)
        ranks.insert(0, "dataset", dataset)
        rank_frames.append(ranks)

    friedman_df = pd.DataFrame(rows)
    ranks_df = (
        pd.concat(rank_frames, ignore_index=True) if rank_frames else pd.DataFrame()
    )
    friedman_df.to_csv(output_dir / "friedman_com_pli.csv", index=False)
    ranks_df.to_csv(output_dir / "ranks_medios_com_pli.csv", index=False)
    return friedman_df, ranks_df


def run_pairwise_wilcoxon_with_pli(
    combined: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    methods = ["PLI", "HHO_RVNS", "ACO_TS"]
    pairs = [("PLI", "HHO_RVNS"), ("PLI", "ACO_TS"), ("HHO_RVNS", "ACO_TS")]
    rows = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )

    for dataset, subset in groups:
        values = method_value_table(subset, methods)
        p_values: list[float] = []
        start = len(rows)
        for method_a, method_b in pairs:
            statistic, p_value, status = safe_wilcoxon(
                values[method_a], values[method_b]
            )
            p_values.append(p_value if not math.isnan(p_value) else 1.0)
            rows.append(
                {
                    "dataset": dataset,
                    "metodo_a": method_a,
                    "metodo_b": method_b,
                    "rotulo_a": plain_method_label(method_a),
                    "rotulo_b": plain_method_label(method_b),
                    "n_instancias": len(values),
                    "estatistica": statistic,
                    "p_valor": p_value,
                    "p_valor_holm": math.nan,
                    "status": status,
                    "observacao": "pos_hoc_com_pli",
                }
            )

        adjusted = holm_adjust(p_values)
        for offset, p_adjusted in enumerate(adjusted):
            rows[start + offset]["p_valor_holm"] = p_adjusted

    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "wilcoxon_pos_hoc_com_pli.csv", index=False)
    return result


def run_metaheuristic_wilcoxon(
    combined: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    rows = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )

    for dataset, subset in groups:
        objective = numeric_series(subset, "Objetivo")
        variables = [
            (
                "gap_relativo_melhor",
                numeric_series(subset, "HHO_RVNS_gap_relativo"),
                numeric_series(subset, "ACO_TS_gap_relativo"),
            ),
            (
                "gap_relativo_mediano_das_10_execucoes",
                100.0
                * (numeric_series(subset, "HHO_RVNS_mediana") - objective)
                / objective,
                100.0
                * (numeric_series(subset, "ACO_TS_mediana") - objective)
                / objective,
            ),
        ]
        for variable, gap_a, gap_b in variables:
            paired = pd.DataFrame({"hho": gap_a, "aco": gap_b}).dropna()
            differences = paired["hho"] - paired["aco"]
            statistic, p_value, status = safe_wilcoxon(paired["hho"], paired["aco"])
            rows.append(
                {
                    "dataset": dataset,
                    "comparacao": "HHO_RVNS_vs_ACO_TS",
                    "variavel": variable,
                    "n_instancias": len(paired),
                    "HHO_RVNS_menor_gap": int((differences < -EPS).sum()),
                    "ACO_TS_menor_gap": int((differences > EPS).sum()),
                    "empates": int((differences.abs() <= EPS).sum()),
                    "mediana_gap_HHO_RVNS": float(paired["hho"].median()),
                    "mediana_gap_ACO_TS": float(paired["aco"].median()),
                    "mediana_diferenca_HHO_menos_ACO": float(differences.median()),
                    "estatistica": statistic,
                    "p_valor": p_value,
                    "status": status,
                    "observacao": "comparacao_principal_metaheuristicas",
                }
            )

    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "wilcoxon_metaheuristicas_gap_relativo.csv", index=False)
    return result


def plot_mean_ranks(ranks: pd.DataFrame, output_dir: Path) -> int:
    if ranks.empty:
        return 0

    all_ranks = ranks[ranks["dataset"].eq("TODOS")].copy()
    if all_ranks.empty:
        return 0

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    labels = [plot_method_label(method) for method in all_ranks["metodo"]]
    colors = [
        "#5A5A5A" if method == "PLI" else ALGORITHM_COLORS.get(method, "#B0B0B0")
        for method in all_ranks["metodo"]
    ]
    ax.bar(labels, all_ranks["rank_medio"], color=colors, width=0.55)
    ax.set_title("Rank Médio dos Métodos")
    ax.set_xlabel("Método")
    ax.set_ylabel("Rank médio (menor é melhor)")
    finish_summary_plot(fig, ax, output_dir / "ranks_medios_com_pli.png")
    return 1


def plot_mean_ranks_by_dataset(ranks: pd.DataFrame, output_dir: Path) -> int:
    if ranks.empty:
        return 0

    subset = ranks[~ranks["dataset"].eq("TODOS")].copy()
    if subset.empty:
        return 0

    datasets = sorted(subset["dataset"].unique())
    methods = ["PLI", "ACO_TS", "HHO_RVNS"]
    x = range(len(datasets))
    width = 0.24
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    for index, method in enumerate(methods):
        values = []
        for dataset in datasets:
            row = subset[subset["dataset"].eq(dataset) & subset["metodo"].eq(method)]
            values.append(
                float(row["rank_medio"].iloc[0]) if not row.empty else math.nan
            )
        offset = (index - (len(methods) - 1) / 2) * width
        color = "#5A5A5A" if method == "PLI" else ALGORITHM_COLORS.get(method)
        ax.bar(
            [position + offset for position in x],
            values,
            width=width,
            color=color,
            label=plot_method_label(method),
        )

    ax.set_title("Rank Médio por Conjunto de Instâncias")
    ax.set_xlabel("Conjunto")
    ax.set_ylabel("Rank médio (menor é melhor)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(datasets)
    place_legend_inside_upper_right(ax, columns=3)
    finish_summary_plot(fig, ax, output_dir / "ranks_medios_por_conjunto_com_pli.png")
    return 1


def plot_metaheuristic_gap_scatter(combined: pd.DataFrame, output_dir: Path) -> int:
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    x = numeric_series(combined, "ACO_TS_gap_relativo")
    y = numeric_series(combined, "HHO_RVNS_gap_relativo")
    paired = pd.DataFrame({"x": x, "y": y, "dataset": combined["dataset"]}).dropna()
    if paired.empty:
        plt.close(fig)
        return 0

    dataset_colors = {"CUBIC": "#3D6FB6", "DIMACS": "#6A8E3D", "HB": "#A65F3D"}
    for dataset, subset in paired.groupby("dataset", sort=True):
        ax.scatter(
            subset["x"],
            subset["y"],
            s=24,
            alpha=0.78,
            color=dataset_colors.get(dataset, "#808080"),
            label=dataset,
        )

    min_value = min(float(paired["x"].min()), float(paired["y"].min()))
    max_value = max(float(paired["x"].max()), float(paired["y"].max()))
    ax.plot(
        [min_value, max_value], [min_value, max_value], color="#333333", linewidth=1.0
    )
    ax.set_title("Comparação do Gap Relativo das Meta-heurísticas")
    ax.set_xlabel(r"Gap relativo do $\mathrm{ACO}_{\mathbb{R}}$-TS (%)")
    ax.set_ylabel("Gap relativo do HHO-RVNS (%)")
    place_legend_inside_upper_right(ax, columns=3)
    finish_summary_plot(
        fig, ax, output_dir / "dispersao_gap_relativo_metaheuristicas.png"
    )
    return 1


def format_p_value(value: float) -> str:
    if math.isnan(value):
        return "NA"
    if value < 0.001:
        return f"{value:.3e}"
    return f"{value:.4f}"


def describe_significance(p_value: float, alpha: float = 0.05) -> str:
    if math.isnan(p_value):
        return "resultado indisponível"
    if p_value < alpha:
        return f"diferença estatisticamente significativa (p < {alpha})"
    return f"sem evidência de diferença estatisticamente significativa (p >= {alpha})"


def gap_summary_by_group(combined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )
    for dataset, subset in groups:
        hho = numeric_series(subset, "HHO_RVNS_gap_relativo")
        aco = numeric_series(subset, "ACO_TS_gap_relativo")
        rows.append(
            {
                "dataset": dataset,
                "n_instancias": len(subset),
                "HHO_RVNS_gap_medio": float(hho.mean()),
                "HHO_RVNS_gap_mediano": float(hho.median()),
                "ACO_TS_gap_medio": float(aco.mean()),
                "ACO_TS_gap_mediano": float(aco.median()),
                "melhor_mediana": (
                    "HHO_RVNS"
                    if hho.median() < aco.median()
                    else "ACO_TS"
                    if aco.median() < hho.median()
                    else "empate"
                ),
            }
        )
    return pd.DataFrame(rows)


def write_statistical_report(
    combined: pd.DataFrame,
    friedman: pd.DataFrame,
    ranks: pd.DataFrame,
    meta_wilcoxon: pd.DataFrame,
    output_dir: Path,
) -> Path:
    gap_summary = gap_summary_by_group(combined)
    gap_summary.to_csv(output_dir / "resumo_gaps_metaheuristicas.csv", index=False)

    lines = [
        "Relatório de análise estatística",
        "================================",
        "",
        "Convenção adotada:",
        "- Menores valores da função objetivo são melhores.",
        "- O gap relativo foi calculado em relação ao valor do PLI de cada instância.",
        "- A comparação principal entre meta-heurísticas usa Wilcoxon signed-rank sobre gaps relativos pareados por instância.",
        "- Foram reportadas duas leituras para as meta-heurísticas: gap do melhor valor e gap mediano das 10 execuções.",
        "- A análise com Friedman inclui o PLI apenas como referência complementar, pois o PLI não é uma meta-heurística estocástica.",
        "",
        "Como interpretar os testes:",
        "- O teste de Friedman compara três ou mais métodos em blocos pareados; aqui cada instância é um bloco.",
        "- O teste de Wilcoxon signed-rank compara dois métodos pareados; ele considera os sinais e os postos das magnitudes das diferenças.",
        "- Portanto, contar em quantas instâncias um método foi melhor não é equivalente ao teste estatístico.",
        "- Muitos empates e diferenças pequenas podem enfraquecer a evidência estatística, mesmo quando um método vence em várias instâncias.",
        "- Diferenças fortes em sentidos opostos entre conjuntos distintos também podem se cancelar quando todos os conjuntos são agregados.",
        "",
        "Arquivos estatísticos gerados:",
        "- friedman_com_pli.csv: resultado do teste de Friedman para PLI, HHO-RVNS e ACO_R-TS.",
        "- ranks_medios_com_pli.csv: ranks médios usados para interpretar o Friedman; menor rank indica melhor desempenho relativo.",
        "- wilcoxon_pos_hoc_com_pli.csv: comparações par-a-par após Friedman, com correção de Holm.",
        "- wilcoxon_metaheuristicas_gap_relativo.csv: comparação direta entre HHO-RVNS e ACO_R-TS.",
        "- resumo_gaps_metaheuristicas.csv: estatísticas descritivas dos gaps por conjunto.",
        "- ranks_medios_com_pli.png: visualização dos ranks médios no conjunto completo.",
        "- ranks_medios_por_conjunto_com_pli.png: ranks médios separados por conjunto de instâncias.",
        "- dispersao_gap_relativo_metaheuristicas.png: compara os gaps relativos das duas meta-heurísticas instância a instância.",
        "",
        "Significado das principais colunas:",
        "- dataset: conjunto de instâncias analisado; TODOS agrega CUBIC, DIMACS e HB.",
        "- n_instancias: quantidade de pares/blocos usados no teste.",
        "- estatistica: valor da estatística calculada pelo teste.",
        "- p_valor: probabilidade, sob a hipótese nula, de observar diferenças tão extremas quanto as obtidas.",
        "- p_valor_holm: p-valor ajustado pela correção de Holm em comparações múltiplas.",
        "- HHO_RVNS_menor_gap / ACO_TS_menor_gap: número de instâncias em que cada meta-heurística teve menor gap.",
        "- empates: número de instâncias em que os gaps comparados foram iguais ou numericamente indistinguíveis.",
        "- mediana_diferenca_HHO_menos_ACO: mediana da diferença pareada entre gaps; valor positivo favorece ACO_R-TS e negativo favorece HHO-RVNS.",
        "",
        "Comparação principal entre meta-heurísticas",
        "-------------------------------------------",
    ]

    for _, row in meta_wilcoxon.iterrows():
        dataset = row["dataset"]
        summary = gap_summary[gap_summary["dataset"].eq(dataset)].iloc[0]
        lines.extend(
            [
                f"- {dataset} ({row['variavel']}): n={int(row['n_instancias'])}, "
                f"p={format_p_value(float(row['p_valor']))}; "
                f"{describe_significance(float(row['p_valor']))}.",
                f"  Menor gap: HHO-RVNS em {int(row['HHO_RVNS_menor_gap'])} instâncias; "
                f"ACO_R-TS em {int(row['ACO_TS_menor_gap'])}; "
                f"empates em {int(row['empates'])}.",
                f"  Gap mediano HHO-RVNS = {float(row['mediana_gap_HHO_RVNS']):.4f}%; "
                f"gap mediano ACO_R-TS = {float(row['mediana_gap_ACO_TS']):.4f}%; "
                f"mediana(HHO - ACO) = {float(row['mediana_diferenca_HHO_menos_ACO']):.4f} pontos percentuais.",
            ]
        )

    lines.extend(
        [
            "",
            "Análise complementar incluindo PLI",
            "----------------------------------",
        ]
    )
    for _, row in friedman.iterrows():
        lines.append(
            f"- {row['dataset']}: Friedman chi2={float(row['estatistica']):.4f}, "
            f"p={format_p_value(float(row['p_valor']))}; "
            f"{describe_significance(float(row['p_valor']))}."
        )

    if not ranks.empty:
        lines.extend(["", "Ranks médios globais", "---------------------"])
        global_ranks = ranks[ranks["dataset"].eq("TODOS")].sort_values("rank_medio")
        for _, row in global_ranks.iterrows():
            lines.append(
                f"- {plain_method_label(str(row['metodo']))}: "
                f"rank médio = {float(row['rank_medio']):.4f}; "
                f"melhor/empatado em {int(row['melhor_em_instancias'])} instâncias."
            )

    lines.extend(
        [
            "",
            "Interpretação prática dos resultados",
            "------------------------------------",
            "- No conjunto agregado, a comparação pelo melhor gap não indica diferença estatisticamente significativa entre as meta-heurísticas.",
            "- Isso não significa que os métodos sejam idênticos; significa que, considerando todas as instâncias juntas, as diferenças pareadas não foram consistentes o suficiente para rejeitar a hipótese nula.",
            "- Separando por conjunto, aparecem diferenças significativas, indicando comportamento dependente da classe de instâncias.",
            "- Em CUBIC, ACO_R-TS apresenta desempenho claramente superior nas comparações pareadas.",
            "- Em DIMACS, HHO-RVNS apresenta vantagem em qualidade de solução em relação ao ACO_R-TS.",
            "- Em HB, ACO_R-TS tende a apresentar menores gaps, embora a diferença seja mais moderada que em CUBIC.",
            "- O PLI deve ser tratado como referência de qualidade, não como método estocástico comparável em igualdade experimental às meta-heurísticas.",
            "- Quando uma meta-heurística supera o PLI, isso normalmente indica que o PLI não provou otimalidade dentro do limite de tempo, não que a heurística superou uma solução ótima certificada.",
        ]
    )

    lines.extend(
        [
            "",
            "Gráficos recomendados para comentar no texto",
            "--------------------------------------------",
            "- graficos_resumo/gap_relativo_*.png: principal evidência de qualidade por instância.",
            "- graficos_resumo/boxplot_gap_relativo_execucoes_*.png: estabilidade das 10 execuções.",
            "- graficos_resumo/tempo_melhor_execucao_*.png: custo computacional da melhor execução.",
            "- graficos_resumo/avaliacoes_melhor_execucao_*.png: esforço algorítmico em número de avaliações.",
            "- graficos_resumo/criterio_parada_melhor_execucao.png: comportamento dos critérios de parada.",
            "- analise_estatistica/dispersao_gap_relativo_metaheuristicas.png: comparação direta entre meta-heurísticas.",
            "- analise_estatistica/ranks_medios_por_conjunto_com_pli.png: visão compacta dos ranks por conjunto.",
            "",
            "Observação para o texto do TCC:",
            "Use o PLI como referência de qualidade, mas evite apresentá-lo como concorrente estocástico equivalente às meta-heurísticas.",
        ]
    )

    report_path = output_dir / "relatorio_analise_estatistica.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_statistical_analysis(
    combined: pd.DataFrame,
    output_dir: Path,
) -> int:
    stats_dir = output_dir / "analise_estatistica"
    if stats_dir.exists():
        shutil.rmtree(stats_dir)
    stats_dir.mkdir(parents=True, exist_ok=True)
    summary_plot_style()

    friedman, ranks = run_friedman_with_pli(combined, stats_dir)
    run_pairwise_wilcoxon_with_pli(combined, stats_dir)
    meta_wilcoxon = run_metaheuristic_wilcoxon(combined, stats_dir)
    write_statistical_report(combined, friedman, ranks, meta_wilcoxon, stats_dir)

    plot_count = 0
    plot_count += plot_mean_ranks(ranks, stats_dir)
    plot_count += plot_mean_ranks_by_dataset(ranks, stats_dir)
    plot_count += plot_metaheuristic_gap_scatter(combined, stats_dir)
    return plot_count


def winner_counts(subset: pd.DataFrame, methods: dict[str, str]) -> dict[str, int]:
    values = subset[list(methods.values())].copy()
    values.columns = list(methods.keys())
    best = values.min(axis=1, skipna=True)
    return {method: int((values[method] == best).sum()) for method in methods}


def strict_winner_counts(
    subset: pd.DataFrame, methods: dict[str, str]
) -> dict[str, int]:
    values = subset[list(methods.values())].copy()
    values.columns = list(methods.keys())
    counts: dict[str, int] = {}
    for method in methods:
        other_methods = [other for other in methods if other != method]
        counts[method] = int((values[method] < values[other_methods].min(axis=1)).sum())
    return counts


def build_general_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )
    methods = {"PLI": "Objetivo", "HHO_RVNS": "HHO_RVNS", "ACO_TS": "ACO_TS"}

    for dataset, subset in groups:
        winners = winner_counts(subset, methods)
        strict_winners = strict_winner_counts(subset, methods)
        row: dict[str, Any] = {
            "dataset": dataset,
            "n_instancias": len(subset),
            "vertices_min": int(numeric_series(subset, "|V|").min()),
            "vertices_max": int(numeric_series(subset, "|V|").max()),
            "arestas_min": int(numeric_series(subset, "|E|").min()),
            "arestas_max": int(numeric_series(subset, "|E|").max()),
            "PLI_melhor_ou_empate": winners["PLI"],
            "HHO_RVNS_melhor_ou_empate": winners["HHO_RVNS"],
            "ACO_TS_melhor_ou_empate": winners["ACO_TS"],
            "PLI_vitoria_estrita": strict_winners["PLI"],
            "HHO_RVNS_vitoria_estrita": strict_winners["HHO_RVNS"],
            "ACO_TS_vitoria_estrita": strict_winners["ACO_TS"],
        }

        for prefix in ["HHO_RVNS", "ACO_TS"]:
            row[f"{prefix}_gap_medio"] = float(
                numeric_series(subset, f"{prefix}_gap_relativo").mean()
            )
            row[f"{prefix}_gap_mediano"] = float(
                numeric_series(subset, f"{prefix}_gap_relativo").median()
            )
            row[f"{prefix}_gap_min"] = float(
                numeric_series(subset, f"{prefix}_gap_relativo").min()
            )
            row[f"{prefix}_gap_max"] = float(
                numeric_series(subset, f"{prefix}_gap_relativo").max()
            )
            row[f"{prefix}_melhor_que_PLI"] = int(
                (numeric_series(subset, f"{prefix}_gap_relativo") < -EPS).sum()
            )
            row[f"{prefix}_empate_com_PLI"] = int(
                (numeric_series(subset, f"{prefix}_gap_relativo").abs() <= EPS).sum()
            )
            row[f"{prefix}_pior_que_PLI"] = int(
                (numeric_series(subset, f"{prefix}_gap_relativo") > EPS).sum()
            )
            row[f"{prefix}_tempo_mediano_s"] = float(
                numeric_series(subset, f"{prefix}_melhor_tempo_s").median()
            )
            row[f"{prefix}_tempo_medio_s"] = float(
                numeric_series(subset, f"{prefix}_melhor_tempo_s").mean()
            )
            row[f"{prefix}_avaliacoes_medianas"] = float(
                numeric_series(subset, f"{prefix}_melhor_avaliacoes").median()
            )
            row[f"{prefix}_avaliacoes_medias"] = float(
                numeric_series(subset, f"{prefix}_melhor_avaliacoes").mean()
            )

        rows.append(row)

    return pd.DataFrame(rows)


def stop_reason_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )
    for dataset, subset in groups:
        for prefix in ["HHO_RVNS", "ACO_TS"]:
            column = f"{prefix}_melhor_criterio_parada"
            counts = subset[column].fillna("indefinido").value_counts().sort_index()
            for reason, count in counts.items():
                rows.append(
                    {
                        "dataset": dataset,
                        "metodo": prefix,
                        "criterio_parada": reason,
                        "quantidade": int(count),
                    }
                )
    return pd.DataFrame(rows)


def pli_status_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )
    for dataset, subset in groups:
        status = subset["Status"].astype(str)
        optimal = int(status.str.casefold().eq("ótimo").sum())
        best = int(status.str.casefold().eq("melhor").sum())
        rows.append(
            {
                "Base": dataset,
                "Instâncias": len(subset),
                "Ótimos": optimal,
                "Melhor": best,
                "% Ótimos": 100.0 * optimal / len(subset) if len(subset) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def basic_method_analysis(combined: pd.DataFrame) -> pd.DataFrame:
    methods = {"PLI": "Objetivo", "HHO_RVNS": "HHO_RVNS", "ACO_TS": "ACO_TS"}
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )

    for dataset, subset in groups:
        values = subset[list(methods.values())].copy()
        values.columns = list(methods.keys())
        best = values.min(axis=1, skipna=True)
        for method in methods:
            others = [other for other in methods if other != method]
            equals_any_other = (values[method].to_numpy()[:, None] == values[others].to_numpy()).any(axis=1)
            row = {
                "dataset": dataset,
                "metodo": method,
                "rotulo": plain_method_label(method),
                "instancias": len(subset),
                "melhor_ou_empate": int((values[method] == best).sum()),
                "vitoria_estrita": int((values[method] < values[others].min(axis=1)).sum()),
                "igual_a_algum_metodo": int(equals_any_other.sum()),
                "igual_ao_PLI": int((values[method] == values["PLI"]).sum()) if method != "PLI" else len(subset),
                "igual_ao_HHO_RVNS": int((values[method] == values["HHO_RVNS"]).sum()) if method != "HHO_RVNS" else len(subset),
                "igual_ao_ACO_TS": int((values[method] == values["ACO_TS"]).sum()) if method != "ACO_TS" else len(subset),
            }
            if method != "PLI":
                gap = numeric_series(subset, f"{method}_gap_relativo")
                row["gap_medio"] = float(gap.mean())
                row["gap_mediano"] = float(gap.median())
                row["melhor_que_PLI"] = int((gap < -EPS).sum())
                row["empate_com_PLI"] = int((gap.abs() <= EPS).sum())
                row["pior_que_PLI"] = int((gap > EPS).sum())
            else:
                row["gap_medio"] = 0.0
                row["gap_mediano"] = 0.0
                row["melhor_que_PLI"] = 0
                row["empate_com_PLI"] = len(subset)
                row["pior_que_PLI"] = 0
            rows.append(row)

    return pd.DataFrame(rows)


def pairwise_equality_summary(combined: pd.DataFrame) -> pd.DataFrame:
    methods = {"PLI": "Objetivo", "HHO_RVNS": "HHO_RVNS", "ACO_TS": "ACO_TS"}
    pairs = [("PLI", "HHO_RVNS"), ("PLI", "ACO_TS"), ("HHO_RVNS", "ACO_TS")]
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("TODOS", combined)]
    groups.extend(
        (dataset, subset) for dataset, subset in combined.groupby("dataset", sort=True)
    )
    for dataset, subset in groups:
        values = subset[list(methods.values())].copy()
        values.columns = list(methods.keys())
        for method_a, method_b in pairs:
            diff = values[method_a] - values[method_b]
            rows.append(
                {
                    "dataset": dataset,
                    "metodo_a": method_a,
                    "metodo_b": method_b,
                    "a_melhor": int((diff < -EPS).sum()),
                    "b_melhor": int((diff > EPS).sum()),
                    "iguais": int((diff.abs() <= EPS).sum()),
                    "instancias": len(subset),
                }
            )
    return pd.DataFrame(rows)


def write_general_results_report(
    combined: pd.DataFrame,
    violations: pd.DataFrame,
    output_dir: Path,
) -> Path:
    summary = build_general_summary(combined)
    stop_summary = stop_reason_summary(combined)
    pli_summary = pli_status_summary(combined)
    method_summary = basic_method_analysis(combined)
    equality_summary = pairwise_equality_summary(combined)
    summary.to_csv(output_dir / "resumo_resultados.csv", index=False)
    stop_summary.to_csv(output_dir / "resumo_criterios_parada.csv", index=False)
    pli_summary.to_csv(output_dir / "resumo_status_pli.csv", index=False)
    method_summary.to_csv(output_dir / "resumo_basico_metodos.csv", index=False)
    equality_summary.to_csv(output_dir / "resumo_igualdades_pareadas.csv", index=False)

    lines = [
        "Relatório geral dos resultados",
        "==============================",
        "",
        "Escopo dos arquivos gerados:",
        f"- Instâncias analisadas: {len(combined)}.",
        "- Cada meta-heurística possui 10 execuções por instância.",
        "- Os gaps das meta-heurísticas são calculados em relação ao valor reportado pelo PLI.",
        f"- Violações dos bounds encontradas: {len(violations)}.",
        "",
        "Arquivos principais gerados:",
        "- resultados_definitivos.csv: tabela combinada com todos os conjuntos.",
        "- *_definitivo.csv: tabelas separadas por conjunto de instâncias.",
        "- violacoes_bounds.csv: lista de soluções fora do intervalo [LB, UB], se houver.",
        "- resumo_resultados.csv: resumo descritivo por conjunto.",
        "- resumo_criterios_parada.csv: distribuição dos critérios de parada por método e conjunto.",
        "- resumo_status_pli.csv: quantidade de instâncias ótimas e melhores do PLI por base.",
        "- resumo_basico_metodos.csv: vitórias, empates e gaps por método.",
        "- resumo_igualdades_pareadas.csv: comparação par-a-par de igualdade e superioridade entre métodos.",
        "- relatorio_resultados.txt: este relatório textual.",
        "- curvas_convergencia/: curvas do melhor caso de cada meta-heurística por instância.",
        "- graficos_resumo/: gráficos agregados de qualidade, robustez e custo computacional.",
        "",
        "Significado das principais medidas:",
        "- Objetivo: valor reportado pelo modelo PLI.",
        "- LB e UB: limites inferior e superior derivados das propriedades estruturais do grafo.",
        "- HHO_RVNS e ACO_TS: melhor valor encontrado nas 10 execuções da respectiva meta-heurística.",
        "- *_media e *_mediana: média e mediana dos valores obtidos nas 10 execuções.",
        "- *_gap_prova: diferença entre o valor da meta-heurística e o valor do PLI.",
        "- *_gap_relativo: gap percentual em relação ao valor do PLI.",
        "- *_melhor_avaliacoes: número de avaliações na execução que produziu o melhor valor.",
        "- *_melhor_iteracoes: número de iterações da execução que produziu o melhor valor.",
        "- *_melhor_tempo_s: tempo da execução que produziu o melhor valor.",
        "- *_melhor_criterio_parada: mecanismo que encerrou a execução de melhor valor.",
        "- *_valores_rodadas: lista dos valores obtidos nas 10 execuções.",
        "",
        "Como interpretar os gaps:",
        "- Gap igual a 0 indica que a meta-heurística alcançou o mesmo valor reportado pelo PLI.",
        "- Gap positivo indica solução pior que o valor reportado pelo PLI.",
        "- Gap negativo indica solução melhor que o valor reportado pelo PLI dentro do limite de tempo.",
        "- Gap negativo não invalida o PLI; em instâncias com status 'Melhor', o PLI pode não ter certificado otimalidade.",
        "",
        "Resumo por conjunto",
        "-------------------",
    ]

    for _, row in summary.iterrows():
        dataset = row["dataset"]
        lines.extend(
            [
                f"- {dataset}: {int(row['n_instancias'])} instâncias; "
                f"|V| de {int(row['vertices_min'])} a {int(row['vertices_max'])}; "
                f"|E| de {int(row['arestas_min'])} a {int(row['arestas_max'])}.",
                f"  Melhores valores ou empates: PLI={int(row['PLI_melhor_ou_empate'])}, "
                f"HHO-RVNS={int(row['HHO_RVNS_melhor_ou_empate'])}, "
                f"ACO_R-TS={int(row['ACO_TS_melhor_ou_empate'])}.",
                f"  Vitórias estritas: PLI={int(row['PLI_vitoria_estrita'])}, "
                f"HHO-RVNS={int(row['HHO_RVNS_vitoria_estrita'])}, "
                f"ACO_R-TS={int(row['ACO_TS_vitoria_estrita'])}.",
                f"  Gap mediano: HHO-RVNS={row['HHO_RVNS_gap_mediano']:.4f}%; "
                f"ACO_R-TS={row['ACO_TS_gap_mediano']:.4f}%.",
                f"  Melhor que o PLI: HHO-RVNS={int(row['HHO_RVNS_melhor_que_PLI'])}; "
                f"ACO_R-TS={int(row['ACO_TS_melhor_que_PLI'])}. "
                f"Empates com PLI: HHO-RVNS={int(row['HHO_RVNS_empate_com_PLI'])}; "
                f"ACO_R-TS={int(row['ACO_TS_empate_com_PLI'])}.",
                f"  Tempo mediano da melhor execução: HHO-RVNS={row['HHO_RVNS_tempo_mediano_s']:.4f}s; "
                f"ACO_R-TS={row['ACO_TS_tempo_mediano_s']:.4f}s.",
                f"  Avaliações medianas da melhor execução: HHO-RVNS={row['HHO_RVNS_avaliacoes_medianas']:.0f}; "
                f"ACO_R-TS={row['ACO_TS_avaliacoes_medianas']:.0f}.",
            ]
        )

    lines.extend(["", "Status do PLI por base", "----------------------"])
    for _, row in pli_summary.iterrows():
        lines.append(
            f"- {row['Base']}: {int(row['Instâncias'])} instâncias; "
            f"ótimos={int(row['Ótimos'])}; melhor={int(row['Melhor'])}; "
            f"% ótimos={float(row['% Ótimos']):.2f}%."
        )

    lines.extend(["", "Análise básica por método", "-------------------------"])
    for dataset, subset in method_summary.groupby("dataset", sort=True):
        lines.append(f"- {dataset}:")
        for _, row in subset.iterrows():
            lines.append(
                f"  {row['rotulo']}: melhor/empate={int(row['melhor_ou_empate'])}; "
                f"vitórias estritas={int(row['vitoria_estrita'])}; "
                f"igual a algum método={int(row['igual_a_algum_metodo'])}; "
                f"gap mediano={float(row['gap_mediano']):.4f}%."
            )

    lines.extend(["", "Igualdades e superioridade par-a-par", "------------------------------------"])
    for dataset, subset in equality_summary.groupby("dataset", sort=True):
        lines.append(f"- {dataset}:")
        for _, row in subset.iterrows():
            lines.append(
                f"  {plain_method_label(str(row['metodo_a']))} vs "
                f"{plain_method_label(str(row['metodo_b']))}: "
                f"{plain_method_label(str(row['metodo_a']))} melhor={int(row['a_melhor'])}; "
                f"{plain_method_label(str(row['metodo_b']))} melhor={int(row['b_melhor'])}; "
                f"iguais={int(row['iguais'])}."
            )

    lines.extend(
        [
            "",
            "Critérios de parada",
            "-------------------",
        ]
    )
    for dataset, subset in stop_summary.groupby("dataset", sort=True):
        lines.append(f"- {dataset}:")
        for _, row in subset.iterrows():
            lines.append(
                f"  {plain_method_label(str(row['metodo']))}: "
                f"{row['criterio_parada']} = {int(row['quantidade'])}."
            )

    lines.extend(
        [
            "",
            "Gráficos mais indicados para comentar",
            "-------------------------------------",
            "- gap_relativo_*.png: qualidade final por instância e comparação direta com o PLI.",
            "- boxplot_gap_relativo_execucoes_*.png: robustez das 10 execuções.",
            "- tempo_melhor_execucao_*.png: custo computacional da melhor execução.",
            "- avaliacoes_melhor_execucao_*.png: esforço de busca independente do tempo de máquina.",
            "- criterio_parada_melhor_execucao.png: comportamento dos mecanismos de interrupção.",
            "- curvas_convergencia: use apenas instâncias representativas no corpo do TCC; deixe o restante em apêndice.",
            "- analise_estatistica/ranks_medios_por_conjunto_com_pli.png: síntese estatística incluindo o PLI como referência.",
            "",
            "Sugestão de organização da seção de resultados em LaTeX:",
            "- \\subsection{Caracterização das Instâncias e Resultados do PLI}: use resumo_status_pli.csv e descreva quantas instâncias tiveram otimalidade certificada.",
            "- \\subsection{Qualidade das Soluções das Meta-heurísticas}: use os gráficos de gap relativo e a análise básica por método.",
            "- \\subsection{Robustez das Execuções}: use médias, medianas, boxplots e valores das 10 rodadas.",
            "- \\subsection{Custo Computacional}: use tempos, número de avaliações e critérios de parada.",
            "- \\subsection{Curvas de Convergência}: escolha poucas instâncias representativas e deixe o restante em apêndice.",
            "- \\subsection{Análise Estatística}: apresente Friedman, Wilcoxon, ranks médios e a interpretação dos p-valores.",
            "- \\subsection{Discussão Geral}: sintetize em quais bases cada método se destacou e explique os casos em que heurísticas superaram o PLI não ótimo.",
            "",
            "Sugestão de uso no texto:",
            "- Use os gráficos de gap relativo para discutir qualidade de solução.",
            "- Use os boxplots para discutir estabilidade dos métodos estocásticos.",
            "- Use tempo e avaliações para discutir custo computacional.",
            "- Use critérios de parada para explicar se os métodos encerraram por estagnação, limite de tempo ou limite de iterações.",
            "- Use poucas curvas de convergência no corpo principal, escolhendo instâncias representativas.",
        ]
    )

    report_path = output_dir / "relatorio_resultados.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera CSVs definitivos com bounds, melhores resultados por algoritmo, "
            "media, mediana, gaps em relacao ao PLI e verificacao de bounds."
        )
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="results/csvs_definitivos",
        help="Pasta onde os CSVs definitivos serao gravados.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        type=parse_dataset,
        help="Dataset no formato DATASET:CSV:INSTANCES_DIR[:OUTPUT_NAME]. Pode repetir.",
    )
    parser.add_argument(
        "--algorithm",
        action="append",
        type=parse_algorithm,
        help="Algoritmo no formato COLUNA:DIRETORIO_JSONS. Pode repetir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = project_path(args.output_dir)
    datasets = args.dataset or default_datasets()
    algorithms = args.algorithm or default_algorithms()

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        algorithm_tables: dict[str, pd.DataFrame] = {}
        convergence_tables: dict[str, pd.DataFrame] = {}
        for algorithm in algorithms:
            result_table, convergence_table = load_algorithm_results(algorithm)
            algorithm_tables[algorithm.column_prefix] = result_table
            convergence_tables[algorithm.column_prefix] = convergence_table

        definitive_frames: list[pd.DataFrame] = []
        violation_frames: list[pd.DataFrame] = []

        for dataset in datasets:
            enriched, violations = enrich_dataset(dataset, algorithm_tables, algorithms)
            output_path = output_dir / dataset.output_name
            enriched.to_csv(output_path, index=False)
            definitive_frames.append(enriched)
            if not violations.empty:
                violations.insert(0, "dataset", dataset.name)
                violation_frames.append(violations)
            print(f"CSV definitivo salvo: {output_path.relative_to(PROJECT_ROOT)}")

        combined = pd.concat(definitive_frames, ignore_index=True)
        combined_path = output_dir / "resultados_definitivos.csv"
        combined.to_csv(combined_path, index=False)
        print(f"CSV combinado salvo: {combined_path.relative_to(PROJECT_ROOT)}")

        clean_obsolete_convergence_csvs(output_dir, algorithms)
        plot_count = plot_best_convergence_curves(
            convergence_tables,
            combined,
            algorithms,
            output_dir,
        )
        print(
            "Plots de convergencia salvos em: "
            f"{(output_dir / 'curvas_convergencia').relative_to(PROJECT_ROOT)} "
            f"({plot_count} arquivos)"
        )
        summary_plot_count = plot_summary_charts(combined, algorithms, output_dir)
        print(
            "Graficos de resumo salvos em: "
            f"{(output_dir / 'graficos_resumo').relative_to(PROJECT_ROOT)} "
            f"({summary_plot_count} arquivos)"
        )
        stats_plot_count = run_statistical_analysis(combined, output_dir)
        print(
            "Analise estatistica salva em: "
            f"{(output_dir / 'analise_estatistica').relative_to(PROJECT_ROOT)} "
            f"({stats_plot_count} graficos)"
        )

        if violation_frames:
            violations = pd.concat(violation_frames, ignore_index=True)
        else:
            violations = pd.DataFrame(
                columns=[
                    "dataset",
                    "Grafo",
                    "algoritmo",
                    "rodada",
                    "valor",
                    "LB",
                    "UB",
                    "violacao",
                ]
            )
        violations_path = output_dir / "violacoes_bounds.csv"
        violations.to_csv(violations_path, index=False)
        print(
            f"Verificacao de bounds salva: {violations_path.relative_to(PROJECT_ROOT)}"
        )
        general_report_path = write_general_results_report(
            combined, violations, output_dir
        )
        print(f"Resumo geral salvo em: {general_report_path.relative_to(PROJECT_ROOT)}")

        if violations.empty:
            print("Todos os resultados verificados estao dentro dos bounds.")
        else:
            print(f"Resultados fora dos bounds: {len(violations)}")

        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
