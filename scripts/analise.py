import sys
import pandas as pd
import numpy as np


def main(csv_path):
    df = pd.read_csv(csv_path)

    # Tipos corretos
    df["|V|"] = df["|V|"].astype(int)
    df["|E|"] = df["|E|"].astype(int)
    df["Densidade"] = df["Densidade"].astype(float)
    df["Objetivo"] = df["Objetivo"].astype(float)
    df["Tempo (s)"] = df["Tempo (s)"].astype(float)
    df["LB"] = df["LB"].astype(float)
    df["UB"] = df["UB"].astype(float)

    # GAPs em relação aos limites
    df["gap_LB_%"] = 100 * (df["Objetivo"] - df["LB"]) / df["LB"]
    df["gap_UB_%"] = 100 * (df["UB"] - df["Objetivo"]) / df["UB"]

    # Estatísticas gerais
    print("\n=== VISÃO GERAL DO PLI ===\n")
    print(f"Número de instâncias: {len(df)}")
    print(f"Tempo médio de execução: {df['Tempo (s)'].mean():.2f} s")
    print(f"Tempo mínimo: {df['Tempo (s)'].min():.2f} s")
    print(f"Tempo máximo: {df['Tempo (s)'].max():.2f} s")

    # Qualidade das soluções
    print("\n=== QUALIDADE DAS SOLUÇÕES ===\n")
    print(f"GAP médio em relação ao LB: {df['gap_LB_%'].mean():.2f}%")
    print(f"GAP médio em relação ao UB: {df['gap_UB_%'].mean():.2f}%")

    # Melhores e piores casos
    best_lb = df.loc[df["gap_LB_%"].idxmin()]
    worst_lb = df.loc[df["gap_LB_%"].idxmax()]

    print("\n=== MELHOR E PIOR CASO (em relação ao LB) ===\n")
    print(f"Melhor caso: {best_lb['Grafo']} (gap = {best_lb['gap_LB_%']:.2f}%)")
    print(f"Pior caso: {worst_lb['Grafo']} (gap = {worst_lb['gap_LB_%']:.2f}%)")

    # Correlações (base para análise textual)
    corr_v_obj = df["|V|"].corr(df["Objetivo"])
    corr_v_gap = df["|V|"].corr(df["gap_LB_%"])
    corr_den_obj = df["Densidade"].corr(df["Objetivo"])

    print("\n=== CORRELAÇÕES ===\n")
    print(f"Correlação |V| × Objetivo: {corr_v_obj:.4f}")
    print(f"Correlação |V| × GAP_LB: {corr_v_gap:.4f}")
    print(f"Correlação Densidade × Objetivo: {corr_den_obj:.4f}")

    # Tendência linear (escala)
    a_obj, _ = np.polyfit(df["|V|"], df["Objetivo"], 1)
    a_gap, _ = np.polyfit(df["|V|"], df["gap_LB_%"], 1)

    print("\n=== TENDÊNCIAS LINEARES ===\n")
    print(f"Crescimento médio do objetivo: +{a_obj:.4f} por vértice")
    print(f"Variação média do GAP_LB: {a_gap:.6f}% por vértice")

    # Análise por faixas de tamanho
    df["faixa_V"] = pd.cut(
        df["|V|"],
        bins=[0, 500, 1000, 2000, 3000],
        labels=["pequeno", "médio", "grande", "muito grande"],
    )

    faixa_stats = df.groupby("faixa_V")[["Objetivo", "gap_LB_%"]].mean()

    print("\n=== ANÁLISE POR PORTE DO GRAFO ===\n")
    print(faixa_stats)

    # Salvar CSV enriquecido
    df.to_csv("analise_pli_enriquecida.csv", index=False)
    print("\nArquivo salvo: analise_pli_enriquecida.csv")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python analise_pli.py dados_pli.csv")
        sys.exit(1)

    main(sys.argv[1])
