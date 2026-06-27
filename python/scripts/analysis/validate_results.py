#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

METHOD_DIRS = {
    "ACO_TS": PROJECT_ROOT / "results" / "experiments" / "aco_ts",
    "HHO_RVNS": PROJECT_ROOT / "results" / "experiments" / "hho_rvns",
    "BRKGA": PROJECT_ROOT / "results" / "experiments" / "brkga",
}

PLI_CSVS = {
    "CUBIC": PROJECT_ROOT / "results" / "pli" / "CUBIC" / "cubic_results.csv",
    "DIMACS": PROJECT_ROOT / "results" / "pli" / "DIMACS" / "dimacs_resultados.csv",
    "HB": PROJECT_ROOT / "results" / "pli" / "HB" / "harwell_boieng_results.csv",
}

DEFINITIVE_CSVS = {
    "CUBIC": PROJECT_ROOT
    / "results"
    / "csvs_definitivos"
    / "cubic_results_definitivo.csv",
    "DIMACS": PROJECT_ROOT
    / "results"
    / "csvs_definitivos"
    / "dimacs_resultados_definitivo.csv",
    "HB": PROJECT_ROOT
    / "results"
    / "csvs_definitivos"
    / "harwell_boieng_results_definitivo.csv",
}

EXPECTED_DATASET_ROWS = {"CUBIC": 30, "DIMACS": 50, "HB": 50}
EXPECTED_ARTIFACT_COUNTS = {
    "results/csvs_definitivos": 16,
    "results/instance_characterization": 2,
    "results/tabelas_tex": 35,
    "results/graficos": 184,
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"arquivo ausente: {path.relative_to(PROJECT_ROOT)}")
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def graph_name(row: dict[str, str]) -> str:
    for key in ("Grafo", "graph", "Instance", "instancia"):
        value = row.get(key)
        if value:
            return Path(value).stem
    raise ValueError("CSV sem coluna de identificacao do grafo")


def verify_json_results() -> dict[str, int]:
    counts: dict[str, int] = {}
    graph_sets: dict[str, set[str]] = {}

    for method, directory in METHOD_DIRS.items():
        paths = sorted(directory.glob("*.json"))
        graphs: set[str] = set()
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            attempts = data.get("attempts")
            if not isinstance(attempts, list) or len(attempts) != 10:
                raise ValueError(
                    f"{path.relative_to(PROJECT_ROOT)}: esperado attempts com 10 itens"
                )
            graph = str(data.get("graph") or path.stem)
            if graph in graphs:
                raise ValueError(f"grafo duplicado em {method}: {graph}")
            graphs.add(graph)
        counts[method] = len(paths)
        graph_sets[method] = graphs

    expected = sum(EXPECTED_DATASET_ROWS.values())
    for method, count in counts.items():
        if count != expected:
            raise ValueError(f"{method}: esperados {expected} JSONs, encontrados {count}")

    first_method = next(iter(graph_sets))
    reference = graph_sets[first_method]
    for method, graphs in graph_sets.items():
        if graphs != reference:
            raise ValueError(f"conjunto de grafos divergente em {method}")
    return counts


def verify_csvs(include_derived: bool) -> dict[str, int]:
    counts: dict[str, int] = {}
    for dataset, expected in EXPECTED_DATASET_ROWS.items():
        pli_rows = read_csv_rows(PLI_CSVS[dataset])
        if len(pli_rows) != expected:
            raise ValueError(f"{dataset}: CSV do BIP possui {len(pli_rows)} linhas")
        counts[dataset] = len(pli_rows)
        if include_derived:
            definitive_rows = read_csv_rows(DEFINITIVE_CSVS[dataset])
            if len(definitive_rows) != expected:
                raise ValueError(
                    f"{dataset}: CSV definitivo possui {len(definitive_rows)} linhas"
                )
            if {graph_name(row) for row in pli_rows} != {
                graph_name(row) for row in definitive_rows
            }:
                raise ValueError(
                    f"{dataset}: grafos divergentes entre BIP e CSV definitivo"
                )

    expected_total = sum(EXPECTED_DATASET_ROWS.values())
    counts["TODOS"] = expected_total
    if include_derived:
        combined = read_csv_rows(
            PROJECT_ROOT
            / "results"
            / "csvs_definitivos"
            / "resultados_definitivos.csv"
        )
        if len(combined) != expected_total:
            raise ValueError(
                f"CSV combinado possui {len(combined)} linhas, "
                f"esperado {expected_total}"
            )
        violations = read_csv_rows(
            PROJECT_ROOT / "results" / "csvs_definitivos" / "violacoes_bounds.csv"
        )
        if violations:
            raise ValueError(
                f"foram encontradas {len(violations)} violacoes de bounds"
            )
    return counts


def verify_output_types() -> dict[str, int]:
    allowed = {
        PROJECT_ROOT / "results" / "csvs_definitivos": {".csv"},
        PROJECT_ROOT / "results" / "instance_characterization": {".csv"},
        PROJECT_ROOT / "results" / "tabelas_tex": {".tex"},
        PROJECT_ROOT / "results" / "graficos": {".png"},
    }
    counts: dict[str, int] = {}
    for directory, suffixes in allowed.items():
        files = [path for path in directory.rglob("*") if path.is_file()]
        invalid = [path for path in files if path.suffix.lower() not in suffixes]
        if invalid:
            relative = ", ".join(
                str(path.relative_to(PROJECT_ROOT)) for path in invalid[:5]
            )
            raise ValueError(f"tipo de arquivo invalido: {relative}")
        if not files:
            raise ValueError(f"diretorio sem artefatos: {directory.relative_to(PROJECT_ROOT)}")
        relative = str(directory.relative_to(PROJECT_ROOT))
        expected = EXPECTED_ARTIFACT_COUNTS[relative]
        if len(files) != expected:
            raise ValueError(
                f"{relative}: esperados {expected} artefatos, encontrados {len(files)}"
            )
        counts[relative] = len(files)
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida os resultados brutos e, opcionalmente, os derivados."
    )
    parser.add_argument(
        "--include-derived",
        action="store_true",
        help="Também valida CSVs, tabelas e gráficos gerados.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = {
            "jsons": verify_json_results(),
            "csvs": verify_csvs(args.include_derived),
        }
        if args.include_derived:
            result["artefatos"] = verify_output_types()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
