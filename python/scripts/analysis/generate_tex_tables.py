#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import _definitive_tables
import _summary_tables


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_DIR = PROJECT_ROOT / "results" / "csvs_definitivos"

DEFINITIVE_CSVS = [
    "cubic_results_definitivo.csv",
    "dimacs_resultados_definitivo.csv",
    "harwell_boieng_results_definitivo.csv",
]

DATASET_NAMES = {
    "cubic_results_definitivo.csv": "CUBIC",
    "dimacs_resultados_definitivo.csv": "\\gls{DIMACS}",
    "harwell_boieng_results_definitivo.csv": "\\gls{HB}",
}

TABLE_KINDS = {
    "qualidade": (
        _definitive_tables.build_quality_columns,
        "Valor do \\gls{{BIP}} e melhores valores de AT, HR e BRKGA na base {dataset}.",
    ),
    "distribuicao": (
        _definitive_tables.build_distribution_columns,
        "Estatísticas das 10 execuções de AT, HR e BRKGA na base {dataset}.",
    ),
    "custo": (
        _definitive_tables.build_cost_columns,
        "Custo da execução que produziu o melhor valor de AT, HR e BRKGA na base {dataset}.",
    ),
    "gaps": (
        _definitive_tables.build_gap_columns,
        "Gaps dos melhores valores de AT, HR e BRKGA em relação ao \\gls{{BIP}} na base {dataset}.",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def pearson(xs: list[float], ys: list[float]) -> float:
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)
    )
    return numerator / denominator if denominator else 0.0


def render_overview_tables(base_dir: Path) -> list[tuple[str, str]]:
    characterization_csv = PROJECT_ROOT / "results" / "instance_characterization" / "summary_by_dataset.csv"
    definitive_csv = base_dir / "resultados_definitivos.csv"
    if not characterization_csv.is_file() or not definitive_csv.is_file():
        return []

    characterization_rows = []
    for row in read_csv(characterization_csv):
        characterization_rows.append(
            {
                "dataset": "TODOS" if row["dataset"] == "ALL" else row["dataset"],
                "instances": row["instances"],
                "vertices": f"{row['min_vertices']} a {row['max_vertices']}",
                "edges": f"{row['min_edges']} a {row['max_edges']}",
                "density": f"{float(row['median_density']):.4f}",
                "degree": f"{float(row['median_avg_degree']):.4f}",
            }
        )
    characterization = _definitive_tables.render_tex(
        characterization_rows,
        [
            ("dataset", "Conj."),
            ("instances", "$N$"),
            ("vertices", "$n(G)$"),
            ("edges", "$m(G)$"),
            ("density", "$\\tilde{d}$"),
            ("degree", "$\\widetilde{\\bar{\\delta}}$"),
        ],
        "Caracterização estrutural das instâncias por conjunto.",
        "tab:caracterizacao_instancias_resultados",
        _definitive_tables.DEFAULT_FONTE,
    )

    definitive_rows = read_csv(definitive_csv)
    grouped = {
        dataset: [row for row in definitive_rows if row["dataset"] == dataset]
        for dataset in ("CUBIC", "DIMACS", "HB")
    }
    status_rows = []
    for dataset, rows in [("TODOS", definitive_rows), *grouped.items()]:
        optimal = sum(
            _definitive_tables.is_optimal_status(row.get("Status")) for row in rows
        )
        status_rows.append(
            {
                "dataset": dataset,
                "instances": str(len(rows)),
                "optimal": str(optimal),
                "best": str(len(rows) - optimal),
                "percent": f"{100.0 * optimal / len(rows):.2f}",
            }
        )
    status = _definitive_tables.render_tex(
        status_rows,
        [
            ("dataset", "Conj."),
            ("instances", "Instâncias"),
            ("optimal", "Ótimos"),
            ("best", "Melhor"),
            ("percent", "\\% Ótimos"),
        ],
        "Status das soluções obtidas pelo \\gls{BIP}.",
        "tab:status_bip",
        _definitive_tables.DEFAULT_FONTE,
    )

    proof_rows = []
    for dataset, rows in grouped.items():
        vertices = [float(row["|V|"]) for row in rows]
        deltas = [float(row["Objetivo"]) - float(row["LB"]) for row in rows]
        relative = [
            100.0 * delta / float(row["Objetivo"])
            for row, delta in zip(rows, deltas)
        ]
        proof_rows.append(
            {
                "dataset": dataset,
                "delta_min": f"{min(deltas):.0f}",
                "delta_med": f"{statistics.median(deltas):.0f}",
                "delta_max": f"{max(deltas):.0f}",
                "gap_min": f"{min(relative):.3f}",
                "gap_med": f"{statistics.median(relative):.3f}",
                "gap_max": f"{max(relative):.3f}",
                "corr_delta": f"{pearson(vertices, deltas):.3f}",
                "corr_gap": f"{pearson(vertices, relative):.3f}",
            }
        )
    proof = _definitive_tables.render_tex(
        proof_rows,
        [
            ("dataset", "Conj."),
            ("delta_min", "$\\Delta_{\\min}$"),
            ("delta_med", "$\\Delta_{\\mathrm{med}}$"),
            ("delta_max", "$\\Delta_{\\max}$"),
            ("gap_min", "$g_{\\min}$"),
            ("gap_med", "$g_{\\mathrm{med}}$"),
            ("gap_max", "$g_{\\max}$"),
            ("corr_delta", "corr.$(n(G),\\Delta)$"),
            ("corr_gap", "corr.$(n(G),g)$"),
        ],
        "Intervalo de prova do \\gls{BIP} por conjunto.",
        "tab:resumo_prova_bip",
        _definitive_tables.DEFAULT_FONTE,
    )
    return [
        ("caracterizacao_instancias_resultados.tex", characterization),
        ("status_bip.tex", status),
        ("resumo_prova_bip.tex", proof),
    ]


def safe_label_stem(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", path.stem)
    return stem.strip("_") or "tabela"


def tex_path_for_csv(output_dir: Path, csv_path: Path) -> Path:
    return output_dir / f"{csv_path.stem}.tex"


def render_definitive_csv_parts(csv_path: Path) -> list[tuple[str, str]]:
    fieldnames, rows = _definitive_tables.read_csv_rows(csv_path)
    methods = _definitive_tables.detect_methods(fieldnames)
    dataset = DATASET_NAMES[csv_path.name]
    base_stem = {
        "cubic_results_definitivo.csv": "cubic",
        "dimacs_resultados_definitivo.csv": "dimacs",
        "harwell_boieng_results_definitivo.csv": "hb",
    }[csv_path.name]
    rendered: list[tuple[str, str]] = []

    for kind, (column_builder, caption_template) in TABLE_KINDS.items():
        columns = column_builder(methods)
        caption = caption_template.format(dataset=dataset)
        label = f"tab:{base_stem}_resultados_{kind}"
        for part_suffix, content in _definitive_tables.render_table_parts(
            rows,
            columns,
            caption,
            label,
            _definitive_tables.DEFAULT_FONTE,
        ):
            rendered.append((f"{base_stem}_resultados_{kind}{part_suffix}.tex", content))
    return rendered


def grouped_auxiliary_specs(base_dir: Path) -> dict[Path, list[_summary_tables.TableSpec]]:
    grouped: dict[Path, list[_summary_tables.TableSpec]] = defaultdict(list)
    for spec in _summary_tables.table_specs(base_dir):
        grouped[spec.source].append(spec)
    return dict(grouped)


def render_auxiliary_csv(specs: list[_summary_tables.TableSpec]) -> str:
    return "\n".join(
        _summary_tables.render_table(spec, _summary_tables.DEFAULT_FONTE)
        for spec in specs
    )


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_all(base_dir: Path, output_dir: Path) -> tuple[list[Path], list[Path]]:
    generated: list[Path] = []
    skipped: list[Path] = []

    for filename, content in render_overview_tables(base_dir):
        output_path = output_dir / filename
        write_file(output_path, content)
        generated.append(output_path)

    for csv_name in DEFINITIVE_CSVS:
        csv_path = base_dir / csv_name
        if not csv_path.is_file():
            skipped.append(csv_path)
            continue
        for filename, content in render_definitive_csv_parts(csv_path):
            output_path = output_dir / filename
            write_file(output_path, content)
            generated.append(output_path)

    for csv_path, specs in grouped_auxiliary_specs(base_dir).items():
        if not csv_path.is_file():
            skipped.append(csv_path)
            continue
        if len(specs) > 1:
            for spec in specs:
                split_name = spec.label.removeprefix("tab:")
                split_path = output_dir / f"{split_name}.tex"
                write_file(split_path, render_auxiliary_csv([spec]))
                generated.append(split_path)
        else:
            output_path = tex_path_for_csv(output_dir, csv_path)
            write_file(output_path, render_auxiliary_csv(specs))
            generated.append(output_path)

    return generated, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera todos os arquivos .tex de tabelas a partir dos CSVs definitivos "
            "e auxiliares. O nome de cada .tex segue o nome do CSV de origem."
        )
    )
    parser.add_argument("output_dir", help="Pasta de saida para os arquivos .tex.")
    parser.add_argument(
        "--base-dir",
        default=str(DEFAULT_BASE_DIR),
        help="Diretorio base dos CSVs definitivos.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Preserva arquivos existentes no diretorio de saida.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir)
    if not base_dir.is_absolute():
        base_dir = PROJECT_ROOT / base_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    if not base_dir.is_dir():
        print(f"Erro: diretorio base nao encontrado: {base_dir}", file=sys.stderr)
        return 1

    if output_dir.exists() and not args.no_clean:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated, skipped = generate_all(base_dir, output_dir)
    print(f"Arquivos .tex gerados em: {output_dir}")
    for path in generated:
        print(f"- {path.name}")
    if skipped:
        print("CSVs ignorados por nao existirem:")
        for path in skipped:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
