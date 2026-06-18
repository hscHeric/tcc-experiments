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
    "ACO_TS": "ACO-TS",
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
        raise argparse.ArgumentTypeError(
            "Use DATASET:CSV:INSTANCES_DIR[:OUTPUT_NAME]."
        )

    name, csv_path, instances_dir = parts[:3]
    output_name = parts[3] if len(parts) == 4 else f"{Path(csv_path).stem}_definitivo.csv"
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
        raise FileNotFoundError(f"Diretorio de instancias nao encontrado: {instances_dir}")
    return {path.stem: path for path in sorted(instances_dir.rglob("*")) if path.is_file()}


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


def load_algorithm_results(config: AlgorithmConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        best_value = min(values)
        best_candidates: list[dict[str, Any]] = []
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            value = attempt_value(attempt)
            if value is not None and math.isclose(value, best_value, rel_tol=0.0, abs_tol=EPS):
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
        if pd.notna(pli_value) and not (pli_value + EPS >= lb and pli_value <= ub + EPS):
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
        raise ValueError(f"{dataset.csv_path} nao tem colunas obrigatorias: {sorted(missing)}")

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
    values = [float(value) for value in str(row[values_column]).split(";") if value.strip()]
    return all(row["LB"] - EPS <= value <= row["UB"] + EPS for value in values)


def order_columns(df: pd.DataFrame, algorithms: list[AlgorithmConfig]) -> pd.DataFrame:
    original_columns = [
        column
        for column in ["dataset", "Grafo", "|V|", "|E|", "Densidade", "Objetivo", "Tempo (s)", "Status"]
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
            "legend.fontsize": 9,
            "legend.title_fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.edgecolor": "#2B2B2B",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    for graph_name in sorted(graph_dataset):
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
            curve["best_fitness"] = pd.to_numeric(curve["best_fitness"], errors="coerce")
            curve = curve.dropna(subset=["iteration", "best_fitness"]).sort_values(
                "iteration"
            )
            if curve.empty:
                continue

            round_value = curve["melhor_rodada"].dropna()
            best_value = curve["melhor_valor"].dropna()
            label = algorithm_label(algorithm.column_prefix)
            if not round_value.empty and not best_value.empty:
                label = (
                    f"{label} "
                    f"(execucao {int(round_value.iloc[0])}; melhor valor = {best_value.iloc[0]:g})"
                )

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
                label=f"PLI = {float(objective):g}",
            )

        ax.set_title(f"Curva de Convergencia - Instancia {graph_name}", pad=12)
        ax.set_xlabel("Iteracao")
        ax.set_ylabel("Melhor Valor Encontrado")
        ax.grid(True, axis="y", color="#D9D9D9", linewidth=0.7)
        ax.grid(True, axis="x", color="#ECECEC", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(title="Metodo", frameon=False, loc="best")
        fig.tight_layout()
        plot_path = graph_dir / f"{safe_filename(graph_name)}.png"
        fig.savefig(plot_path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        plot_count += 1

    return plot_count


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

        if violation_frames:
            violations = pd.concat(violation_frames, ignore_index=True)
        else:
            violations = pd.DataFrame(
                columns=["dataset", "Grafo", "algoritmo", "rodada", "valor", "LB", "UB", "violacao"]
            )
        violations_path = output_dir / "violacoes_bounds.csv"
        violations.to_csv(violations_path, index=False)
        print(f"Verificacao de bounds salva: {violations_path.relative_to(PROJECT_ROOT)}")

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
