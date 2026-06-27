#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp") / "matplotlib"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "graficos"
DEFAULT_DEFINITIVE_CSVS = [
    PROJECT_ROOT / "results" / "csvs_definitivos" / "cubic_results_definitivo.csv",
    PROJECT_ROOT / "results" / "csvs_definitivos" / "dimacs_resultados_definitivo.csv",
    PROJECT_ROOT
    / "results"
    / "csvs_definitivos"
    / "harwell_boieng_results_definitivo.csv",
]
DEFAULT_STATS_DIR = (
    PROJECT_ROOT / "results" / "csvs_definitivos" / "analise_estatistica"
)

EPS = 1e-9

METHOD_PRIORITY = {
    "PLI": 0,
    "ACO_TS": 1,
    "ACO": 1,
    "HHO_RVNS": 2,
    "HHO": 2,
    "BRKGA": 3,
    "BRKGA_MP_IPR": 3,
}

METHOD_LABELS = {
    "PLI": "PLIB",
    "ACO_TS": "AT",
    "ACO": "AT",
    "HHO_RVNS": "HR",
    "HHO": "HR",
    "BRKGA": "BRKGA",
    "BRKGA_MP_IPR": "BRKGA",
}

METHOD_COLORS = {
    "PLI": "#4A4A4A",
    "ACO_TS": "#1F4E79",
    "ACO": "#1F4E79",
    "HHO_RVNS": "#A23E48",
    "HHO": "#A23E48",
    "BRKGA": "#3E7B40",
    "BRKGA_MP_IPR": "#3E7B40",
}

METHOD_MARKERS = {
    "PLI": "o",
    "ACO_TS": "s",
    "ACO": "s",
    "HHO_RVNS": "^",
    "HHO": "^",
    "BRKGA": "D",
    "BRKGA_MP_IPR": "D",
}

STOP_REASON_LABELS = {
    "time_limit": "Limite de tempo",
    "stagnation": "Estagnação",
    "max_iterations": "Limite de iterações",
    "max_iters": "Limite de iterações",
    "max_generations": "Limite de gerações",
    "indefinido": "Indefinido",
}


def project_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "grafico"


def natural_sort_key(value: Any) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", str(value))
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def method_label(method: str) -> str:
    return METHOD_LABELS.get(method, method.replace("_", "-"))


def method_color(method: str) -> str:
    return METHOD_COLORS.get(method, "#666666")


def method_marker(method: str) -> str:
    return METHOD_MARKERS.get(method, "o")


def numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def pearson_r(x: pd.Series, y: pd.Series) -> float | None:
    paired = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(paired) < 2:
        return None
    if paired["x"].nunique() < 2 or paired["y"].nunique() < 2:
        return None
    value = paired["x"].corr(paired["y"], method="pearson")
    if pd.isna(value) or not math.isfinite(float(value)):
        return None
    return float(value)


def format_r(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def linear_fit(x: pd.Series, y: pd.Series) -> tuple[float, float] | None:
    paired = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(paired) < 2 or paired["x"].nunique() < 2:
        return None
    x_mean = float(paired["x"].mean())
    y_mean = float(paired["y"].mean())
    denominator = float(((paired["x"] - x_mean) ** 2).sum())
    if math.isclose(denominator, 0.0, abs_tol=EPS):
        return None
    slope = float(((paired["x"] - x_mean) * (paired["y"] - y_mean)).sum() / denominator)
    intercept = y_mean - slope * x_mean
    if not math.isfinite(slope) or not math.isfinite(intercept):
        return None
    return slope, intercept


def parse_round_values(value: Any) -> list[float]:
    if pd.isna(value):
        return []
    values: list[float] = []
    for item in str(value).split(";"):
        item = item.strip()
        if not item:
            continue
        try:
            number = float(item)
        except ValueError:
            continue
        if math.isfinite(number):
            values.append(number)
    return values


def graph_stem(value: Any) -> str:
    name = Path(str(value)).name
    return name[:-4] if name.lower().endswith(".col") else name


def load_json(path_value: Any) -> dict[str, Any] | None:
    if pd.isna(path_value):
        return None
    path = project_path(str(path_value))
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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


def select_attempt(
    data: dict[str, Any], best_round: Any, best_value: Any
) -> dict[str, Any] | None:
    attempts = data.get("attempts")
    if not isinstance(attempts, list):
        return None

    round_number = pd.to_numeric(pd.Series([best_round]), errors="coerce").iloc[0]
    if pd.notna(round_number):
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            if attempt.get("attempt") == int(round_number):
                return attempt

    target_value = pd.to_numeric(pd.Series([best_value]), errors="coerce").iloc[0]
    if pd.notna(target_value):
        best_candidates: list[dict[str, Any]] = []
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            value = attempt_value(attempt)
            if value is not None and math.isclose(
                value, float(target_value), abs_tol=EPS
            ):
                best_candidates.append(attempt)
        if best_candidates:
            return next(
                (
                    attempt
                    for attempt in best_candidates
                    if isinstance(attempt.get("convergence"), list)
                    and attempt.get("convergence")
                ),
                best_candidates[0],
            )

    return next((attempt for attempt in attempts if isinstance(attempt, dict)), None)


def detect_methods(columns: list[str]) -> list[str]:
    column_set = set(columns)
    methods: list[str] = []
    for column in columns:
        if column in {"dataset", "Grafo", "Objetivo", "PLI"}:
            continue
        if column.endswith("_gap_relativo"):
            method = column[: -len("_gap_relativo")]
            if method in column_set and method not in methods:
                methods.append(method)
    return sorted(
        methods,
        key=lambda method: (
            METHOD_PRIORITY.get(method, len(METHOD_PRIORITY)),
            methods.index(method),
        ),
    )


def load_definitive_csvs(paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.is_file():
            continue
        frames.append(pd.read_csv(path))
    if not frames:
        raise FileNotFoundError("Nenhum CSV definitivo encontrado.")
    combined = pd.concat(frames, ignore_index=True)
    if "dataset" not in combined.columns:
        combined["dataset"] = "TODOS"
    return combined


def sort_instances(df: pd.DataFrame) -> pd.DataFrame:
    helper = df.copy()
    helper["_graph_sort_key"] = helper["Grafo"].map(natural_sort_key)
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
        .drop(columns=["_graph_sort_key"])
        .reset_index(drop=True)
    )


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 7,
            "legend.title_fontsize": 7,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.edgecolor": "#2B2B2B",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def finish_plot(fig: plt.Figure, ax: plt.Axes, path: Path) -> None:
    ax.grid(True, axis="y", color="#D9D9D9", linewidth=0.7)
    ax.grid(True, axis="x", color="#EFEFEF", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def place_legend(ax: plt.Axes, columns: int = 2) -> None:
    ax.legend(
        frameon=True,
        loc="best",
        ncol=columns,
        handlelength=1.6,
        columnspacing=0.75,
        handletextpad=0.45,
        borderpad=0.28,
        labelspacing=0.25,
        framealpha=0.9,
        facecolor="white",
        edgecolor="#D9D9D9",
    )


def plot_gap_vs_vertices(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
    gap_type: str,
) -> int:
    suffix = "gap_prova" if gap_type == "absoluto" else "gap_relativo"
    ylabel = "Gap absoluto"
    title_base = "Gap absoluto em função de $n$"
    output_prefix = "gap_absoluto_vertices"
    if gap_type == "relativo":
        ylabel = "Gap relativo (%)"
        title_base = "Gap relativo em função de $n$"
        output_prefix = "gap_relativo_vertices"

    count = 0
    for dataset, subset in combined.groupby("dataset", sort=True):
        subset = sort_instances(subset)
        if "|V|" not in subset.columns:
            continue
        x = numeric_series(subset, "|V|")
        fig, ax = plt.subplots(figsize=(8.2, 4.8))

        ax.axhline(0.0, color="#333333", linewidth=0.8, linestyle=(0, (4, 3)))
        ax.plot(
            x,
            [0.0] * len(subset),
            marker=method_marker("PLI"),
            markersize=4.0,
            linewidth=1.2,
            color=method_color("PLI"),
            label=method_label("PLI"),
        )

        for method in methods:
            column = f"{method}_{suffix}"
            if column not in subset.columns:
                continue
            y = numeric_series(subset, column)
            r = pearson_r(x, y)
            ax.plot(
                x,
                y,
                marker=method_marker(method),
                markersize=4.2,
                linewidth=1.5,
                color=method_color(method),
                label=f"{method_label(method)} ($r={format_r(r)}$)",
            )

        ax.set_xlabel("Número de vértices ($n$)")
        ax.set_ylabel(ylabel)
        place_legend(ax, columns=3)
        finish_plot(
            fig, ax, output_dir / f"{output_prefix}_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_relative_gap_by_instance(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
) -> int:
    count = 0
    for dataset, subset in combined.groupby("dataset", sort=True):
        subset = sort_instances(subset)
        x = range(len(subset))
        plotted_methods = [
            method for method in methods if f"{method}_gap_relativo" in subset.columns
        ]
        if not plotted_methods:
            continue
        width = min(0.8 / len(plotted_methods), 0.38)
        fig_width = max(8.0, min(18.0, len(subset) * 0.28))
        fig, ax = plt.subplots(figsize=(fig_width, 4.8))

        for index, method in enumerate(plotted_methods):
            offset = (index - (len(plotted_methods) - 1) / 2) * width
            ax.bar(
                [position + offset for position in x],
                numeric_series(subset, f"{method}_gap_relativo"),
                width=width,
                color=method_color(method),
                label=method_label(method),
            )

        ax.axhline(0.0, color="#333333", linewidth=0.8)
        ax.set_xlabel("Instância")
        ax.set_ylabel(r"$g$ (%)")
        ax.set_xticks(list(x))
        ax.set_xticklabels(subset["Grafo"], rotation=90)
        place_legend(ax, columns=2)
        finish_plot(
            fig, ax, output_dir / f"gap_relativo_instancia_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_round_gap_boxplots(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
) -> int:
    count = 0
    for dataset, subset in combined.groupby("dataset", sort=True):
        box_data: list[list[float]] = []
        labels: list[str] = []
        colors: list[str] = []
        for method in methods:
            values_column = f"{method}_valores_rodadas"
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
                labels.append(method_label(method))
                colors.append(method_color(method))

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
            patch.set_facecolor(color)
            patch.set_alpha(0.72)
        for median in boxplot["medians"]:
            median.set_color("#111111")
            median.set_linewidth(1.2)
        for mean in boxplot["means"]:
            mean.set_color("#FFFFFF")
            mean.set_linewidth(1.0)
        ax.set_xlabel("Método")
        ax.set_ylabel(r"$g$ por execução (%)")
        finish_plot(
            fig,
            ax,
            output_dir / f"boxplot_gap_relativo_execucoes_{safe_filename(dataset)}.png",
        )
        count += 1
    return count


def plot_best_run_metric_by_instance(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
    metric_suffix: str,
    title: str,
    ylabel: str,
    output_prefix: str,
    use_log_scale: bool,
) -> int:
    count = 0
    for dataset, subset in combined.groupby("dataset", sort=True):
        subset = sort_instances(subset)
        x = range(len(subset))
        plotted_methods = [
            method
            for method in methods
            if f"{method}_{metric_suffix}" in subset.columns
        ]
        if not plotted_methods:
            continue
        width = min(0.8 / len(plotted_methods), 0.38)
        fig_width = max(8.0, min(18.0, len(subset) * 0.28))
        fig, ax = plt.subplots(figsize=(fig_width, 4.8))

        for index, method in enumerate(plotted_methods):
            offset = (index - (len(plotted_methods) - 1) / 2) * width
            ax.bar(
                [position + offset for position in x],
                numeric_series(subset, f"{method}_{metric_suffix}"),
                width=width,
                color=method_color(method),
                label=method_label(method),
            )

        if use_log_scale:
            ax.set_yscale("log")
        ax.set_xlabel("Instância")
        ax.set_ylabel(ylabel)
        ax.set_xticks(list(x))
        ax.set_xticklabels(subset["Grafo"], rotation=90)
        place_legend(ax, columns=2)
        finish_plot(
            fig, ax, output_dir / f"{output_prefix}_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_stop_reason_counts(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
) -> int:
    rows: list[dict[str, Any]] = []
    for method in methods:
        column = f"{method}_melhor_criterio_parada"
        if column not in combined.columns:
            continue
        reasons = combined[column].fillna("indefinido").map(
            lambda reason: STOP_REASON_LABELS.get(str(reason), str(reason))
        )
        counts = reasons.value_counts().sort_index()
        for reason, count in counts.items():
            rows.append(
                {
                    "Metodo": method_label(method),
                    "Criterio": str(reason),
                    "Quantidade": int(count),
                }
            )
    if not rows:
        return 0

    table = pd.DataFrame(rows)
    pivot = table.pivot(index="Criterio", columns="Metodo", values="Quantidade").fillna(
        0
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    x = range(len(pivot.index))
    methods_labels = list(pivot.columns)
    width = min(0.8 / len(methods_labels), 0.38)
    for index, label in enumerate(methods_labels):
        offset = (index - (len(methods_labels) - 1) / 2) * width
        method_key = next(
            (method for method in methods if method_label(method) == label), label
        )
        ax.bar(
            [position + offset for position in x],
            pivot[label],
            width=width,
            color=method_color(method_key),
            label=label,
        )
    ax.set_xlabel("Critério de parada")
    ax.set_ylabel("Quantidade de instâncias")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index, rotation=0)
    place_legend(ax, columns=2)
    finish_plot(fig, ax, output_dir / "criterio_parada_melhor_execucao.png")
    return 1


def plot_metaheuristic_gap_scatter(
    combined: pd.DataFrame,
    output_dir: Path,
) -> int:
    methods = [
        method
        for method in ("ACO_TS", "HHO_RVNS", "BRKGA")
        if f"{method}_gap_relativo" in combined.columns
    ]

    def configure_scatter_axes(
        ax: plt.Axes,
        x: pd.Series,
        y: pd.Series,
        method_a: str,
        method_b: str,
    ) -> None:
        finite = pd.concat([x, y]).dropna()
        if not finite.empty:
            low = float(finite.min())
            high = float(finite.max())
            margin = max((high - low) * 0.05, 1.0)
            ax.plot(
                [low - margin, high + margin],
                [low - margin, high + margin],
                color="#333333",
                linewidth=0.9,
                linestyle=(0, (4, 3)),
                label=(
                    f"$g_{{{method_label(method_a)}}}="
                    f"g_{{{method_label(method_b)}}}$"
                ),
            )
            fit = linear_fit(x, y)
            if fit is not None:
                slope, intercept = fit
                x_start = low - margin
                x_end = high + margin
                ax.plot(
                    [x_start, x_end],
                    [slope * x_start + intercept, slope * x_end + intercept],
                    color="#A23E48",
                    linewidth=1.1,
                    linestyle="-",
                    label="Ajuste linear",
                )
            ax.set_xlim(low - margin, high + margin)
            ax.set_ylim(low - margin, high + margin)
        ax.axhline(0.0, color="#BBBBBB", linewidth=0.7)
        ax.axvline(0.0, color="#BBBBBB", linewidth=0.7)
        ax.set_xlabel(f"$g_{{{method_label(method_a)}}}$ (%)")
        ax.set_ylabel(f"$g_{{{method_label(method_b)}}}$ (%)")

    count = 0
    for method_a, method_b in combinations(methods, 2):
        x_all = numeric_series(combined, f"{method_a}_gap_relativo")
        y_all = numeric_series(combined, f"{method_b}_gap_relativo")
        base_name = (
            "dispersao_gap_relativo_metaheuristicas"
            if (method_a, method_b) == ("ACO_TS", "HHO_RVNS")
            else f"dispersao_gap_relativo_{method_a.lower()}_{method_b.lower()}"
        )
        fig, ax = plt.subplots(figsize=(6.8, 5.8))
        for dataset, subset in combined.groupby("dataset", sort=True):
            ax.scatter(
                numeric_series(subset, f"{method_a}_gap_relativo"),
                numeric_series(subset, f"{method_b}_gap_relativo"),
                s=28,
                alpha=0.78,
                label=dataset,
            )
        configure_scatter_axes(ax, x_all, y_all, method_a, method_b)
        r_all = pearson_r(x_all, y_all)
        ax.text(
            0.02,
            0.98,
            f"$r={format_r(r_all)}$",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "#D9D9D9", "alpha": 0.88},
        )
        place_legend(ax, columns=1)
        finish_plot(fig, ax, output_dir / f"{base_name}.png")
        count += 1

        for dataset, subset in combined.groupby("dataset", sort=True):
            x = numeric_series(subset, f"{method_a}_gap_relativo")
            y = numeric_series(subset, f"{method_b}_gap_relativo")
            if pd.DataFrame({"x": x, "y": y}).dropna().empty:
                continue
            r = pearson_r(x, y)
            fig, ax = plt.subplots(figsize=(6.8, 5.8))
            ax.scatter(
                x,
                y,
                s=30,
                alpha=0.8,
                color="#5E548E",
                label=f"{dataset} ($r={format_r(r)}$)",
            )
            configure_scatter_axes(ax, x, y, method_a, method_b)
            place_legend(ax, columns=1)
            finish_plot(
                fig,
                ax,
                output_dir / f"{base_name}_{safe_filename(dataset)}.png",
            )
            count += 1
    return count


def plot_best_convergence_curves(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
) -> int:
    plots_dir = output_dir / "curvas_convergencia"
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_count = 0

    for _, row in sort_instances(combined).iterrows():
        dataset = str(row.get("dataset", "TODOS"))
        graph_name = graph_stem(row.get("Grafo", "instancia"))
        graph_dir = plots_dir / safe_filename(dataset)
        graph_dir.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        plotted = False

        for method in methods:
            json_column = f"{method}_json"
            if json_column not in row.index:
                continue
            data = load_json(row.get(json_column))
            if data is None:
                continue
            attempt = select_attempt(
                data,
                row.get(f"{method}_melhor_rodada"),
                row.get(method),
            )
            if not isinstance(attempt, dict):
                continue
            convergence = attempt.get("convergence")
            if not isinstance(convergence, list) or not convergence:
                continue

            curve = pd.DataFrame(
                point for point in convergence if isinstance(point, dict)
            )
            if curve.empty:
                continue
            if "iteration" not in curve.columns and "generation" in curve.columns:
                curve = curve.rename(columns={"generation": "iteration"})
            if "iteration" not in curve.columns or "best_fitness" not in curve.columns:
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

            label = method_label(method)
            method_value = pd.to_numeric(
                pd.Series([row.get(method)]), errors="coerce"
            ).iloc[0]
            if pd.notna(method_value):
                label = f"{label} ({float(method_value):g})"

            ax.plot(
                curve["iteration"],
                curve["best_fitness"],
                marker="o",
                markersize=3.2,
                linewidth=1.7,
                drawstyle="steps-post",
                color=method_color(method),
                markeredgewidth=0.0,
                label=label,
            )

            parameters = data.get("parameters")
            if isinstance(parameters, dict):
                local_search_start = pd.to_numeric(
                    pd.Series([parameters.get("local_search_start")]),
                    errors="coerce",
                ).iloc[0]
                if pd.notna(local_search_start):
                    ax.axvline(
                        float(local_search_start),
                        color=method_color(method),
                        linewidth=1.0,
                        linestyle=(0, (2, 3)),
                        alpha=0.75,
                        label=f"Busca local ({method_label(method)})",
                    )

            plotted = True

        if not plotted:
            plt.close(fig)
            continue

        objective = pd.to_numeric(
            pd.Series([row.get("Objetivo")]), errors="coerce"
        ).iloc[0]
        if pd.notna(objective):
            ax.axhline(
                float(objective),
                color=method_color("PLI"),
                linewidth=1.1,
                linestyle=(0, (4, 3)),
                label=rf"$z_{{PLI}}$ ({float(objective):g})",
            )

        ax.set_xlabel("Iteração/geração")
        ax.set_ylabel(r"Melhor $z$ encontrado")
        place_legend(ax, columns=2)
        finish_plot(fig, ax, graph_dir / f"{safe_filename(graph_name)}.png")
        plot_count += 1

    return plot_count


def plot_gap_vs_cost_metric(
    combined: pd.DataFrame,
    methods: list[str],
    output_dir: Path,
    metric_suffix: str,
    title: str,
    xlabel: str,
    output_prefix: str,
) -> int:
    count = 0
    for dataset, subset in combined.groupby("dataset", sort=True):
        plotted_methods = [
            method
            for method in methods
            if f"{method}_{metric_suffix}" in subset.columns
            and f"{method}_gap_relativo" in subset.columns
        ]
        if not plotted_methods:
            continue

        fig, ax = plt.subplots(figsize=(7.4, 4.8))
        ax.axhline(0.0, color="#333333", linewidth=0.8, linestyle=(0, (4, 3)))
        for method in plotted_methods:
            x = numeric_series(subset, f"{method}_{metric_suffix}")
            y = numeric_series(subset, f"{method}_gap_relativo")
            r = pearson_r(x, y)
            ax.scatter(
                x,
                y,
                s=28,
                alpha=0.78,
                marker=method_marker(method),
                color=method_color(method),
                label=f"{method_label(method)} ($r={format_r(r)}$)",
            )

        ax.set_xscale("log")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(r"$g$ (%)")
        place_legend(ax, columns=1)
        finish_plot(
            fig, ax, output_dir / f"{output_prefix}_{safe_filename(dataset)}.png"
        )
        count += 1
    return count


def plot_paired_gap_difference_by_vertices(
    combined: pd.DataFrame,
    output_dir: Path,
) -> int:
    methods = [
        method
        for method in ("ACO_TS", "HHO_RVNS", "BRKGA")
        if f"{method}_gap_relativo" in combined.columns
    ]
    count = 0
    for method_a, method_b in combinations(methods, 2):
        for dataset, subset in combined.groupby("dataset", sort=True):
            subset = sort_instances(subset)
            x = numeric_series(subset, "|V|")
            y = numeric_series(
                subset, f"{method_b}_gap_relativo"
            ) - numeric_series(subset, f"{method_a}_gap_relativo")
            r = pearson_r(x, y)

            fig, ax = plt.subplots(figsize=(8.2, 4.8))
            ax.axhline(0.0, color="#333333", linewidth=0.8, linestyle=(0, (4, 3)))
            ax.plot(
                x,
                y,
                marker="o",
                markersize=4.2,
                linewidth=1.5,
                color="#5E548E",
                label=(
                    f"$g_{{{method_label(method_b)}}} - "
                    f"g_{{{method_label(method_a)}}}$ ($r={format_r(r)}$)"
                ),
            )
            ax.set_xlabel("Número de vértices ($n$)")
            ax.set_ylabel(
                f"$g_{{{method_label(method_b)}}} - "
                f"g_{{{method_label(method_a)}}}$ (p.p.)"
            )
            ax.text(
                0.02,
                0.98,
                f"positivo favorece {method_label(method_a)}\n"
                f"negativo favorece {method_label(method_b)}",
                transform=ax.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox={"facecolor": "white", "edgecolor": "#D9D9D9", "alpha": 0.88},
            )
            place_legend(ax, columns=1)
            suffix = (
                ""
                if (method_a, method_b) == ("ACO_TS", "HHO_RVNS")
                else f"_{method_a.lower()}_{method_b.lower()}"
            )
            finish_plot(
                fig,
                ax,
                output_dir
                / (
                    "diferenca_gap_relativo_vertices"
                    f"{suffix}_{safe_filename(dataset)}.png"
                ),
            )
            count += 1
    return count


def plot_pli_proof_gap_vs_vertices(combined: pd.DataFrame, output_dir: Path) -> int:
    required = {"dataset", "|V|", "Objetivo", "LB"}
    if not required.issubset(combined.columns):
        return 0

    plot_specs = [
        {
            "dataset": "DIMACS",
            "metric": "delta",
            "ylabel": r"$\Delta_{\mathrm{prova}}$",
            "output": "pli_delta_prova_vertices_DIMACS.png",
            "x_log": False,
        },
        {
            "dataset": "DIMACS",
            "metric": "delta",
            "ylabel": r"$\Delta_{\mathrm{prova}}$",
            "output": "pli_delta_prova_vertices_DIMACS_log.png",
            "x_log": True,
        },
        {
            "dataset": "CUBIC",
            "metric": "gap_percent",
            "ylabel": r"$\mathrm{gap}_{\mathrm{prova}}$ (%)",
            "output": "pli_gap_prova_percent_vertices_CUBIC.png",
            "x_log": False,
        },
        {
            "dataset": "CUBIC",
            "metric": "delta",
            "ylabel": r"$\Delta_{\mathrm{prova}}$",
            "output": "pli_delta_prova_vertices_CUBIC.png",
            "x_log": False,
        },
        {
            "dataset": "HB",
            "metric": "delta",
            "ylabel": r"$\Delta_{\mathrm{prova}}$",
            "output": "pli_delta_prova_vertices_HB.png",
            "x_log": False,
        },
        {
            "dataset": "HB",
            "metric": "gap_percent",
            "ylabel": r"$\mathrm{gap}_{\mathrm{prova}}$ (%)",
            "output": "pli_gap_prova_percent_vertices_HB.png",
            "x_log": False,
        },
    ]

    count = 0
    for spec in plot_specs:
        subset = sort_instances(combined[combined["dataset"].eq(spec["dataset"])])
        if subset.empty:
            continue

        x = numeric_series(subset, "|V|")
        objective = numeric_series(subset, "Objetivo")
        lb = numeric_series(subset, "LB")
        delta = objective - lb
        if spec["metric"] == "gap_percent":
            y = (delta / objective) * 100.0
            y = y.mask(objective.eq(0.0))
        else:
            y = delta

        paired = pd.DataFrame({"x": x, "y": y}).dropna()
        if paired.empty:
            continue

        r = pearson_r(x, y)
        fig, ax = plt.subplots(figsize=(7.4, 4.8))
        ax.scatter(
            x,
            y,
            s=30,
            alpha=0.8,
            color="#5E548E",
            label=f"{spec['dataset']} ($r={format_r(r)}$)",
        )
        fit = linear_fit(x, y)
        if fit is not None:
            slope, intercept = fit
            x_min = float(paired["x"].min())
            x_max = float(paired["x"].max())
            ax.plot(
                [x_min, x_max],
                [slope * x_min + intercept, slope * x_max + intercept],
                color="#A23E48",
                linewidth=1.1,
                label="Ajuste linear",
            )

        ax.axhline(0.0, color="#333333", linewidth=0.8, linestyle=(0, (4, 3)))
        if spec["x_log"]:
            ax.set_xscale("log")
        ax.set_xlabel(r"$n(G)$")
        ax.set_ylabel(str(spec["ylabel"]))
        place_legend(ax, columns=1)
        finish_plot(fig, ax, output_dir / str(spec["output"]))
        count += 1

    return count


def plot_mean_ranks(stats_dir: Path, output_dir: Path) -> int:
    ranks_path = stats_dir / "ranks_medios_com_pli.csv"
    if not ranks_path.is_file():
        return 0
    ranks = pd.read_csv(ranks_path)
    if ranks.empty:
        return 0
    subset = ranks[ranks["dataset"].eq("TODOS")].copy()
    if subset.empty:
        return 0
    subset["rotulo_plot"] = subset["metodo"].map(method_label)
    subset = subset.sort_values("rank_medio")
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.bar(
        subset["rotulo_plot"],
        numeric_series(subset, "rank_medio"),
        color=[method_color(method) for method in subset["metodo"]],
    )
    ax.set_xlabel("Método")
    ax.set_ylabel("Rank médio")
    finish_plot(fig, ax, output_dir / "ranks_medios_com_pli.png")

    by_dataset = ranks.copy()
    by_dataset["rotulo_plot"] = by_dataset["metodo"].map(method_label)
    datasets = list(by_dataset["dataset"].drop_duplicates())
    methods = list(by_dataset["rotulo_plot"].drop_duplicates())
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = range(len(datasets))
    width = min(0.8 / len(methods), 0.25)
    for index, label in enumerate(methods):
        values = []
        for dataset in datasets:
            match = by_dataset[
                by_dataset["dataset"].eq(dataset) & by_dataset["rotulo_plot"].eq(label)
            ]
            values.append(
                float(match["rank_medio"].iloc[0]) if not match.empty else math.nan
            )
        method_key = next(
            (method for method in METHOD_LABELS if METHOD_LABELS[method] == label),
            label,
        )
        offset = (index - (len(methods) - 1) / 2) * width
        ax.bar(
            [position + offset for position in x],
            values,
            width=width,
            color=method_color(method_key),
            label=label,
        )
    ax.set_xlabel("Conjunto")
    ax.set_ylabel("Rank médio")
    ax.set_xticks(list(x))
    ax.set_xticklabels(datasets)
    place_legend(ax, columns=3)
    finish_plot(fig, ax, output_dir / "ranks_medios_por_conjunto_com_pli.png")
    return 2


def generate_plots(combined: pd.DataFrame, output_dir: Path, stats_dir: Path) -> int:
    methods = detect_methods(list(combined.columns))
    configure_plot_style()
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    count += plot_gap_vs_vertices(combined, methods, output_dir, gap_type="absoluto")
    count += plot_gap_vs_vertices(combined, methods, output_dir, gap_type="relativo")
    count += plot_pli_proof_gap_vs_vertices(combined, output_dir)
    count += plot_relative_gap_by_instance(combined, methods, output_dir)
    count += plot_round_gap_boxplots(combined, methods, output_dir)
    count += plot_best_run_metric_by_instance(
        combined,
        methods,
        output_dir,
        "melhor_tempo_s",
        "Tempo da Melhor Execução",
        "Tempo (s)",
        "tempo_melhor_execucao",
        use_log_scale=True,
    )
    count += plot_best_run_metric_by_instance(
        combined,
        methods,
        output_dir,
        "melhor_avaliacoes",
        "Avaliações da Melhor Execução",
        "Número de avaliações",
        "avaliacoes_melhor_execucao",
        use_log_scale=True,
    )
    count += plot_stop_reason_counts(combined, methods, output_dir)
    count += plot_metaheuristic_gap_scatter(combined, output_dir)
    count += plot_best_convergence_curves(combined, methods, output_dir)
    count += plot_gap_vs_cost_metric(
        combined,
        methods,
        output_dir,
        "melhor_tempo_s",
        r"$g$ em função de $t^*$",
        "Tempo da melhor execução (s, escala log)",
        "gap_relativo_tempo",
    )
    count += plot_gap_vs_cost_metric(
        combined,
        methods,
        output_dir,
        "melhor_avaliacoes",
        r"$g$ em função de $N^*_{eval}$",
        "Avaliações da melhor execução (escala log)",
        "gap_relativo_avaliacoes",
    )
    count += plot_paired_gap_difference_by_vertices(combined, output_dir)
    count += plot_mean_ranks(stats_dir, output_dir)
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera todos os graficos de resultados a partir dos CSVs definitivos."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Pasta de saida dos graficos. Padrao: results/graficos.",
    )
    parser.add_argument(
        "--csv",
        action="append",
        dest="csvs",
        help="CSV definitivo de entrada. Pode ser informado varias vezes.",
    )
    parser.add_argument(
        "--stats-dir",
        default=str(DEFAULT_STATS_DIR),
        help="Pasta com CSVs estatisticos, usada para os graficos de ranks.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Nao limpa a pasta de saida antes de gerar os graficos.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = project_path(args.output_dir)
    stats_dir = project_path(args.stats_dir)
    csv_paths = (
        [project_path(path) for path in args.csvs]
        if args.csvs
        else DEFAULT_DEFINITIVE_CSVS
    )

    if output_dir.exists() and not args.no_clean:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combined = load_definitive_csvs(csv_paths)
    count = generate_plots(combined, output_dir, stats_dir)
    print(f"Graficos gerados em: {output_dir}")
    print(f"Total de graficos: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
