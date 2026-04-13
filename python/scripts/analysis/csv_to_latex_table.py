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
        fieldnames = reader.fieldnames

    if not rows:
        raise ValueError("CSV vazio.")

    latex = []

    latex.append("\\begin{table}[h!]")
    latex.append("\t%\\centering")
    latex.append("\t\\captionsetup{width=\\linewidth}")
    latex.append(f"\t\\Caption{{\\label{{{label}}} {caption}}}")
    latex.append("\t\\IBGEtab{}{")
    latex.append(f"\t\t\\begin{{tabular}}{{{'l' * len(fieldnames)}}}")
    latex.append("\t\t\t\\toprule")

    # Cabeçalho exatamente como no CSV
    header = " & ".join(latex_escape(h) for h in fieldnames)
    latex.append(f"\t\t\t{header} \\\\")
    latex.append("\t\t\t\\midrule \\midrule")

    for r in rows:
        values = [latex_escape(r[col]) for col in fieldnames]
        latex.append("\t\t\t" + " & ".join(values) + " \\\\")

    latex.append("\t\t\t\\bottomrule")
    latex.append("\t\t\\end{tabular}")
    latex.append("\t}{")
    latex.append(f"\t\\Fonte{{{fonte}}}")
    latex.append("}")
    latex.append("\\end{table}")

    return "\n".join(latex)


def main():
    parser = argparse.ArgumentParser(
        description="Converte CSV em tabela LaTeX (IBGE/ABNT)."
    )

    parser.add_argument("csv", help="Arquivo CSV de entrada")
    parser.add_argument("--out", required=True, help="Arquivo .tex de saída")
    parser.add_argument(
        "--caption",
        default="Resultados computacionais",
        help="Legenda da tabela",
    )
    parser.add_argument(
        "--label",
        default="tab:resultados",
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
