import pandas as pd
import argparse
import sys
from pathlib import Path


def merge_csvs(data_file: str, bounds_file: str, output_file: str):
    print("--- Iniciando mesclagem de arquivos ---")

    # 1. Carregar os arquivos CSV
    try:
        df_data = pd.read_csv(data_file)
        df_bounds = pd.read_csv(bounds_file)
    except FileNotFoundError as e:
        print(f"[ERRO] Arquivo não encontrado: {e}")
        sys.exit(1)

    print(f"Dados carregados: {len(df_data)} linhas")
    print(f"Bounds carregados: {len(df_bounds)} linhas")

    # 2. Renomear colunas do arquivo de DADOS (para o formato final desejado)
    # Mapeamento: nome_antigo -> nome_novo
    rename_map_data = {
        "filename": "Grafo",
        "vertex": "|V|",
        "edge": "|E|",
        "density": "Densidade",
        "objective": "Objetivo",
        "runtime_s": "Tempo (s)",
        "status": "Status",
    }
    df_data.rename(columns=rename_map_data, inplace=True)

    # 3. Renomear colunas do arquivo de BOUNDS (para facilitar o merge e resultado final)
    rename_map_bounds = {
        "Grafo": "Grafo",  # Mantém igual para garantir a chave de junção
        "Lower Bound": "LB",
        "Upper Bound": "UB",
    }
    df_bounds.rename(columns=rename_map_bounds, inplace=True)

    # 4. Realizar a junção (Merge)
    # Usamos 'left' join para garantir que todos os dados do arquivo principal sejam mantidos,
    # mesmo que não haja bounds para algum grafo (o que ficaria vazio).
    df_final = pd.merge(
        df_data, df_bounds[["Grafo", "LB", "UB"]], on="Grafo", how="left"
    )

    # 5. Reordenar as colunas (Opcional, mas garante a ordem visual desejada)
    colunas_ordenadas = [
        "Grafo",
        "|V|",
        "|E|",
        "Densidade",
        "Objetivo",
        "Tempo (s)",
        "Status",
        "LB",
        "UB",
    ]

    # Verifica se todas as colunas existem antes de reordenar (segurança)
    cols_to_save = [c for c in colunas_ordenadas if c in df_final.columns]
    df_final = df_final[cols_to_save]

    # 6. Salvar o resultado
    try:
        df_final.to_csv(
            output_file, index=False, float_format="%.4f"
        )  # float_format opcional para densidade
        print(f"--- Sucesso! Arquivo salvo em: {output_file} ---")
        print("Primeiras 5 linhas do resultado:")
        print(df_final.head().to_string(index=False))
    except Exception as e:
        print(f"[ERRO] Ao salvar arquivo: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mescla resultados de execução com limitantes (bounds)."
    )

    parser.add_argument(
        "dados", help="Caminho do CSV com os dados completos (filename, vertex, etc)"
    )
    parser.add_argument(
        "bounds", help="Caminho do CSV com os bounds (Grafo, Lower Bound, Upper Bound)"
    )
    parser.add_argument("saida", help="Caminho do arquivo CSV de saída")

    args = parser.parse_args()

    merge_csvs(args.dados, args.bounds, args.saida)
