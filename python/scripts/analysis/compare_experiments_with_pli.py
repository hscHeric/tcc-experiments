#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PLI_FILES = [
    "results/pli/CUBIC/cubic_results.csv",
    "results/pli/DIMACS/dimacs_resultados.csv",
    "results/pli/HB/harwell_boieng_results.csv",
]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def graph_stem(value: Any) -> str:
    return Path(str(value)).stem


def load_pli_results(files: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for file_name in files:
        path = project_path(file_name)
        if not path.is_file():
            continue

        df = pd.read_csv(path)
        required = ["Grafo", "|V|", "|E|", "Densidade", "Objetivo", "Tempo (s)", "Status"]
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"{path} nao tem as colunas obrigatorias: {missing}")

        df = df[required].copy()
        df["graph"] = df["Grafo"].map(graph_stem)
        df["pli_source"] = str(path.relative_to(PROJECT_ROOT))
        frames.append(df)

    if not frames:
        return pd.DataFrame(
            columns=[
                "graph",
                "vertices",
                "edges",
                "density",
                "pli_objective",
                "pli_runtime_seconds",
                "pli_status",
                "pli_source",
            ]
        )

    df = pd.concat(frames, ignore_index=True)
    df = df.rename(
        columns={
            "|V|": "vertices",
            "|E|": "edges",
            "Densidade": "density",
            "Objetivo": "pli_objective",
            "Tempo (s)": "pli_runtime_seconds",
            "Status": "pli_status",
        }
    )
    df["pli_objective"] = pd.to_numeric(df["pli_objective"], errors="coerce")
    df["pli_runtime_seconds"] = pd.to_numeric(df["pli_runtime_seconds"], errors="coerce")
    df = df.sort_values("pli_runtime_seconds", ascending=False)
    return df.drop_duplicates("graph", keep="first")


def is_complete_result(data: dict[str, Any]) -> bool:
    attempts = data.get("attempts")
    parameters = data.get("parameters", {})
    expected_attempts = int(parameters.get("attempts", 1))
    return (
        isinstance(attempts, list)
        and len(attempts) == expected_attempts
        and data.get("best_fitness_global") is not None
    )


def load_experiment_result(path: Path, algorithm_key: str) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as result_file:
            data = json.load(result_file)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict) or not is_complete_result(data):
        return None

    attempts = data.get("attempts", [])
    parameters = data.get("parameters", {})
    total_runtime = sum(
        float(attempt.get("total_runtime_seconds", 0.0))
        for attempt in attempts
        if isinstance(attempt, dict)
    )

    return {
        "graph": graph_stem(data.get("graph", path.stem)),
        f"{algorithm_key}_best": float(data["best_fitness_global"]),
        f"{algorithm_key}_attempts": len(attempts),
        f"{algorithm_key}_expected_attempts": int(parameters.get("attempts", 1)),
        f"{algorithm_key}_runtime_seconds": total_runtime,
        f"{algorithm_key}_output": str(path.relative_to(PROJECT_ROOT)),
    }


def load_experiment_dir(directory: str, algorithm_key: str) -> pd.DataFrame:
    path = project_path(directory)
    rows: list[dict[str, Any]] = []
    if path.exists():
        for json_path in sorted(path.glob("*.json")):
            row = load_experiment_result(json_path, algorithm_key)
            if row is not None:
                rows.append(row)
    return pd.DataFrame(rows)


def add_gap_columns(df: pd.DataFrame, algorithm_key: str) -> pd.DataFrame:
    best_column = f"{algorithm_key}_best"
    if best_column not in df.columns:
        df[f"{algorithm_key}_gap"] = pd.NA
        df[f"{algorithm_key}_gap_percent"] = pd.NA
        return df

    df[f"{algorithm_key}_gap"] = df[best_column] - df["pli_objective"]
    df[f"{algorithm_key}_gap_percent"] = (
        df[f"{algorithm_key}_gap"] / df["pli_objective"].abs()
    ) * 100.0
    df.loc[df["pli_objective"] == 0, f"{algorithm_key}_gap_percent"] = pd.NA
    return df


def build_comparison(
    pli_df: pd.DataFrame,
    aco_df: pd.DataFrame,
    hho_df: pd.DataFrame,
    only_both: bool,
) -> pd.DataFrame:
    computed = pd.merge(aco_df, hho_df, on="graph", how="outer")
    if only_both:
        computed = computed[
            computed["aco_ts_best"].notna() & computed["hho_rvns_best"].notna()
        ]

    df = pd.merge(pli_df, computed, on="graph", how="inner")
    if df.empty:
        return df

    df = add_gap_columns(df, "aco_ts")
    df = add_gap_columns(df, "hho_rvns")

    best_columns = [column for column in ["aco_ts_best", "hho_rvns_best"] if column in df]
    df["best_heuristic"] = df[best_columns].min(axis=1, skipna=True)
    df["best_heuristic_gap"] = df["best_heuristic"] - df["pli_objective"]
    df["best_heuristic_gap_percent"] = (
        df["best_heuristic_gap"] / df["pli_objective"].abs()
    ) * 100.0
    df.loc[df["pli_objective"] == 0, "best_heuristic_gap_percent"] = pd.NA

    df["computed_by"] = ""
    df.loc[df["aco_ts_best"].notna(), "computed_by"] += "aco_ts"
    has_both = df["aco_ts_best"].notna() & df["hho_rvns_best"].notna()
    df.loc[has_both, "computed_by"] += "+"
    df.loc[df["hho_rvns_best"].notna(), "computed_by"] += "hho_rvns"

    ordered_columns = [
        "graph",
        "vertices",
        "edges",
        "density",
        "pli_objective",
        "pli_status",
        "pli_runtime_seconds",
        "aco_ts_best",
        "aco_ts_gap",
        "aco_ts_gap_percent",
        "aco_ts_attempts",
        "aco_ts_runtime_seconds",
        "hho_rvns_best",
        "hho_rvns_gap",
        "hho_rvns_gap_percent",
        "hho_rvns_attempts",
        "hho_rvns_runtime_seconds",
        "best_heuristic",
        "best_heuristic_gap",
        "best_heuristic_gap_percent",
        "computed_by",
        "aco_ts_output",
        "hho_rvns_output",
        "pli_source",
    ]
    for column in ordered_columns:
        if column not in df.columns:
            df[column] = pd.NA

    return df[ordered_columns].sort_values(
        ["pli_runtime_seconds", "graph"], ascending=[False, True]
    )


def print_summary(df: pd.DataFrame) -> None:
    print(f"Grafos comparados: {len(df)}")
    if df.empty:
        return

    print(f"Com os dois algoritmos: {(df['computed_by'] == 'aco_ts+hho_rvns').sum()}")
    print(f"Somente ACO+TS: {(df['computed_by'] == 'aco_ts').sum()}")
    print(f"Somente HHO+RVNS: {(df['computed_by'] == 'hho_rvns').sum()}")

    best_counts = {"PLI": 0, "ACO+TS": 0, "HHO+RVNS": 0}
    unique_best_counts = {"PLI": 0, "ACO+TS": 0, "HHO+RVNS": 0}
    for _, row in df.iterrows():
        values = {
            "PLI": row["pli_objective"],
            "ACO+TS": row["aco_ts_best"],
            "HHO+RVNS": row["hho_rvns_best"],
        }
        values = {
            algorithm: value
            for algorithm, value in values.items()
            if not pd.isna(value)
        }
        if not values:
            continue

        best_value = min(values.values())
        winners = [
            algorithm
            for algorithm, value in values.items()
            if value == best_value
        ]
        for winner in winners:
            best_counts[winner] += 1
        if len(winners) == 1:
            unique_best_counts[winners[0]] += 1

    print("\nMelhor valor por grafo (inclui empates):")
    print(f"PLI: {best_counts['PLI']}")
    print(f"ACO+TS: {best_counts['ACO+TS']}")
    print(f"HHO+RVNS: {best_counts['HHO+RVNS']}")

    print("\nVitorias unicas:")
    print(f"PLI: {unique_best_counts['PLI']}")
    print(f"ACO+TS: {unique_best_counts['ACO+TS']}")
    print(f"HHO+RVNS: {unique_best_counts['HHO+RVNS']}")

    print("\nPrimeiros grafos pela dificuldade PLI:")
    for _, row in df.head(10).iterrows():
        aco = "-" if pd.isna(row["aco_ts_best"]) else f"{row['aco_ts_best']:.6g}"
        hho = "-" if pd.isna(row["hho_rvns_best"]) else f"{row['hho_rvns_best']:.6g}"
        print(
            f"- {row['graph']}: PLI={row['pli_objective']:.6g} "
            f"ACO+TS={aco} HHO+RVNS={hho} status={row['pli_status']}"
        )


def print_table(df: pd.DataFrame) -> None:
    if df.empty:
        return

    display_columns = [
        "graph",
        "pli_objective",
        "pli_status",
        "pli_runtime_seconds",
        "aco_ts_best",
        "aco_ts_gap",
        "hho_rvns_best",
        "hho_rvns_gap",
        "best_heuristic",
        "best_heuristic_gap",
        "computed_by",
    ]
    table = df[display_columns].copy()
    float_columns = table.select_dtypes(include="number").columns
    for column in float_columns:
        table[column] = table[column].map(
            lambda value: "" if pd.isna(value) else f"{value:.6g}"
        )
    print("\nTabela:")
    print(table.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compara os resultados ja computados por ACO+TS e HHO+RVNS "
            "com os resultados do PLI."
        )
    )
    parser.add_argument(
        "--aco-dir",
        default="results/experiments/aco_ts",
        help="Diretorio com JSONs do ACO+TS.",
    )
    parser.add_argument(
        "--hho-dir",
        default="results/experiments/hho_rvns",
        help="Diretorio com JSONs do HHO+RVNS.",
    )
    parser.add_argument(
        "--pli-files",
        nargs="+",
        default=DEFAULT_PLI_FILES,
        help="CSVs do PLI usados como referencia.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Opcional: salva a comparacao completa em CSV.",
    )
    parser.add_argument(
        "--only-both",
        action="store_true",
        help="Inclui apenas grafos que ja foram computados pelos dois algoritmos.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pli_df = load_pli_results(args.pli_files)
        aco_df = load_experiment_dir(args.aco_dir, "aco_ts")
        hho_df = load_experiment_dir(args.hho_dir, "hho_rvns")
        comparison = build_comparison(pli_df, aco_df, hho_df, args.only_both)
        print_summary(comparison)
        print_table(comparison)
        if args.output:
            output = project_path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            comparison.to_csv(output, index=False)
            print(f"\nCSV salvo em: {output}")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
