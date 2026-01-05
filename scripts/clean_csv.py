import pandas as pd
import argparse
import glob
import re
import sys
import os


def limpar_nome_grafo(nome):
    # remove .txt no final
    nome = re.sub(r"\.txt$", "", nome)
    # remove prefixo numérico + underscore
    nome = re.sub(r"^\d+_", "", nome)
    return nome


def expandir_arquivos(entradas):
    arquivos = []
    for entrada in entradas:
        if any(c in entrada for c in "*?[]"):
            arquivos.extend(glob.glob(entrada))
        else:
            arquivos.append(entrada)

    arquivos = sorted(set(arquivos))

    if not arquivos:
        print("Erro: nenhum arquivo encontrado.", file=sys.stderr)
        sys.exit(1)

    return arquivos


def main():
    parser = argparse.ArgumentParser(
        description="Limpa CSV: remove coluna message e normaliza nome dos grafos"
    )

    parser.add_argument(
        "inputs", nargs="+", help="Arquivos CSV de entrada (aceita wildcard, ex: *.csv)"
    )

    parser.add_argument("--out", required=True, help="Arquivo CSV de saída")

    args = parser.parse_args()

    arquivos = expandir_arquivos(args.inputs)

    dfs = []
    for arquivo in arquivos:
        df = pd.read_csv(arquivo)

        # remove coluna message se existir
        if "message" in df.columns:
            df = df.drop(columns=["message"])

        # limpa nome do grafo
        if "filename" not in df.columns:
            print(
                f"Erro: coluna 'filename' não encontrada em {arquivo}", file=sys.stderr
            )
            sys.exit(1)

        df["filename"] = df["filename"].apply(limpar_nome_grafo)

        dfs.append(df)

    df_final = pd.concat(dfs, ignore_index=True)

    # cria diretório de saída se necessário
    if os.path.dirname(args.out):
        os.makedirs(os.path.dirname(args.out), exist_ok=True)

    df_final.to_csv(args.out, index=False)

    print(f"✔ Arquivos processados: {len(arquivos)}")
    print(f"✔ Linhas totais: {len(df_final)}")
    print(f"✔ CSV limpo gerado em: {args.out}")


if __name__ == "__main__":
    main()
