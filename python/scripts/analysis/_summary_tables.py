#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "tabelas_tex" / "tabelas_auxiliares_resultados.tex"
DEFAULT_FONTE = "Autor (2026)."

METHOD_LABELS = {
    "PLI": "PLIB",
    "ACO_TS": "AT",
    "ACO_R-TS": "AT",
    "HHO_RVNS": "HR",
    "HHO-RVNS": "HR",
    "BRKGA": "BRKGA",
    "BRKGA_MP_IPR": "BRKGA",
}

STOP_LABELS = {
    "max_iterations": "Limite de iterações",
    "max_iters": "Limite de iterações",
    "max_generations": "Limite de gerações",
    "stagnation": "Estagnação",
    "time_limit": "Limite de tempo",
}

VARIABLE_LABELS = {
    "gap_relativo_melhor": "$g^*$",
    "gap_relativo_mediano_das_10_execucoes": "$\\tilde{g}_{10}$",
}


@dataclass(frozen=True)
class ColumnSpec:
    source: str
    header: str
    formatter: Callable[[str], str] | None = None


@dataclass(frozen=True)
class TableSpec:
    source: Path
    label: str
    caption: str
    columns: tuple[ColumnSpec, ...]
    row_filter: Callable[[dict[str, str]], bool] | None = None
    row_transform: Callable[[dict[str, str]], dict[str, str]] | None = None
    row_expand: Callable[[dict[str, str]], Iterable[dict[str, str]]] | None = None


def project_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


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


def fmt_int(value: str) -> str:
    number = parse_float(value)
    if number is None:
        return latex_escape(value) if value else "-"
    return str(int(round(number)))


def fmt_num(value: str, decimals: int = 3) -> str:
    number = parse_float(value)
    if number is None:
        return latex_escape(value) if value else "-"
    if math.isclose(number, round(number), abs_tol=1e-9):
        return str(int(round(number)))
    return f"{number:.{decimals}f}".rstrip("0").rstrip(".")


def fmt_pct(value: str) -> str:
    number = parse_float(value)
    if number is None:
        return latex_escape(value) if value else "-"
    return f"{number:.4f}"


def fmt_pvalue(value: str) -> str:
    number = parse_float(value)
    if number is None:
        return latex_escape(value) if value else "-"
    if number < 0.0001:
        return f"{number:.2e}"
    return f"{number:.4f}"


def fmt_dataset(value: str) -> str:
    return latex_escape(value)


def fmt_method(value: str) -> str:
    return latex_escape(METHOD_LABELS.get(value, value.replace("_", "-")))


def fmt_comparison(value: str) -> str:
    parts = str(value).split("_vs_")
    if len(parts) == 2:
        return f"{fmt_method(parts[0])} $\\times$ {fmt_method(parts[1])}"
    return latex_escape(value.replace("_", "-"))


def fmt_variable(value: str) -> str:
    return VARIABLE_LABELS.get(value, latex_escape(value.replace("_", "-")))


def fmt_stop(value: str) -> str:
    return latex_escape(STOP_LABELS.get(value, value.replace("_", "-")))


def fmt_methods(value: str) -> str:
    return ", ".join(fmt_method(part) for part in str(value).split(",") if part)


def fmt_best_median(value: str) -> str:
    return fmt_method(value)


def col(source: str, header: str, formatter: Callable[[str], str] | None = None) -> ColumnSpec:
    return ColumnSpec(source=source, header=header, formatter=formatter)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def filter_best_gap(row: dict[str, str]) -> bool:
    return row.get("variavel") == "gap_relativo_melhor"


def expand_quality_reference(row: dict[str, str]) -> Iterable[dict[str, str]]:
    methods = (
        ("AT", "ACO_TS"),
        ("HR", "HHO_RVNS"),
        ("BRKGA", "BRKGA"),
    )
    for method, prefix in methods:
        yield {
            "dataset": row["dataset"],
            "n_instancias": row["n_instancias"],
            "method": method,
            "melhor_que_bip": row[f"{prefix}_melhor_que_PLI"],
            "empate_com_bip": row[f"{prefix}_empate_com_PLI"],
            "gap_mediano": row[f"{prefix}_gap_mediano"],
        }


def normalize_caption(text: str) -> str:
    replacements = {
        "estatisticamente": "estatisticamente",
        "meta-heuristicas": "meta-heurísticas",
        "instancias": "instâncias",
        "metodos": "métodos",
        "Metodos": "Métodos",
        "metodo": "método",
        "numero": "número",
        "avaliacoes": "avaliações",
        "execucoes": "execuções",
        "execucao": "execução",
        "criterios": "critérios",
        "portugues": "português",
        "comparacoes": "comparações",
        "comparacao": "comparação",
        "correcao": "correção",
        "referencia": "referência",
        "estatistica": "estatística",
        "hipotese": "hipótese",
        "diferencas": "diferenças",
        "diferenca": "diferença",
        "apos": "após",
        "multiplas": "múltiplas",
        "medio": "médio",
        "mediano": "mediano",
        "aleatorias": "aleatórias",
        "genetico": "genético",
        "evidencia": "evidência",
        "variavel": "variável",
        "interpretacao": "interpretação",
        "sao": "são",
        "tem": "têm",
    }
    for source, target in replacements.items():
        text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return text


def render_table(spec: TableSpec, fonte: str) -> str:
    rows = read_rows(spec.source)
    if spec.row_filter is not None:
        rows = [row for row in rows if spec.row_filter(row)]
    if spec.row_transform is not None:
        rows = [spec.row_transform(row) for row in rows]
    if spec.row_expand is not None:
        rows = [expanded for row in rows for expanded in spec.row_expand(row)]

    alignment = "l" * len(spec.columns)
    lines = [
        r"\begin{table}[h!]",
        r"    \scriptsize",
        r"    \captionsetup{width=\linewidth}",
        rf"    \Caption{{\label{{{spec.label}}} {normalize_caption(spec.caption)}}}",
        r"    \IBGEtab{}{",
        rf"        \begin{{tabular}}{{{alignment}}}",
        r"            \toprule",
        "            " + " & ".join(column.header for column in spec.columns) + r" \\",
        r"            \midrule \midrule",
    ]

    for row in rows:
        values: list[str] = []
        for column in spec.columns:
            value = row.get(column.source, "")
            values.append(
                column.formatter(value) if column.formatter is not None else latex_escape(value)
            )
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


def table_specs(base_dir: Path) -> list[TableSpec]:
    stats_dir = base_dir / "analise_estatistica"
    return [
        TableSpec(
            source=base_dir / "resumo_resultados.csv",
            label="tab:resumo_qualidade_melhores",
            caption="Frequência de melhores resultados do \\gls{BIP}, AT, HR e BRKGA por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("n_instancias", "$N$", fmt_int),
                col("PLI_melhor_ou_empate", "BIP $M/E$", fmt_int),
                col("ACO_TS_melhor_ou_empate", "AT $M/E$", fmt_int),
                col("HHO_RVNS_melhor_ou_empate", "HR $M/E$", fmt_int),
                col("BRKGA_melhor_ou_empate", "BRKGA $M/E$", fmt_int),
                col("ACO_TS_vitoria_estrita", "AT $V$", fmt_int),
                col("HHO_RVNS_vitoria_estrita", "HR $V$", fmt_int),
                col("BRKGA_vitoria_estrita", "BRKGA $V$", fmt_int),
            ),
        ),
        TableSpec(
            source=base_dir / "resumo_resultados.csv",
            label="tab:resumo_qualidade_referencia",
            caption="Resultados de AT, HR e BRKGA em relação ao valor do \\gls{BIP} por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("n_instancias", "$N$", fmt_int),
                col("method", "Método", fmt_method),
                col("melhor_que_bip", "$<z_{\\mathrm{BIP}}$", fmt_int),
                col("empate_com_bip", "$=z_{\\mathrm{BIP}}$", fmt_int),
                col("gap_mediano", "$\\tilde{g}$ (\\%)", fmt_pct),
            ),
            row_expand=expand_quality_reference,
        ),
        TableSpec(
            source=base_dir / "resumo_resultados.csv",
            label="tab:resumo_custo_conjuntos_com_brkga",
            caption="Tempo e avaliações da execução que produziu o melhor valor por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("n_instancias", "$N$", fmt_int),
                col("ACO_TS_tempo_mediano_s", "AT $\\tilde{t}^*$", fmt_num),
                col("HHO_RVNS_tempo_mediano_s", "HR $\\tilde{t}^*$", fmt_num),
                col("BRKGA_tempo_mediano_s", "BRKGA $\\tilde{t}^*$", fmt_num),
                col("ACO_TS_avaliacoes_medianas", "AT $\\tilde{a}^*$", fmt_int),
                col("HHO_RVNS_avaliacoes_medianas", "HR $\\tilde{a}^*$", fmt_int),
                col("BRKGA_avaliacoes_medianas", "BRKGA $\\tilde{a}^*$", fmt_int),
            ),
        ),
        TableSpec(
            source=base_dir / "resumo_basico_metodos.csv",
            label="tab:resumo_basico_metodos",
            caption="Síntese da qualidade de cada método por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo", "Metodo", fmt_method),
                col("instancias", "$N$", fmt_int),
                col("melhor_ou_empate", "$M/E$", fmt_int),
                col("vitoria_estrita", "$V$", fmt_int),
                col("melhor_que_PLI", "$<$PLIB", fmt_int),
                col("empate_com_PLI", "$=$PLIB", fmt_int),
                col("pior_que_PLI", "$>$PLIB", fmt_int),
                col("gap_mediano", "$\\tilde{g}$", fmt_pct),
            ),
        ),
        TableSpec(
            source=base_dir / "resumo_igualdades_pareadas.csv",
            label="tab:igualdades_pareadas",
            caption="Comparações pareadas dos melhores valores de AT, HR e BRKGA.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo_a", "$A$", fmt_method),
                col("metodo_b", "$B$", fmt_method),
                col("a_melhor", "$A<B$", fmt_int),
                col("b_melhor", "$B<A$", fmt_int),
                col("iguais", "$A=B$", fmt_int),
                col("instancias", "$N$", fmt_int),
            ),
        ),
        TableSpec(
            source=base_dir / "resumo_robustez_metaheuristicas.csv",
            label="tab:robustez_metaheuristicas_com_brkga",
            caption="Robustez de AT, HR e BRKGA nas 10 execuções por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("n_instancias", "$N$", fmt_int),
                col(
                    "ACO_TS_gap_mediano_10_execucoes",
                    "$g^{10}_{\\mathrm{AT}}$ med.",
                    fmt_pct,
                ),
                col(
                    "HHO_RVNS_gap_mediano_10_execucoes",
                    "$g^{10}_{\\mathrm{HR}}$ med.",
                    fmt_pct,
                ),
                col(
                    "BRKGA_gap_mediano_10_execucoes",
                    "$g^{10}_{\\mathrm{BRKGA}}$ med.",
                    fmt_pct,
                ),
                col("ACO_TS_melhor_gap_mediano", "AT melhor", fmt_int),
                col("HHO_RVNS_melhor_gap_mediano", "HR melhor", fmt_int),
                col("BRKGA_melhor_gap_mediano", "BRKGA melhor", fmt_int),
                col("empates_gap_mediano", "Emp.", fmt_int),
            ),
        ),
        TableSpec(
            source=stats_dir / "resumo_gaps_metaheuristicas.csv",
            label="tab:resumo_gaps_metaheuristicas",
            caption="Média e mediana dos gaps relativos de AT, HR e BRKGA por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("n_instancias", "$N$", fmt_int),
                col("ACO_TS_gap_medio", "AT $\\bar{g}$", fmt_pct),
                col("ACO_TS_gap_mediano", "AT $\\tilde{g}$", fmt_pct),
                col("HHO_RVNS_gap_medio", "HR $\\bar{g}$", fmt_pct),
                col("HHO_RVNS_gap_mediano", "HR $\\tilde{g}$", fmt_pct),
                col("BRKGA_gap_medio", "BRKGA $\\bar{g}$", fmt_pct),
                col("BRKGA_gap_mediano", "BRKGA $\\tilde{g}$", fmt_pct),
                col("melhor_mediana", "Melhor $\\tilde{g}$", fmt_best_median),
            ),
        ),
        TableSpec(
            source=base_dir / "resumo_criterios_parada.csv",
            label="tab:criterios_parada_com_brkga",
            caption="Critérios de parada da execução que produziu o melhor valor.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo", "Metodo", fmt_method),
                col("criterio_parada", "Crit.", fmt_stop),
                col("quantidade", "$q$", fmt_int),
            ),
        ),
        TableSpec(
            source=stats_dir / "friedman_com_pli.csv",
            label="tab:friedman_com_pli_e_brkga",
            caption="Teste de Friedman entre o \\gls{BIP}, AT, HR e BRKGA por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodos", "Metodos", fmt_methods),
                col("n_instancias", "$N$", fmt_int),
                col("estatistica", "$\\chi^2_F$", fmt_num),
                col("p_valor", "$p$", fmt_pvalue),
            ),
        ),
        TableSpec(
            source=stats_dir / "ranks_medios_com_pli.csv",
            label="tab:ranks_medios_com_pli_e_brkga",
            caption="Ranks médios do \\gls{BIP}, AT, HR e BRKGA por conjunto.",
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo", "Metodo", fmt_method),
                col("rank_medio", "$\\bar{r}$", fmt_num),
                col("rank_mediano", "$\\tilde{r}$", fmt_num),
                col("melhor_em_instancias", "$M/E$", fmt_int),
            ),
        ),
        TableSpec(
            source=stats_dir / "wilcoxon_metaheuristicas_gap_relativo.csv",
            label="tab:wilcoxon_tres_metaheuristicas",
            caption=(
                "Teste de Wilcoxon pareado entre AT, HR e BRKGA sobre os gaps "
                "do melhor valor e da mediana das 10 execuções."
            ),
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo_a", "$A$", fmt_method),
                col("metodo_b", "$B$", fmt_method),
                col("variavel", "Var.", fmt_variable),
                col("n_instancias", "$N$", fmt_int),
                col("a_menor_gap", "$A<$", fmt_int),
                col("b_menor_gap", "$B<$", fmt_int),
                col("empates", "$=$", fmt_int),
                col("mediana_gap_a", "$\\tilde{g}_A$", fmt_pct),
                col("mediana_gap_b", "$\\tilde{g}_B$", fmt_pct),
                col("mediana_diferenca_a_menos_b", "$\\widetilde{\\Delta g}_{A-B}$", fmt_pct),
                col("estatistica", "$W$", fmt_num),
                col("p_valor", "$p$", fmt_pvalue),
            ),
        ),
        TableSpec(
            source=stats_dir / "wilcoxon_pos_hoc_com_pli.csv",
            label="tab:wilcoxon_pos_hoc_com_pli_e_brkga",
            caption=(
                "Comparações pós-hoc de Wilcoxon com correção de Holm entre o \\gls{BIP}, "
                "AT, HR e BRKGA."
            ),
            columns=(
                col("dataset", "Conj.", fmt_dataset),
                col("metodo_a", "$A$", fmt_method),
                col("metodo_b", "$B$", fmt_method),
                col("n_instancias", "$N$", fmt_int),
                col("estatistica", "$W$", fmt_num),
                col("p_valor", "$p$", fmt_pvalue),
                col("p_valor_holm", "$p_H$", fmt_pvalue),
            ),
        ),
    ]


def render_all_tables(base_dir: Path, fonte: str) -> tuple[str, list[Path]]:
    rendered: list[str] = []
    missing: list[Path] = []
    for spec in table_specs(base_dir):
        if not spec.source.is_file():
            missing.append(spec.source)
            continue
        rendered.append(render_table(spec, fonte))
    return "\n".join(rendered), missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera tabelas LaTeX auxiliares para as secoes de resultados a partir "
            "dos CSVs definitivos e estatisticos."
        )
    )
    parser.add_argument(
        "output_tex",
        nargs="?",
        default=str(DEFAULT_OUTPUT),
        help="Arquivo .tex de saida.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(PROJECT_ROOT / "results" / "csvs_definitivos"),
        help="Diretorio que contem os CSVs definitivos.",
    )
    parser.add_argument("--fonte", default=DEFAULT_FONTE, help="Fonte das tabelas.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_tex = project_path(args.output_tex)
    base_dir = project_path(args.base_dir)

    if not base_dir.is_dir():
        print(f"Erro: diretorio nao encontrado: {base_dir}", file=sys.stderr)
        return 1

    tex, missing = render_all_tables(base_dir, args.fonte)
    if not tex.strip():
        print("Erro: nenhuma tabela foi gerada.", file=sys.stderr)
        return 1

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(tex, encoding="utf-8")

    print(f"Tabelas auxiliares geradas em: {output_tex}")
    if missing:
        print("Arquivos ignorados por nao existirem:")
        for path in missing:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
