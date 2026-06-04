#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_result(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as result_file:
        data = json.load(result_file)
    if not isinstance(data, dict):
        raise ValueError("O arquivo JSON deve conter um objeto.")
    return data


def convergence_points(attempt: dict[str, Any], x_axis: str) -> tuple[list[float], list[float]]:
    convergence = attempt.get("convergence", [])
    if not isinstance(convergence, list):
        return [], []

    x_values: list[float] = []
    y_values: list[float] = []
    for point in convergence:
        if not isinstance(point, dict):
            continue
        if x_axis not in point or "best_fitness" not in point:
            continue
        x_values.append(float(point[x_axis]))
        y_values.append(float(point["best_fitness"]))

    final_value = attempt.get("final_solution_value")
    final_x = {
        "iteration": attempt.get("iterations"),
        "elapsed_seconds": attempt.get("total_runtime_seconds"),
        "evaluations": attempt.get("evaluations"),
    }.get(x_axis)

    if final_value is not None and final_x is not None:
        if not x_values or float(final_x) != x_values[-1]:
            x_values.append(float(final_x))
            y_values.append(float(final_value))

    return x_values, y_values


def plot_convergence(data: dict[str, Any], json_path: Path, x_axis: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as error:
        if error.name == "matplotlib":
            raise RuntimeError(
                "matplotlib nao esta instalado neste ambiente. "
                "Instale as dependencias com: pip install -r requirements.txt"
            ) from error
        raise

    attempts = data.get("attempts", [])
    if not isinstance(attempts, list) or not attempts:
        raise ValueError("O JSON nao contem tentativas em 'attempts'.")

    labels = {
        "iteration": "Iteracao",
        "elapsed_seconds": "Tempo (s)",
        "evaluations": "Avaliacoes",
    }

    plotted = 0
    plt.figure(figsize=(11, 6))
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        x_values, y_values = convergence_points(attempt, x_axis)
        if not x_values:
            continue
        attempt_number = attempt.get("attempt", plotted + 1)
        plt.step(
            x_values,
            y_values,
            where="post",
            linewidth=1.2,
            alpha=0.65,
            label=f"Tentativa {attempt_number}",
        )
        plotted += 1

    if plotted == 0:
        raise ValueError("Nenhuma tentativa possui pontos de convergencia validos.")

    algorithm = data.get("algorithm", "Algoritmo")
    graph = data.get("graph", json_path.stem)
    best = data.get("best_fitness_global")
    title = f"Curva de convergencia - {algorithm} - {graph}"
    if best is not None:
        title += f" | melhor global: {best}"

    plt.title(title)
    plt.xlabel(labels[x_axis])
    plt.ylabel("Fitness")
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    plt.tight_layout()

    if plotted <= 12:
        plt.legend()

    plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mostra a curva de convergencia de um JSON de resultado."
    )
    parser.add_argument("json_file", help="JSON gerado por um runner de experimento.")
    parser.add_argument(
        "--x-axis",
        choices=["iteration", "elapsed_seconds", "evaluations"],
        default="iteration",
        help="Campo usado no eixo X. Padrao: iteration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        json_path = Path(args.json_file)
        data = load_result(json_path)
        plot_convergence(data, json_path, args.x_axis)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
