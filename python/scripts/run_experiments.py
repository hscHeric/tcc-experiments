#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import glob
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


RUNNERS = {
    "aco_ts": {
        "binary": "aco_ts_runner",
        "options": {
            "attempts": "--attempts",
            "archive_size": "--archive",
            "ants": "--ants",
            "q": "--q",
            "xi": "--xi",
            "threads": "--threads",
            "max_iterations": "--iters",
            "max_time_seconds": "--time",
            "max_stagnation": "--stagnation",
            "local_search_start": "--local-search-start",
            "local_search_interval": "--local-search-interval",
            "ts_iterations": "--ts-iters",
            "ts_neighborhood_size": "--ts-neigh",
            "ts_tabu_tenure": "--ts-tenure",
            "seed": "--seed",
        },
    },
    "hho_rvns": {
        "binary": "hho_rvns_runner",
        "options": {
            "attempts": "--attempts",
            "agents": "--agents",
            "threads": "--threads",
            "max_iterations": "--iters",
            "max_time_seconds": "--time",
            "max_stagnation": "--stagnation",
            "local_search_start": "--local-search-start",
            "local_search_interval": "--local-search-interval",
            "rvns_iterations": "--rvns-iters",
            "rvns_k_max": "--rvns-k",
            "seed": "--seed",
        },
    },
}

DEFAULT_DIFFICULTY_FILES = [
    "results/pli/CUBIC/cubic_results.csv",
    "results/pli/DIMACS/dimacs_resultados.csv",
    "results/pli/HB/harwell_boieng_results.csv",
]


@dataclass(frozen=True)
class Job:
    algorithm: str
    graph: Path
    output: Path
    params: dict[str, Any]


@dataclass(frozen=True)
class GraphSelection:
    path: Path
    difficulty: float | None


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("O arquivo de configuracao deve conter um objeto JSON.")
    return config


def load_difficulty_map(config: dict[str, Any]) -> dict[str, float]:
    files = config.get("difficulty_files", DEFAULT_DIFFICULTY_FILES)
    if not isinstance(files, list):
        raise ValueError("'difficulty_files' deve ser uma lista de CSVs.")

    difficulty_by_name: dict[str, float] = {}
    for file_name in files:
        csv_path = project_path(file_name)
        if not csv_path.is_file():
            continue

        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                continue
            if "Grafo" not in reader.fieldnames or "Tempo (s)" not in reader.fieldnames:
                continue

            for row in reader:
                graph_name = row.get("Grafo", "").strip()
                runtime_text = row.get("Tempo (s)", "").strip()
                if not graph_name or not runtime_text:
                    continue
                try:
                    runtime = float(runtime_text)
                except ValueError:
                    continue

                stem = Path(graph_name).stem
                difficulty_by_name[stem] = max(
                    difficulty_by_name.get(stem, 0.0), runtime
                )

    return difficulty_by_name


def expand_graphs(config: dict[str, Any]) -> list[GraphSelection]:
    graph_config = config.get("graphs")
    if not isinstance(graph_config, dict):
        raise ValueError("Configure 'graphs' como objeto com 'files' e/ou 'globs'.")

    graph_paths: list[Path] = []

    for file_name in graph_config.get("files", []):
        graph_paths.append(project_path(file_name))

    for pattern in graph_config.get("globs", []):
        matches = glob.glob(str(project_path(pattern)), recursive=True)
        graph_paths.extend(Path(match) for match in matches)

    unique_paths = sorted(set(graph_paths), key=lambda path: path.as_posix())
    missing = [path for path in unique_paths if not path.is_file()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"Grafos nao encontrados:\n{missing_text}")
    if not unique_paths:
        raise ValueError("Nenhum grafo foi selecionado pela configuracao.")

    difficulty_by_name = load_difficulty_map(config)
    selected = [
        GraphSelection(path=path, difficulty=difficulty_by_name.get(path.stem))
        for path in unique_paths
    ]
    selected.sort(
        key=lambda graph: (
            graph.difficulty is None,
            -(graph.difficulty or 0.0),
            graph.path.as_posix(),
        )
    )
    return selected


def configured_algorithms(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    algorithms = config.get("algorithms")
    if not isinstance(algorithms, dict):
        raise ValueError("Configure 'algorithms' como objeto.")

    selected: dict[str, dict[str, Any]] = {}
    for name, algorithm_config in algorithms.items():
        if name not in RUNNERS:
            valid = ", ".join(sorted(RUNNERS))
            raise ValueError(f"Algoritmo invalido '{name}'. Valores validos: {valid}")
        if not isinstance(algorithm_config, dict):
            raise ValueError(f"Configuracao de '{name}' deve ser um objeto.")
        if algorithm_config.get("enabled", True):
            params = algorithm_config.get("params", {})
            if not isinstance(params, dict):
                raise ValueError(f"'algorithms.{name}.params' deve ser um objeto.")
            selected[name] = params

    if not selected:
        raise ValueError("Nenhum algoritmo esta habilitado.")
    return selected


def build_jobs(config: dict[str, Any]) -> list[Job]:
    graphs = expand_graphs(config)
    algorithms = configured_algorithms(config)
    output_root = project_path(config.get("output_dir", "results/experiments/manual"))
    add_algorithm_dir = len(algorithms) > 1

    jobs: list[Job] = []
    for algorithm, params in algorithms.items():
        for graph in graphs:
            output_dir = output_root / algorithm if add_algorithm_dir else output_root
            output_file = output_dir / f"{graph.path.stem}.json"
            jobs.append(
                Job(
                    algorithm=algorithm,
                    graph=graph.path,
                    output=output_file,
                    params=params,
                )
            )
    return jobs


def runner_path(build_type: str, algorithm: str) -> Path:
    binary = RUNNERS[algorithm]["binary"]
    return PROJECT_ROOT / "build" / build_type / binary


def command_for_job(job: Job, build_type: str) -> list[str]:
    executable = runner_path(build_type, job.algorithm)
    if not executable.is_file():
        raise FileNotFoundError(
            f"Runner nao encontrado: {executable}\n"
            f"Compile antes com: mise run build-{build_type.lower()}"
        )

    options = RUNNERS[job.algorithm]["options"]
    unknown = sorted(set(job.params) - set(options))
    if unknown:
        valid = ", ".join(sorted(options))
        raise ValueError(
            f"Parametros invalidos para {job.algorithm}: {', '.join(unknown)}. "
            f"Parametros validos: {valid}"
        )

    command = [str(executable), str(job.graph), "--output", str(job.output)]
    for name, value in job.params.items():
        if value is None:
            continue
        command.extend([options[name], str(value)])
    return command


def load_result(job: Job) -> dict[str, Any]:
    with job.output.open(encoding="utf-8") as result_file:
        result = json.load(result_file)

    attempts = result.get("attempts", [])
    runtimes = [attempt.get("total_runtime_seconds", 0.0) for attempt in attempts]
    return {
        "algorithm": job.algorithm,
        "graph": job.graph.name,
        "output": str(job.output.relative_to(PROJECT_ROOT)),
        "best_fitness_global": result.get("best_fitness_global"),
        "attempts": len(attempts),
        "total_runtime_seconds": sum(runtimes),
    }


def is_completed_result(job: Job) -> bool:
    if not job.output.is_file():
        return False

    try:
        with job.output.open(encoding="utf-8") as result_file:
            result = json.load(result_file)
    except (OSError, json.JSONDecodeError):
        return False

    attempts = result.get("attempts")
    expected_attempts = int(job.params.get("attempts", 1))
    return (
        isinstance(attempts, list)
        and len(attempts) == expected_attempts
        and "best_fitness_global" in result
    )


def write_summary(rows: list[dict[str, Any]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "algorithm",
                "graph",
                "best_fitness_global",
                "attempts",
                "total_runtime_seconds",
                "output",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def run_jobs(
    jobs: list[Job], build_type: str, dry_run: bool, skip_existing: bool
) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []

    for index, job in enumerate(jobs, start=1):
        if skip_existing and is_completed_result(job):
            print(f"[{index}/{len(jobs)}] pulando existente: {job.output}")
            summary_rows.append(load_result(job))
            continue

        command = command_for_job(job, build_type)
        print(f"[{index}/{len(jobs)}] {' '.join(command)}")

        if dry_run:
            continue

        job.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
        summary_rows.append(load_result(job))

    return summary_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa experimentos configurados em JSON para os runners C++."
    )
    parser.add_argument(
        "config",
        nargs="+",
        help="Arquivo JSON com a configuracao dos experimentos.",
    )
    parser.add_argument(
        "--build-type",
        default="Release",
        choices=["Debug", "Release", "RelWithDebInfo"],
        help="Pasta de build onde os runners foram compilados.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os comandos sem executar os experimentos.",
    )
    parser.add_argument(
        "--skip-existing",
        "--skipping-existing",
        "--skiping-existing",
        action=argparse.BooleanOptionalAction,
        dest="skip_existing",
        default=True,
        help="Nao executa novamente resultados JSON que ja existem. Padrao: ativo.",
    )
    parser.add_argument(
        "--summary",
        help="Caminho do CSV de resumo. Se omitido, usa '<output_dir>/summary.csv'.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configs = [load_config(project_path(config_file)) for config_file in args.config]
    jobs = [job for config in configs for job in build_jobs(config)]

    try:
        rows = run_jobs(jobs, args.build_type, args.dry_run, args.skip_existing)
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    if not args.dry_run:
        summary_path = (
            project_path(args.summary)
            if args.summary
            else project_path(
                configs[0].get("output_dir", "results/experiments/manual")
            )
            / "summary.csv"
        )
        write_summary(rows, summary_path)
        print(f"Resumo salvo em: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
