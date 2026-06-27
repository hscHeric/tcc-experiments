#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import unicodedata
from pathlib import Path
from typing import Iterable


DEFAULT_CAPTION = "Resultados computacionais por instância."
DEFAULT_LABEL = "tab:resultados_definitivos"
DEFAULT_GAP_LABEL = "tab:gaps_resultados_definitivos"
DEFAULT_FONTE = "Autor (2026)."
MAX_MAIN_TABLE_ROWS = 30

BASE_COLUMNS = [
    ("Grafo", "$G$"),
    ("|V|", "$n$"),
    ("|E|", "$m$"),
    ("LB", "LB"),
    ("Objetivo", "$z_{\\mathrm{BIP}}$"),
    ("UB", "UB"),
]

METHOD_SUFFIXES = [
    "",
    "_media",
    "_mediana",
    "_melhor_tempo_s",
    "_melhor_avaliacoes",
    "_tempo_total_s",
    "_valores_rodadas",
]

METHOD_HEADERS = [
    ("", "$z^*$"),
    ("_media", "$\\bar{z}$"),
    ("_mediana", "$\\tilde{z}$"),
    ("_desvio_padrao", "$\\sigma_z$"),
    ("_melhor_avaliacoes", "$a^*$"),
    ("_melhor_tempo_s", "$t^*$"),
]

GAP_HEADERS = [
    ("_gap_prova", "$\\Delta z$"),
    ("_gap_relativo", "$g$ (\\%)"),
]


def latex_escape(value: object) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_round_values(value: object) -> list[float]:
    if value is None:
        return []
    values: list[float] = []
    for item in str(value).replace(",", ";").split(";"):
        number = parse_float(item)
        if number is not None:
            values.append(number)
    return values


def format_number(value: object, decimals: int = 3) -> str:
    number = parse_float(value)
    if number is None:
        text = "" if value is None else str(value).strip()
        return "-" if not text else text
    if math.isclose(number, round(number), abs_tol=1e-9):
        return str(int(round(number)))
    return f"{number:.{decimals}f}".rstrip("0").rstrip(".")


def format_percent(value: object) -> str:
    number = parse_float(value)
    if number is None:
        return "-"
    return f"{number:.2f}"


def pli_lb_gap(row: dict[str, str]) -> str:
    objective = parse_float(row.get("Objetivo"))
    lb = parse_float(row.get("LB"))
    if objective is None or lb in {None, 0.0}:
        return "-"
    return format_percent(((objective - lb) / lb) * 100.0)


def absolute_method_gap(row: dict[str, str], prefix: str) -> str:
    column = f"{prefix}_gap_prova"
    if column in row and row[column].strip():
        return format_number(row[column])

    method_value = parse_float(row.get(prefix))
    objective = parse_float(row.get("Objetivo"))
    if method_value is None or objective is None:
        return "-"
    return format_number(method_value - objective)


def relative_method_gap(row: dict[str, str], prefix: str) -> str:
    column = f"{prefix}_gap_relativo"
    if column in row and row[column].strip():
        return format_percent(row[column])

    method_value = parse_float(row.get(prefix))
    objective = parse_float(row.get("Objetivo"))
    if method_value is None or objective in {None, 0.0}:
        return "-"
    return format_percent(((method_value - objective) / objective) * 100.0)


def method_stddev(row: dict[str, str], prefix: str) -> str:
    for suffix in ("_desvio_padrao", "_std", "_stddev", "_dp"):
        column = f"{prefix}{suffix}"
        if column in row and row[column].strip():
            return format_number(row[column])

    values = parse_round_values(row.get(f"{prefix}_valores_rodadas"))
    if len(values) < 2:
        return "-"
    return format_number(statistics.stdev(values))


def detect_methods(fieldnames: Iterable[str]) -> list[str]:
    columns = list(fieldnames)
    column_set = set(columns)
    prefixes: list[str] = []

    for column in columns:
        for suffix in METHOD_SUFFIXES[1:]:
            if not column.endswith(suffix):
                continue
            prefix = column[: -len(suffix)]
            if prefix and prefix not in prefixes and prefix in column_set:
                prefixes.append(prefix)

    priority = {
        "ACO_TS": 0,
        "ACO": 0,
        "HHO_RVNS": 1,
        "HHO": 1,
        "BRKGA": 2,
        "BRKGA_MP_IPR": 2,
    }
    return sorted(
        prefixes,
        key=lambda prefix: (priority.get(prefix, len(priority)), prefixes.index(prefix)),
    )


def method_label(prefix: str) -> str:
    labels = {
        "HHO_RVNS": "HR",
        "ACO_TS": "AT",
        "BRKGA": "BRKGA",
        "BRKGA_MP_IPR": "BRKGA",
    }
    return labels.get(prefix, prefix.replace("_", "-"))


def build_output_columns(methods: list[str]) -> list[tuple[str, str]]:
    columns = BASE_COLUMNS.copy()
    for method in methods:
        label = method_label(method)
        for suffix, header in METHOD_HEADERS:
            columns.append((f"{method}{suffix}", f"{label} {header}"))
    return columns


def build_quality_columns(methods: list[str]) -> list[tuple[str, str]]:
    columns = BASE_COLUMNS.copy()
    for method in methods:
        columns.append((method, f"{method_label(method)} $z^*$"))
    return columns


def build_distribution_columns(methods: list[str]) -> list[tuple[str, str]]:
    columns = [("Grafo", "$G$")]
    for method in methods:
        label = method_label(method)
        columns.extend(
            [
                (f"{method}_media", f"{label} $\\bar{{z}}$"),
                (f"{method}_mediana", f"{label} $\\tilde{{z}}$"),
                (f"{method}_desvio_padrao", f"{label} $\\sigma_z$"),
            ]
        )
    return columns


def build_cost_columns(methods: list[str]) -> list[tuple[str, str]]:
    columns = [("Grafo", "$G$")]
    for method in methods:
        label = method_label(method)
        columns.extend(
            [
                (f"{method}_melhor_avaliacoes", f"{label} $a^*$"),
                (f"{method}_melhor_iteracoes", f"{label} $c^*$"),
                (f"{method}_melhor_tempo_s", f"{label} $t^*$"),
            ]
        )
    return columns


def build_gap_columns(methods: list[str]) -> list[tuple[str, str]]:
    columns = [("Grafo", "$G$")]
    for method in methods:
        label = method_label(method)
        for suffix, header in GAP_HEADERS:
            columns.append((f"{method}{suffix}", f"{label} {header}"))
    return columns


def is_optimal_status(value: object) -> bool:
    status = "" if value is None else str(value).strip().lower()
    normalized = unicodedata.normalize("NFKD", status)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized in {"otimo", "optimal"} or "otim" in normalized


def is_best_status(value: object) -> bool:
    status = "" if value is None else str(value).strip().lower()
    normalized = unicodedata.normalize("NFKD", status)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized == "melhor"


def pli_status_marker(row: dict[str, str]) -> str:
    if is_optimal_status(row.get("Status")):
        return r"$^{\circ}$"
    if is_best_status(row.get("Status")):
        return r"$^{m}$"
    return ""


def best_value_columns(row: dict[str, str], columns: list[tuple[str, str]]) -> set[str]:
    candidates: list[tuple[str, float]] = []
    for column, header in columns:
        if column == "Objetivo" or header.endswith(" $z^*$"):
            value = parse_float(row.get(column))
            if value is not None:
                candidates.append((column, value))
    if not candidates:
        return set()

    best = min(value for _, value in candidates)
    return {
        column
        for column, value in candidates
        if math.isclose(value, best, rel_tol=0.0, abs_tol=1e-9)
    }


def row_value(row: dict[str, str], column: str, header: str) -> str:
    if column == "__PLI_LB_GAP__":
        return pli_lb_gap(row)
    if column.endswith("_desvio_padrao"):
        return method_stddev(row, column[: -len("_desvio_padrao")])
    if column.endswith("_melhor_avaliacoes"):
        return format_number(row.get(column), decimals=0)
    if (
        column in {"|V|", "|E|", "LB", "UB"}
        or column.endswith("_melhor_rodada")
        or column.endswith("_rodadas")
    ):
        return format_number(row.get(column), decimals=0)
    if (
        column in {"Densidade", "Objetivo"}
        or header.endswith(" $z^*$")
        or column.endswith("_media")
        or column.endswith("_mediana")
        or column.endswith("_melhor_tempo_s")
        or column.endswith("_tempo_total_s")
        or header.endswith("(\\%)")
    ):
        return format_number(row.get(column))
    return row.get(column, "").strip() or "-"


def gap_row_value(row: dict[str, str], column: str) -> str:
    if column == "Grafo":
        return row.get(column, "").strip() or "-"
    if column.endswith("_gap_prova"):
        return absolute_method_gap(row, column[: -len("_gap_prova")])
    if column.endswith("_gap_relativo"):
        return relative_method_gap(row, column[: -len("_gap_relativo")])
    return row.get(column, "").strip() or "-"


def read_csv_rows(input_csv: Path) -> tuple[list[str], list[dict[str, str]]]:
    with input_csv.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if not fieldnames:
        raise ValueError("CSV sem cabecalho.")
    if not rows:
        raise ValueError("CSV vazio.")
    return fieldnames, rows


def render_tex(
    rows: list[dict[str, str]],
    columns: list[tuple[str, str]],
    caption: str,
    label: str,
    fonte: str,
) -> str:
    alignment = "l" * len(columns)
    lines = [
        r"\begin{table}[h!]",
        r"    \scriptsize",
        r"    \captionsetup{width=\linewidth}",
        rf"    \Caption{{\label{{{label}}} {caption}}}",
        r"    \IBGEtab{}{",
        rf"        \begin{{tabular}}{{{alignment}}}",
        r"            \toprule",
        "            " + " & ".join(header for _, header in columns) + r" \\",
        r"            \midrule \midrule",
    ]

    for row in rows:
        values = []
        bold_columns = best_value_columns(row, columns)
        for column, header in columns:
            value = latex_escape(row_value(row, column, header))
            if column in bold_columns:
                value = rf"\textbf{{{value}}}"
            if column == "Objetivo":
                value = f"{value}{pli_status_marker(row)}"
            values.append(value)
        lines.append("            " + " & ".join(values) + r" \\")

    lines.extend(
        [
            r"            \bottomrule",
            r"        \end{tabular}",
            r"    }{",
            rf"    \Fonte{{{fonte}}}",
            r"}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def chunk_rows(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def part_label(label: str, part_number: int) -> str:
    return f"{label}_parte_{part_number}"


def part_caption(caption: str, part_number: int, total_parts: int) -> str:
    if total_parts == 1:
        return caption
    return f"{caption} Parte {part_number} de {total_parts}."


def render_table_parts(
    rows: list[dict[str, str]],
    columns: list[tuple[str, str]],
    caption: str,
    label: str,
    fonte: str,
    max_rows: int = MAX_MAIN_TABLE_ROWS,
) -> list[tuple[str, str]]:
    chunks = chunk_rows(rows, max_rows)
    total_parts = len(chunks)
    rendered: list[tuple[str, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        part = f"_parte_{index}" if total_parts > 1 else ""
        rendered.append(
            (
                part,
                render_tex(
                    chunk,
                    columns,
                    part_caption(caption, index, total_parts),
                    f"{label}{part}",
                    fonte,
                ),
            )
        )
    return rendered


def render_main_tables_tex(
    rows: list[dict[str, str]],
    columns: list[tuple[str, str]],
    caption: str,
    label: str,
    fonte: str,
) -> str:
    chunks = chunk_rows(rows, MAX_MAIN_TABLE_ROWS)
    total_parts = len(chunks)
    tables: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        tables.append(
            render_tex(
                chunk,
                columns,
                part_caption(caption, index, total_parts),
                part_label(label, index) if total_parts > 1 else label,
                fonte,
            )
        )
    return "\n".join(tables)


def render_gap_tex(
    rows: list[dict[str, str]],
    columns: list[tuple[str, str]],
    caption: str,
    label: str,
    fonte: str,
) -> str:
    alignment = "l" * len(columns)
    lines = [
        r"\begin{table}[h!]",
        r"    \scriptsize",
        r"    \captionsetup{width=\linewidth}",
        rf"    \Caption{{\label{{{label}}} {caption}}}",
        r"    \IBGEtab{}{",
        rf"        \begin{{tabular}}{{{alignment}}}",
        r"            \toprule",
        "            " + " & ".join(header for _, header in columns) + r" \\",
        r"            \midrule \midrule",
    ]

    for row in rows:
        values = [latex_escape(gap_row_value(row, column)) for column, _ in columns]
        lines.append("            " + " & ".join(values) + r" \\")

    lines.extend(
        [
            r"            \bottomrule",
            r"        \end{tabular}",
            r"    }{",
            rf"    \Fonte{{{fonte}}}",
            r"}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_tex(output_tex: Path, content: str) -> None:
    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Converte um CSV definitivo de resultados em uma tabela LaTeX no "
            "formato IBGE usado no projeto."
        )
    )
    parser.add_argument("input_csv", help="CSV definitivo de entrada.")
    parser.add_argument("output_tex", help="Arquivo .tex de saida.")
    parser.add_argument(
        "--caption",
        default=DEFAULT_CAPTION,
        help="Caption da tabela. Tambem pode ser alterada no topo do script.",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help="Label da tabela principal. Tambem pode ser alterado no topo do script.",
    )
    parser.add_argument(
        "--gap-label",
        default=DEFAULT_GAP_LABEL,
        help="Label da tabela de gaps.",
    )
    parser.add_argument(
        "--fonte",
        default=DEFAULT_FONTE,
        help="Fonte exibida abaixo da tabela.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_tex = Path(args.output_tex)

    if not input_csv.is_file():
        print(f"Erro: arquivo de entrada nao encontrado: {input_csv}", file=sys.stderr)
        return 1

    try:
        fieldnames, rows = read_csv_rows(input_csv)
        methods = detect_methods(fieldnames)
        columns = build_output_columns(methods)
        gap_columns = build_gap_columns(methods)
        main_tex = render_main_tables_tex(
            rows, columns, args.caption, args.label, args.fonte
        )
        gap_caption = (
            "Gaps absolutos e relativos das metaheuristicas em relacao ao modelo exato."
        )
        gap_tex = render_gap_tex(
            rows, gap_columns, gap_caption, args.gap_label, args.fonte
        )
        tex = main_tex + "\n" + gap_tex
        write_tex(output_tex, tex)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print(f"Tabela gerada em: {output_tex}")
    print("Metaheuristicas detectadas: " + (", ".join(methods) if methods else "nenhuma"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
