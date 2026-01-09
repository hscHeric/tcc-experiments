#!/usr/bin/env python3
import csv
import argparse
import sys
from pathlib import Path


def latex_escape(text: str) -> str:
    """
    Escapa caracteres especiais do LaTeX.
    """
    replacements = {
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
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text


def gerar_tabela_latex(csv_path, caption, label, fonte):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV vazio.")

    latex = []

    latex.append("\\begin{table}[h!]")
    latex.append("\t%\\centering")
    latex.append("\t\\captionsetup{width=11.3cm}")
    latex.append(f"\t\\Caption{{\\label{{{label}}} {caption}}}")
    latex.append("\t\\IBGEtab{}{")
    latex.append("\t\t\\begin{tabular}{lrrrrrr}")
    latex.append("\t\t\t\\toprule")
    latex.append(
        "\t\t\tGrafo & |V| & |E| & Densidade & Objetivo & Tempo (s) & Status \\\\"
    )
    latex.append("\t\t\t\\midrule \\midrule")

    for r in rows:
        linha = [
            latex_escape(r["filename"]),
            r["vertex"],
            r["edge"],
            r["density"],
            r["objective"],
            r["runtime_s"],
            latex_escape(r["status"]),
        ]
        latex.append("\t\t\t" + " & ".join(linha) + " \\\\")

    latex.append("\t\t\t\\bottomrule")
    latex.append("\t\t\\end{tabular}")
    latex.append("\t}{")
    latex.append(f"\t\\Fonte{{{fonte}}}")
    latex.append("}")
    latex.append("\\end{table}")

    return "\n".join(latex)


def main():
    parser = argparse.ArgumentParser(
        description="Converte CSV de instâncias de grafos em tabela LaTeX (IBGE/ABNT)."
    )

    parser.add_argument("csv", help="Arquivo CSV de entrada")
    parser.add_argument("--out", required=True, help="Arquivo .tex de saída")
    parser.add_argument(
        "--caption",
        default="Resultados computacionais para instâncias DIMACS",
        help="Legenda da tabela",
    )
    parser.add_argument(
        "--label",
        default="tab:dimacs",
        help="Label LaTeX da tabela",
    )
    parser.add_argument(
        "--fonte",
        default="elaborado pelo autor.",
        help="Fonte da tabela",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)

    if not csv_path.exists():
        print(f"Erro: arquivo '{csv_path}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    latex = gerar_tabela_latex(
        csv_path,
        caption=args.caption,
        label=args.label,
        fonte=args.fonte,
    )

    out_path.write_text(latex, encoding="utf-8")
    print(f"Tabela LaTeX gerada em: {out_path}")


if __name__ == "__main__":
    main()
